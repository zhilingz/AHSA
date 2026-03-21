"""
Purpose: Compile skill query result files into markdown and policy files by calling an LLM.
Input: Skill query result JSON files and model configuration.
Output: Generated markdown summaries and policy JSON files.
"""

import argparse
import json
import os
import re
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from verify_openai_chat_config import client as SHARED_CLIENT
except Exception:
    SHARED_CLIENT = None


SYSTEM_PROMPT = """You are a skill workflow and policy compiler.
Input is one query and a list of related skills.
You must solve the workflow abstraction and policy generation with the model itself.
Return JSON with this exact shape:
{
  "cluster_type": "string",
  "workflow": "string",
  "situations": [
    {
      "situation": "string",
      "action": "string",
      "permissions": ["string"],
      "scope": ["string"]
    }
  ],
  "policy": {
    "cluster_type": "string",
    "permissions": {}
  }
}
Rules:
- Do not output markdown.
- Do not output code fences.
- Keep permissions as arrays.
- Keep scope as arrays.
- Make the policy usable as-is.
- Only use permissions from this taxonomy (exact strings):
  filesystem: read, write, edit
  compute: exec, process
  network: web_search, web_fetch, browser
  media: image, pdf, canvas, tts
  schedule: cron, message, nodes
  agent: sessions_spawn, sessions_list, sessions_send, subagents
  system: gateway, memory_search, memory_get"""


def load_json(path):
    """
    Purpose: Read one JSON file from disk.
    Input: A file path.
    Output: A parsed JSON object.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path, data):
    """
    Purpose: Write one JSON object to disk in a stable readable format.
    Input: A file path and a serializable object.
    Output: A formatted JSON file on disk.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def dump_text(path, text):
    """
    Purpose: Write plain text output files such as generated markdown.
    Input: A file path and a text string.
    Output: A text file on disk with a trailing newline.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def normalize_text(text):
    """
    Purpose: Normalize free-form text before prompt building and output formatting.
    Input: Any text-like value.
    Output: One trimmed single-line string.
    """
    return re.sub(r"\s+", " ", (text or "")).strip()


def build_prompt(query, records, max_records=20):
    """
    Purpose: Pack the query and top skill descriptions into a compact model prompt.
    Input: A query string, raw search result records, and an optional record limit.
    Output: A compact JSON prompt string for the model.
    """
    data = {
        "query": normalize_text(query),
        "skills": [
            {
                "slug": item.get("slug"),
                "display_name": item.get("display_name"),
                "description": normalize_text(item.get("description") or item.get("summary")),
                "clawhub_url": item.get("clawhub_url"),
            }
            for item in records[:max_records]
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def extract_json(text):
    """
    Purpose: Recover the first JSON object from raw model text.
    Input: Raw model text output.
    Output: A JSON object string or None.
    """
    if not text:
        return None
    text = text.strip()
    if text.startswith("{"):
        return text
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        return fence.group(1)
    brace = re.search(r"(\{.*\})", text, re.S)
    if brace:
        return brace.group(1)
    return None


def get_client():
    """
    Purpose: Resolve one reusable OpenAI-compatible client for compiler requests.
    Input: Local shared client config or environment variables.
    Output: A ready-to-use OpenAI-compatible client.
    """
    if SHARED_CLIENT is not None:
        return SHARED_CLIENT
    if OpenAI is None:
        raise RuntimeError("openai package is required")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "https://ie-crs.haoxiang.ai/v1"),
        api_key=api_key,
    )


def call_llm(prompt, model):
    """
    Purpose: Request one workflow and policy spec from the model and parse it.
    Input: A prompt string and a model name.
    Output: A parsed model JSON object.
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content
    payload = extract_json(content)
    if not payload:
        raise ValueError("model output does not contain a JSON object")
    return json.loads(payload)


