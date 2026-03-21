# RESEARCH

## goal

build a minimal llm-driven security workflow for clustered agent skills

## parts

- `cluster_compiler.py`
  - input: grouped skill json
  - output: workflow markdown and policy json
  - method: llm abstraction only

- `security_interceptor.py`
  - input: policy json and runtime operation
  - output: pass or block
  - scope: file system, command execution, generic capability

- `verify_openai_chat_config.py`
  - input: prompt and model
  - output: llm response
  - use: verify api config before compiling

## flow

1. verify llm api
2. compile grouped skills into workflow and policy
3. load policy in interceptor
4. validate file, exec, capability calls
5. record pass and block events

## deliverables

- llm compiler
- interceptor
- api check script
- run guide
