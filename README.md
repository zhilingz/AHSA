# AHSA

[中文说明](./README.zh.md)

## abstract

AHSA means Ad Hoc Sandboxed Agent.

It is a research prototype for zero-trust execution of AI agent skills.

The core idea is:

- a concrete task only needs a strict subset of full system permissions
- this subset can be approximated from execution traces
- later executions should be constrained by that task-specific profile

AHSA uses 3 stages:

1. trace run
2. profile generation
3. sandboxed execution

## problem

Modern agents can read files, run commands, call tools, and access external services.

This creates 3 major risks:

- malicious third-party skills
- prompt injection
- model planning errors

The root issue is over-privilege:

- task-specific required permissions are smaller than full system permissions
- current agent frameworks usually run with much broader authority

AHSA addresses this by moving security control from prompt-only constraints to code-level enforcement.

## research questions

### formal target

Given:

- task `T`
- agent `A`
- full capability set `C`

AHSA tries to approximate a task-specific capability profile `P(T, A)`, where:

- `P(T, A) ⊆ C`
- `P(T, A)` contains only the permissions required to complete `T`

### core questions

- how to collect representative traces for one task
- how to convert traces into a stable capability profile
- how to enforce the profile at runtime with acceptable overhead
- how to reduce false positives and false negatives

## architecture

AHSA has 2 logical layers:

- policy layer
- enforcement layer

### policy layer

The policy layer:

- collects grouped skill or task data
- extracts workflow structure
- maps workflow to `Situation | Action | Permission | Scope`
- compiles the result as policy json

### enforcement layer

The enforcement layer:

- checks file access against path rules
- checks command execution against restricted command rules
- checks generic capabilities against target scope rules
- blocks out-of-profile operations
- writes audit records for pass and block

## three-stage mechanism

### phase 1: trace run

Run the task in a controlled environment and record:

- tool calls
- file reads and writes
- network requests
- command execution
- data flow between input and output resources

### phase 2: profile generation

Convert trace results into a capability profile:

- aggregate observed actions
- generalize exact resources into reusable scope patterns
- remove redundant or clearly unrelated permissions

Example policy shape:

```json
{
  "cluster_type": "ai_coding_workflow",
  "permissions": {
    "file_system": {
      "default_action": "deny",
      "rules": [
        {
          "method": ["read", "edit", "write"],
          "path_glob": ["./**/*"]
        }
      ]
    },
    "exec": {
      "allowed": true,
      "restricted_cmds": ["rm -rf", "mkfs"]
    }
  }
}
```

### phase 3: sandboxed execution

Before each runtime action:

- normalize the target
- check whether it is inside the profile
- allow, block, or escalate

Current prototype supports:

- file system interception
- command interception
- generic capability checks
- audit logging

## capability taxonomy

- file system: `read`, `write`, `edit`
- compute: `exec`, `process`
- network: `web_search`, `web_fetch`, `browser`
- media: `image`, `pdf`, `canvas`, `tts`
- schedule: `cron`, `message`, `nodes`
- agent: `sessions_spawn`, `sessions_list`, `sessions_send`, `subagents`
- system: `gateway`, `memory_search`, `memory_get`

## key challenges

### incomplete trace coverage

A limited number of runs may miss legitimate actions.

Possible directions:

- diversify task inputs
- estimate trace coverage
- generalize from exact resources to semantic scope
- update profiles under supervision

### profile poisoning

If trace collection runs in a polluted environment, the generated profile may inherit malicious permissions.

Possible directions:

- use isolated trace environments
- review profiles manually
- compare profile output against task prior constraints
- cross-check independent traces

### residual indirect injection

Even when all single actions are allowed, an attacker may still abuse legal steps to achieve a malicious goal.

Possible directions:

- constrain action sequences
- track input-to-output data flow
- combine with input-layer injection defense
- verify consistency between current action and original task intent

## expected contributions

### research

- a formal task-specific capability profile concept for agents
- a complete trace-to-profile-to-sandbox pipeline
- an evaluation frame for profile precision and coverage
- a security-oriented dataset for skill and capability analysis

