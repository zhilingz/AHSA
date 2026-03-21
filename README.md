# AHSA

## files

- `scraper.py`: fetch clawhub skill metadata and SKILL.md files
- `cluster_compiler.py`: read grouped skill json, call llm, output `md + policy.json`
- `security_interceptor.py`: enforce file, exec, capability policy
- `RESEARCH.md`: research plan

## env

```bash
export OPENAI_BASE_URL=https://ie-crs.haoxiang.ai/v1
export OPENAI_API_KEY=your_key
export SKILL_CLUSTERING_MODEL=google/gemini-3.1-flash-lite-preview
```

## run scraper

```bash
python3 scraper.py -n 100 --output .
```

outputs:

- `output/skills/*.md`
- `output/descriptions/*.json`
- `output/index.json`
- `output/index.csv`

## run compiler

input json format:

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

run:

```bash
python3 cluster_compiler.py --input /path/to/skills --output /path/to/generated
```

## run interceptor check

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
