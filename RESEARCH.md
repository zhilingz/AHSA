# RESEARCH

## goal

build a minimal llm-driven security workflow for clustered agent skills

## parts

- `scraper.py`
  - input: clawhub list api and file api
  - output: skill markdown and metadata index
  - use: build local skill dataset

- `cluster_compiler.py`
  - input: grouped skill json
  - output: workflow markdown and policy json
  - method: llm abstraction only

- `security_interceptor.py`
  - input: policy json and runtime operation
  - output: pass or block
  - scope: file system, command execution, generic capability

## flow

1. fetch skill dataset
2. compile grouped skills into workflow and policy
3. load policy in interceptor
4. validate file, exec, capability calls
5. record pass and block events

## deliverables

- scraper
- llm compiler
- interceptor
- run guide
