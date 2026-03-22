# AHSA

[中文说明](./README.zh.md)

AHSA means Ad Hoc Sandboxed Agent.

This project explores a simple idea: an agent task should run only with the permissions it actually needs.

The long-term goal is larger than this prototype. Every skill on ClawHub should eventually declare its security boundary in a structured form:

- `Situation`
- `Action`
- `Permission`
- `Scope`

This would make skill behavior easier to review, easier to compare, and easier to enforce. To make that work at ecosystem scale, OpenClaw needs official support in two places:

- ClawHub should require or standardize the `Situation | Action | Permission | Scope` layer
- OpenClaw should enforce permissions at runtime with low-level checks before execution

## what this repo contains

- `scraper.py`
  fetches skill metadata and `SKILL.md` files from ClawHub

- `cluster_compiler.py`
  reads grouped skill data and asks an LLM to generate:
  - workflow markdown
  - policy json

- `security_interceptor.py`
  enforces file, command, and generic capability checks at runtime

## how it works

The research flow is:

1. collect skill or task data
2. generate a task or cluster policy
3. use the policy to gate runtime operations

The intended security model is:

- collect traces or grouped skill descriptions
- infer a task-specific permission profile
- block operations that exceed this profile

The current code is a minimal prototype of that direction.

## capabilities

The policy vocabulary used in this project includes:

- file system: `read`, `write`, `edit`
- compute: `exec`, `process`
- network: `web_search`, `web_fetch`, `browser`
- media: `image`, `pdf`, `canvas`, `tts`
- schedule: `cron`, `message`, `nodes`
- agent: `sessions_spawn`, `sessions_list`, `sessions_send`, `subagents`
- system: `gateway`, `memory_search`, `memory_get`

## examples in this repo

This repository includes checked-in runtime examples under `examples/`.

- `examples/compiler_input/`
  sample grouped skill input

- `examples/compiler_run/`
  sample compiler output

- `examples/interceptor_run/`
  sample interceptor input, normalized policy, result, and audit log

- `examples/scraper_run/output/`
  sample scraped skills, descriptions, and indexes

Useful example files:

- `examples/compiler_run/query_results_codex_vibe_workflow.md`
- `examples/compiler_run/query_results_codex_vibe_workflow.policy.json`
- `examples/interceptor_run/policy.json`
- `examples/interceptor_run/normalized_policy.json`
- `examples/interceptor_run/result.json`
- `examples/interceptor_run/audit.jsonl`
- `examples/scraper_run/output/index.json`

## environment

You must configure the LLM endpoint yourself.

The code does not include any default API base URL or API key.

```bash
export OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
export OPENAI_API_KEY=your_key
export SKILL_CLUSTERING_MODEL=google/gemini-3.1-flash-lite-preview
```

## run scraper

```bash
python3 scraper.py -n 100 --output .
```

Expected outputs:

- `output/skills/*.md`
- `output/descriptions/*.json`
- `output/index.json`
- `output/index.csv`

## run compiler

Input json format:

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

Expected outputs:

- one markdown file with:
  - `cluster_type`
  - `query`
  - `workflow`
  - `Situation | Action | Permission | Scope`
- one policy json file with:
  - `cluster_type`
  - `permissions`

Note:

- compiler output depends on external model availability
- the checked-in `examples/compiler_run/` files are a successful sample run

## run interceptor

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from security_interceptor import PolicyEngine, SecurityInterceptionError

root = Path(".").resolve()
path = root / "examples" / "compiler_run" / "query_results_codex_vibe_workflow.policy.json"
engine = PolicyEngine.from_file(path, project_root=root, audit_log_path=str(root / "examples" / "interceptor_run" / "audit.jsonl"))

print(engine.check_file("read", "README.md"))
print(engine.check_exec("python3 -V"))
print(engine.check_capability("message", "feishu:group1"))
print(engine.check_capability("web_search", "https://example.com"))

try:
    engine.check_file("read", "../proposal.md")
except SecurityInterceptionError as e:
    print(e.to_dict())

try:
    engine.check_exec("rm -rf /tmp/x")
except SecurityInterceptionError as e:
    print(e.to_dict())
PY
```

Expected results:

- allowed file read returns `method` and `path`
- allowed command returns `command`
- allowed capability returns `capability` and `target`
- blocked operations return:
  - `error`
  - `capability`
  - `reason`
  - `target`

The interceptor reads the compiler policy, normalizes it into runtime enforcement schema, and then applies checks.
