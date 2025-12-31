import { Badge, Button, Caption1Strong, Card, CardFooter, CardHeader, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle, Field, makeStyles, mergeClasses, MessageBar, MessageBarBody, MessageBarTitle, Spinner, Textarea, tokens } from "@fluentui/react-components";
import { Checkmark16Regular, CheckmarkCircle20Filled, Circle20Filled, Dismiss16Regular, DismissCircle20Filled, PersonFeedback20Filled } from "@fluentui/react-icons";
import { useState } from "react";
import { issueTypeLabel } from "../i18n/labels";
import { callApi } from "../services/api";
import { DismissalFeedback, Issue, IssueStatus, ModifiedFields } from "../types/issue";

type IssueCardProps = {
  docId: string;
  issue: Issue;
  selected: boolean;
  onSelect: (issue: Issue) => void;
  onUpdate: (updatedIssue: Issue) => void;
};

const useStyles = makeStyles({
  card: { margin: '5px' },
  explanation: { marginTop: '10px' },
  accepted: {
    backgroundColor: tokens.colorPaletteGreenBackground1,
  },
  dismissed: {
    backgroundColor: tokens.colorNeutralBackground2
  },
  header: { height: '40px', textOverflow: 'ellipsis' },
  footer: { paddingTop: '10px' },
  feedback: {
    backgroundColor: tokens.colorPaletteYellowBackground2,
  },
});

