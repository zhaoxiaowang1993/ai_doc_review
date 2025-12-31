# LLM app

This document contains a high-level overview of the LLM application (residing in the `flows` folder).

## Overview

The LLM application is responsible for executing the agents on the input text and returning the results to the caller. The application is built using the PromptFlow framework, which provides a set of tools for building and executing agents. The application is designed to be modular, with each agent being implemented as a separate flow that can be executed independently and in parallel.

> A [Flow](https://learn.microsoft.com/en-us/azure/machine-learning/prompt-flow/concept-flows?view=azureml-api-2) in PromptFlow is essentially an executable workflow with defined inputs and outputs, that can run any Python code.

The application consists of the following components:

- **Main flow**: this is the entry point for the application and is responsible for processing the input text and executing the agents on the input text.
- **Agent flows**: The agent flows are responsible for executing the agents on the input text. Each agent flow is implemented as a separate flow that can be executed independently. The agent flows contain the logic for executing the agents and processing the results.

For more details on the main flow architecture, see the [main flow design document](./main_flow_design.md).

For more details on the agents, see the [agent documentation](./agent_design.md).

### Evaluation

The LLM application also includes an evaluation flow that can be used to evaluate the performance of the agents. The evaluation flow takes as input the output of the agents and the ground truth data and computes various metrics to evaluate the performance of the agents. For more details on the evaluation flow, see the [evaluation flow document](./evaluation_flow.md).