def normalize_list(value):
    """
    Purpose: Coerce model fields into a list form.
    Input: A scalar value, a list, or None.
    Output: A list of strings.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [normalize_text(str(item)) for item in value if item is not None and normalize_text(str(item))]
    text = normalize_text(str(value))
    return [text] if text else []


def normalize_spec(spec, query, records):
    """
    Purpose: Validate and normalize the model output into one stable compiler result.
    Input: A model spec plus raw query data.
    Output: A normalized compiler result.
    """
    if not isinstance(spec, dict):
        raise ValueError("model output must be a JSON object")
    cluster_type = normalize_text(spec.get("cluster_type"))
    workflow = normalize_text(spec.get("workflow"))
    policy = spec.get("policy")
    if not cluster_type:
        raise ValueError("cluster_type is required")
    if not workflow:
        raise ValueError("workflow is required")
    if not isinstance(policy, dict):
        raise ValueError("policy must be a JSON object")
    permissions = policy.get("permissions")
    if not isinstance(permissions, dict) or not permissions:
        raise ValueError("policy.permissions must be a non-empty object")
    situations = []
    for item in spec.get("situations", []):
        if not isinstance(item, dict):
            continue
        situation = normalize_text(item.get("situation"))
        action = normalize_text(item.get("action"))
        permissions_list = normalize_list(item.get("permissions"))
        scope_list = normalize_list(item.get("scope"))
        if situation and action and permissions_list and scope_list:
            situations.append(
                {
                    "situation": situation,
                    "action": action,
                    "permissions": permissions_list,
                    "scope": scope_list,
                }
            )
    if not situations:
        raise ValueError("situations must contain at least one valid item")
    policy["cluster_type"] = normalize_text(policy.get("cluster_type")) or cluster_type
    return {
        "cluster_type": cluster_type,
        "workflow": workflow,
        "situations": situations,
        "policy": policy,
        "query": normalize_text(query),
        "skills": [item.get("slug") for item in records if item.get("slug")],
    }


def to_markdown(spec):
    """
    Purpose: Render one normalized compiler result as a markdown table.
    Input: A normalized compiler result.
    Output: Markdown table text.
    """
    lines = [
        f"# {spec['cluster_type']}",
        "",
        f"query: {spec['query']}",
        "",
        f"workflow: {spec['workflow']}",
        "",
        "| Situation | Action | Permission | Scope |",
        "| --- | --- | --- | --- |",
    ]
    for item in spec["situations"]:
        permissions = ", ".join(item["permissions"])
        scope = ", ".join(item["scope"])
        lines.append(f"| {item['situation']} | {item['action']} | {permissions} | {scope} |")
    return "\n".join(lines)


def compile_file(input_path, output_dir, model):
    """
    Purpose: Compile one input JSON file into markdown and policy outputs.
    Input: One cluster JSON path, one output directory, and one model name.
    Output: Generated files on disk and the compiled spec.
    """
    data = load_json(input_path)
    query = data.get("query", "")
    records = data.get("results", [])
    prompt = build_prompt(query, records)
    spec = normalize_spec(call_llm(prompt, model), query, records)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    dump_text(output_dir / f"{stem}.md", to_markdown(spec))
    dump_json(output_dir / f"{stem}.policy.json", spec["policy"])
    return spec


def iter_inputs(path):
    """
    Purpose: Expand one input argument into a list of JSON files to compile.
    Input: A file path or directory path.
    Output: A list of input JSON paths.
    """
    if path.is_file():
        return [path]
    return sorted(path.glob("*.json"))


def main():
    """
    Purpose: Run the compiler from the command line for one file or a whole directory.
    Input: CLI arguments.
    Output: Generated files on disk and one printed result line per input file.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="skills")
    parser.add_argument("--output", default="generated")
    parser.add_argument("--model", default=os.getenv("SKILL_CLUSTERING_MODEL", "google/gemini-3.1-flash-lite-preview"))
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    input_path = (base / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    output_dir = (base / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    for path in iter_inputs(input_path):
        spec = compile_file(path, output_dir, args.model)
        print(json.dumps({"input": str(path), "cluster_type": spec["cluster_type"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