### engineering

- a ClawHub skill scraper
- an llm-driven profile compiler
- a runtime security interceptor
- an auditable execution boundary for agent systems

## files

- `scraper.py`: fetch skill metadata and `SKILL.md` files from ClawHub
- `cluster_compiler.py`: read grouped skill json and use an LLM to generate workflow markdown and policy json
- `security_interceptor.py`: enforce file, command, and capability policy before runtime execution

## examples

This repository includes checked-in runtime examples under `examples/`.

- `examples/compiler_input/`: one grouped skill input file
- `examples/compiler_run/`: one workflow markdown and one policy json generated from that input
- `examples/interceptor_run/`: one test policy, one audit log, and one block/pass result file
- `examples/scraper_run/output/`: one small scraped dataset with skill markdown, descriptions, and indexes

## env

You must configure the LLM endpoint yourself.

The code does not include any default API base URL or API key.

Set all required variables before running the compiler:

```bash
export OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
export OPENAI_API_KEY=your_key
export SKILL_CLUSTERING_MODEL=google/gemini-3.1-flash-lite-preview
```

## run scraper

```bash
python3 scraper.py -n 100 --output .
```

Outputs:

- `output/skills/*.md`
- `output/descriptions/*.json`
- `output/index.json`
- `output/index.csv`

Expected example structure:

```text
examples/scraper_run/output/
├── descriptions/
├── skills/
├── index.csv
└── index.json
```

Included example files:

- `examples/scraper_run/output/skills/self-improving-agent.md`
- `examples/scraper_run/output/descriptions/self-improving-agent.json`
- `examples/scraper_run/output/index.json`

## run compiler

Input json:

```json
{
  "query": "string",
  "results": [
    {
      "slug": "string",
      "display_name": "string",
      "description": "string"
    }
  ]
}
```

Run:

```bash
python3 cluster_compiler.py --input /path/to/skills --output /path/to/generated
```

Outputs:

- `generated/*.md`
- `generated/*.policy.json`

Expected output shape:

- one markdown file with:
  - `cluster_type`
  - `query`
  - `workflow`
  - `Situation | Action | Permission | Scope`
- one policy json file with:
  - `cluster_type`
  - `permissions`

Included example files:

- `examples/compiler_input/query_results_codex_vibe_workflow.json`
- `examples/compiler_run/query_results_codex_vibe_workflow.md`
- `examples/compiler_run/query_results_codex_vibe_workflow.policy.json`
- `examples/compiler_run/notes.txt`

Current note:

- compiler output depends on external model availability
- one live run failed with upstream `502`
- the checked-in `compiler_run` files are from a successful run of the same input

## run interceptor

```bash
python3 - <<'PY'
import json
from pathlib import Path
from security_interceptor import PolicyEngine, SecurityInterceptionError

root = Path(".").resolve()
policy = {
    "cluster_type": "test",
    "permissions": {
        "file_system": {
            "default_action": "deny",
            "rules": [{"method": ["read"], "path_glob": ["./*"]}]
        },
        "exec": {
            "allowed": True,
            "restricted_cmds": ["rm -rf"]
        },
        "message": {
            "allowed": True,
            "allowed_targets": ["feishu:*"]
        }
    }
}

path = root / "policy.json"
path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
engine = PolicyEngine.from_file(path, project_root=root)
print(engine.check_file("read", "README.md"))
print(engine.check_exec("python3 -V"))
print(engine.check_capability("message", "feishu:test"))
try:
    engine.check_exec("rm -rf /tmp/x")
except SecurityInterceptionError as e:
    print(e.to_dict())
PY
```

Expected result shape:

- allowed file read returns `{"method": "...", "path": "..."}`
- allowed command returns `{"command": "..."}`
- allowed capability returns `{"capability": "...", "target": "..."}`
- blocked operations return:
  - `error`
  - `capability`
  - `reason`
  - `target`

Included example files:

- `examples/interceptor_run/policy.json`
- `examples/interceptor_run/result.json`
- `examples/interceptor_run/audit.jsonl`
