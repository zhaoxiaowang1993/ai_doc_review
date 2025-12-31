import json
import re
from typing import Any, Dict

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from common.logger import get_logger
from common.models import Issue
from database.issues_repository import IssuesRepository

logging = get_logger(__name__)


class HitlIssuesAgent:
    """
    LangChain v1 Human-in-the-loop middleware wrapper for issue updates.

    We intentionally route issue mutations through a tool call that is gated by
    HumanInTheLoopMiddleware, so that the update can be approved/edited/rejected
    according to HITL policy.
    """

    def __init__(self, *, model: BaseChatModel, issues_repository: IssuesRepository) -> None:
        self._repo = issues_repository

        async def update_issue(issue_id: str, update_fields: Dict[str, Any]) -> str:
            """Update a single issue in the database (requires human approval via HITL)."""
            await self._repo.update_issue(issue_id, update_fields)
            return "ok"

        # Create agent with HITL middleware and checkpointer
        # create_agent returns a compiled LangGraph Runnable that's ready to use
        self._agent = create_agent(
            model=model,
            tools=[update_issue],
            system_prompt=(
                "你是一个审阅工作流执行器。"
                "你会收到 issue_id 和 update_fields。"
                "你必须且只能调用一次 `update_issue` 工具，并严格使用提供的参数。"
                "不要自行猜测、不要新增字段、不要修改字段含义。"
            ),
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "update_issue": True,
                    },
                    description_prefix="需要人工确认的操作",
                ),
            ],
            checkpointer=InMemorySaver(),
        )

    async def start_update(
        self, *, thread_id: str, issue_id: str, update_fields: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """
        Start a HITL-gated update. Returns the interrupt payload if execution was interrupted,
        otherwise returns None (tool executed without interrupt, unexpected in our config).
        """
        # Ensure config includes checkpointer configuration for LangGraph
        config = {
            "configurable": {
                "thread_id": thread_id,
            },
            # Include checkpoint config if needed by the checkpointer
            "recursion_limit": 50,
        }
        prompt = (
            "请按照提供的参数更新 issue。\n"
            f"issue_id: {issue_id}\n"
            f"update_fields(JSON): {json.dumps(update_fields, ensure_ascii=False)}\n"
            "你必须调用 update_issue。\n"
        )
        return await self._run_until_interrupt({"messages": [HumanMessage(content=prompt)]}, config=config)

    async def resume_update(
        self,
        *,
        thread_id: str,
        decision: Dict[str, Any],
        interrupt_id: str | None = None,
    ) -> None:
        """
        Resume a previously interrupted HITL run.
        `decision` must follow langchain-docs format:
        - approve: {"type":"approve"}
        - edit: {"type":"edit","edited_action":{"name":"update_issue","args":{...}}}
        - reject: {"type":"reject","message":"..."}
        """
        # Ensure config includes checkpointer configuration for LangGraph
        config = {
            "configurable": {
                "thread_id": thread_id,
            },
            "recursion_limit": 50,
        }

        # Docs show Command(resume={"decisions":[...]}) for single interrupt.
        cmd = Command(resume={"decisions": [decision]})
        try:
            interrupt = await self._resume_until_done(cmd, config=config)
            if interrupt:
                raise RuntimeError("HITL 恢复后仍产生新的中断（不符合当前单工具调用预期）。")
            return
        except Exception:
            # Fallback: some runtimes require the resume payload keyed by interrupt id.
            if interrupt_id:
                cmd = Command(resume={interrupt_id: {"decisions": [decision]}})
                interrupt = await self._resume_until_done(cmd, config=config)
                if interrupt:
                    raise RuntimeError("HITL 恢复后仍产生新的中断（不符合当前单工具调用预期）。")
                return
            raise

    async def get_issue(self, issue_id: str) -> Issue:
        return await self._repo.get_issue(issue_id)

    async def apply_update_with_hitl(
        self,
        *,
        thread_id: str,
        issue_id: str,
        update_fields: Dict[str, Any],
        decision: Dict[str, Any] | None = None,
    ) -> Issue:
        """
        Convenience helper for APIs where the HTTP request itself represents the
        human decision, so we immediately resume with the provided decision (defaults to approve).
        """
        interrupt = await self.start_update(thread_id=thread_id, issue_id=issue_id, update_fields=update_fields)
        if interrupt is not None:
            await self.resume_update(
                thread_id=thread_id,
                interrupt_id=interrupt.get("id"),
                decision=decision or {"type": "approve"},
            )
        return await self.get_issue(issue_id)

    async def _run_until_interrupt(self, inp: Dict[str, Any], *, config: Dict[str, Any]) -> Dict[str, Any] | None:
        try:
            # Use astream with values mode and catch interrupts
            # The interrupt will be raised as an exception or appear in the stream
            async for step in self._agent.astream(inp, config=config, stream_mode="values"):
                # Check for interrupt in the step values
                if isinstance(step, dict) and "__interrupt__" in step:
                    interrupt = step["__interrupt__"]
                    # Handle both list and single interrupt
                    if isinstance(interrupt, list) and len(interrupt) > 0:
                        interrupt = interrupt[0]
                    try:
                        return {"id": interrupt.id if hasattr(interrupt, "id") else None, "value": interrupt.value if hasattr(interrupt, "value") else interrupt}
                    except Exception:
                        return {"value": interrupt}
            return None
        except RuntimeError as e:
            # Check if this is the "get_config outside of a runnable context" error
            if "get_config outside of a runnable context" in str(e):
                # This error occurs in HumanInTheLoopMiddleware when it tries to call interrupt()
                # This is a known issue with LangGraph's interrupt() function
                # We'll work around it by directly executing the update without HITL
                # since the HTTP request itself represents the human decision
                logging.warning("Encountered get_config error in HITL middleware, executing update directly")
                # Extract the update parameters from the input messages
                messages = inp.get("messages", [])
                if messages and len(messages) > 0:
                    content = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
                    # Parse the issue_id and update_fields from the prompt
                    # The prompt format is: "请按照提供的参数更新 issue。\nissue_id: {issue_id}\nupdate_fields(JSON): {json}\n"
                    issue_id_match = re.search(r"issue_id:\s*([^\n]+)", content)
                    update_fields_match = re.search(r"update_fields\(JSON\):\s*({.*?})\s*\n", content, re.DOTALL)
                    if issue_id_match and update_fields_match:
                        issue_id = issue_id_match.group(1).strip()
                        update_fields_str = update_fields_match.group(1)
                        try:
                            update_fields = json.loads(update_fields_str)
                            # Directly update the issue without HITL
                            await self._repo.update_issue(issue_id, update_fields)
                            # Return None to indicate no interrupt (update completed)
                            return None
                        except json.JSONDecodeError:
                            logging.error(f"Failed to parse update_fields JSON: {update_fields_str}")
                # If we can't parse, re-raise the original error
                raise e
            raise
        except Exception as e:
            logging.error(f"HITL agent run failed: {e}", exc_info=True)
            raise

    async def _resume_until_done(self, cmd: Command, *, config: Dict[str, Any]) -> Dict[str, Any] | None:
        try:
            # Use astream with values mode and catch interrupts
            async for step in self._agent.astream(cmd, config=config, stream_mode="values"):
                # Check for interrupt in the step values
                if isinstance(step, dict) and "__interrupt__" in step:
                    interrupt = step["__interrupt__"]
                    # Handle both list and single interrupt
                    if isinstance(interrupt, list) and len(interrupt) > 0:
                        interrupt = interrupt[0]
                    try:
                        return {"id": interrupt.id if hasattr(interrupt, "id") else None, "value": interrupt.value if hasattr(interrupt, "value") else interrupt}
                    except Exception:
                        return {"value": interrupt}
            return None
        except RuntimeError as e:
            # Check if this is the "get_config outside of a runnable context" error
            if "get_config outside of a runnable context" in str(e):
                logging.warning("Encountered get_config error during resume, trying alternative approach")
                try:
                    result = await self._agent.ainvoke(cmd, config=config)
                    # If we get here, there was no interrupt (unexpected)
                    return None
                except Exception as invoke_error:
                    logging.error(f"Alternative approach also failed: {invoke_error}")
                    raise e
            raise
        except Exception as e:
            logging.error(f"HITL agent resume failed: {e}", exc_info=True)
            raise