export function IssueCard({ docId, issue, selected, onSelect, onUpdate }: IssueCardProps) {
  const classes = useStyles();

  function getCardClassName() {
    switch (issue.status) {
      case IssueStatus.Accepted:
        return mergeClasses(classes.card, classes.accepted);
      case IssueStatus.Dismissed:
        return mergeClasses(classes.card, classes.dismissed);
      default:
        return classes.card;
    }
  }

  const [accepting, setAccepting] = useState<boolean>(false);
  const [dismissing, setDismissing] = useState<boolean>(false);
  const [submittingFeedback, setSubmittingFeedback] = useState<boolean>(false);
  const [addFeedback, setAddFeedback] = useState<boolean>(false);
  const [modifiedExplanation, setModifiedExplanation] = useState<string>();
  const [modifiedSuggestedFix, setModifiedSuggestedFix] = useState<string>();
  const [feedback, setFeedback] = useState<DismissalFeedback>();
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);
  const [error, setError] = useState<string>();
  const [hitlOpen, setHitlOpen] = useState<boolean>(false);
  const [hitlLoading, setHitlLoading] = useState<boolean>(false);
  const [hitlThreadId, setHitlThreadId] = useState<string>();
  const [hitlInterruptId, setHitlInterruptId] = useState<string>();
  const [hitlArgsJson, setHitlArgsJson] = useState<string>("");
  const [hitlError, setHitlError] = useState<string>();

  function buildModifiedFields(): ModifiedFields | undefined {
    const modifiedFields: ModifiedFields = {};
    if (modifiedExplanation) modifiedFields.explanation = modifiedExplanation;
    if (modifiedSuggestedFix) modifiedFields.suggested_fix = modifiedSuggestedFix;
    return Object.keys(modifiedFields).length ? modifiedFields : undefined;
  }

  async function openHitlEditDialog() {
    setHitlError(undefined);
    setHitlOpen(true);
    setHitlLoading(true);
    try {
      const response = await callApi(
        `${docId}/issues/${issue.id}/hitl/start`,
        "POST",
        {
          action: "accept",
          modified_fields: buildModifiedFields(),
        },
      );
      const payload = (await response.json()) as {
        thread_id: string;
        interrupt_id?: string;
        proposed_action: { name: string; args: unknown };
      };
      setHitlThreadId(payload.thread_id);
      setHitlInterruptId(payload.interrupt_id);
      setHitlArgsJson(JSON.stringify(payload.proposed_action.args, null, 2));
    } catch (err) {
      if (err instanceof Error) setHitlError(err.message);
      else setHitlError(String(err));
    } finally {
      setHitlLoading(false);
    }
  }

  async function runHitlDecision(decision: Record<string, unknown>) {
    if (!hitlThreadId) {
      setHitlError("缺少 thread_id，无法继续。请重新打开编辑窗口。");
      return;
    }
    setHitlLoading(true);
    setHitlError(undefined);
    try {
      const response = await callApi(
        `${docId}/issues/${issue.id}/hitl/resume`,
        "POST",
        {
          thread_id: hitlThreadId,
          interrupt_id: hitlInterruptId,
          decision,
        },
      );
      const updatedIssue = (await response.json()) as Issue;
      onUpdate(updatedIssue);
      setHitlOpen(false);
      setHitlThreadId(undefined);
      setHitlInterruptId(undefined);
      setHitlArgsJson("");
    } catch (err) {
      if (err instanceof Error) setHitlError(err.message);
      else setHitlError(String(err));
    } finally {
      setHitlLoading(false);
    }
  }

  /**
   * 接受问题，并提交修改内容（可选）。
   */
  async function handleAccept() {
    try {
      setAccepting(true);
      // Send the request
      const response = await callApi(
        `${docId}/issues/${issue.id}/accept`,
        'PATCH',
        buildModifiedFields()
      )
      // Update issue state
      const updatedIssue = (await response.json()) as Issue;
      if (onUpdate) {
        onUpdate(updatedIssue);
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setAccepting(false);
    }
  }

  /**
   * 驳回问题。
   */
  async function handleDismiss() {
    try {
      setDismissing(true);
      const response = await callApi(`${docId}/issues/${issue.id}/dismiss`, 'PATCH');
      const updatedIssue = (await response.json()) as Issue;
      if (onUpdate) {
        onUpdate(updatedIssue);
      }
      setAddFeedback(true);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setDismissing(false);
    }
  }

  /**
   * 提交驳回反馈。
   */
  async function handleSubmitFeedback() {
    try {
      setSubmittingFeedback(true);
      await callApi(`${docId}/issues/${issue.id}/feedback`, 'PATCH', feedback);
      setFeedbackSubmitted(true);
      setAddFeedback(false);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setSubmittingFeedback(false);
    }
  }

  return (
    <Card className={getCardClassName()} selected={selected} onSelectionChange={() => onSelect(issue)} color={tokens.colorNeutralForeground2}>
        <CardHeader
          className={classes.header}
          image={
            issue.status === IssueStatus.Accepted
              ? <CheckmarkCircle20Filled primaryFill={tokens.colorPaletteLightGreenForeground1} />
              : issue.status === IssueStatus.Dismissed
                ? <DismissCircle20Filled primaryFill={tokens.colorNeutralForeground2} />
                : <Circle20Filled primaryFill={tokens.colorNeutralBackground4} />
          }
          header={
            <Caption1Strong strikethrough={issue.status === IssueStatus.Dismissed}>{ issue.text }</Caption1Strong>
          }
        />

        <Badge appearance="tint" color="informative" shape="rounded">
          { issueTypeLabel(issue.type) }
        </Badge>

      {
        selected && <>
          <Field label="说明" className={classes.explanation}>
            <Textarea
              defaultValue={issue.modified_fields?.explanation ? issue.modified_fields.explanation : issue.explanation}
              readOnly={issue.status !== IssueStatus.NotReviewed}
              value={modifiedExplanation}
              onChange={e => setModifiedExplanation(e.target.value)}
              required
              rows={4}
            />
          </Field>
          <Field label="建议修改">
            <Textarea
              defaultValue={issue.modified_fields?.suggested_fix ? issue.modified_fields?.suggested_fix : issue.suggested_fix}
              readOnly={issue.status !== IssueStatus.NotReviewed}
              value={modifiedSuggestedFix}
              onChange={e => setModifiedSuggestedFix(e.target.value)}
              required
              rows={4} 
            />
          </Field>
          {
            error && <MessageBar intent="error">
              <MessageBarBody>
                <MessageBarTitle>错误</MessageBarTitle>
                { error }
              </MessageBarBody>
            </MessageBar>
          }
          { 
            issue.status === IssueStatus.NotReviewed && <CardFooter className={classes.footer}>
              <Button
                appearance="primary"
                disabledFocusable={accepting}
                icon={
                  accepting ? (
                    <Spinner size="tiny" />
                  ) : <Checkmark16Regular />
                }
                onClick={handleAccept}
              >
                接受
              </Button>
              <Button
                appearance="secondary"
                disabledFocusable={hitlLoading}
                onClick={openHitlEditDialog}
              >
                编辑并执行
              </Button>
              <Button
                disabledFocusable={dismissing}
                icon={
                  dismissing ? (
                    <Spinner size="tiny" />
                  ) : <Dismiss16Regular />
                }
                onClick={handleDismiss}
              >
                驳回
              </Button>
            </CardFooter>
          }
          {
            addFeedback && <Card appearance="outline" className={classes.feedback}>
              <CardHeader image={<PersonFeedback20Filled primaryFill={tokens.colorPaletteDarkOrangeForeground1} />} header="帮助我们改进" />
              <Field>
                <Textarea
                  value={feedback?.reason}
                  placeholder="请说明为什么这个建议不正确，以及应如何改进。"
                  onChange={e => setFeedback({...feedback, reason: e.target.value})}
                  required
                  rows={4}
                />
              </Field>
              <CardFooter>
                <Button
                  appearance="primary"
                  disabled={!feedback}
                  onClick={handleSubmitFeedback}
                  disabledFocusable={submittingFeedback}
                  icon={
                    submittingFeedback ? (
                      <Spinner size="tiny" />
                    ) : undefined
                  }
                >
                  提交
                </Button>
              </CardFooter>
            </Card>
          }
          {
            feedbackSubmitted && <MessageBar intent="success">
              <MessageBarBody>
                <MessageBarTitle>反馈已提交</MessageBarTitle>
                感谢你的反馈，我们会持续改进审阅效果。
              </MessageBarBody>
            </MessageBar>
          }
        </>
      }
      <Dialog open={hitlOpen} onOpenChange={(_, data) => setHitlOpen(data.open)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>HITL 编辑（接受）</DialogTitle>
            <DialogContent>
              {hitlError && (
                <MessageBar intent="error">
                  <MessageBarBody>
                    <MessageBarTitle>错误</MessageBarTitle>
                    {hitlError}
                  </MessageBarBody>
                </MessageBar>
              )}
              <Field label="将要执行的工具参数（JSON，可编辑）">
                <Textarea
                  value={hitlArgsJson}
                  onChange={(e) => setHitlArgsJson(e.target.value)}
                  rows={10}
                />
              </Field>
            </DialogContent>
            <DialogActions>
              <Button
                appearance="primary"
                disabledFocusable={hitlLoading}
                icon={hitlLoading ? <Spinner size="tiny" /> : undefined}
                onClick={() => runHitlDecision({ type: "approve" })}
              >
                直接执行
              </Button>
              <Button
                disabledFocusable={hitlLoading}
                onClick={() => {
                  try {
                    const args = JSON.parse(hitlArgsJson || "{}");
                    runHitlDecision({
                      type: "edit",
                      edited_action: { name: "update_issue", args },
                    });
                  } catch {
                    setHitlError("JSON 解析失败，请检查格式。");
                  }
                }}
              >
                按编辑执行
              </Button>
              <Button appearance="secondary" onClick={() => setHitlOpen(false)}>
                取消
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </Card>
  )
}
