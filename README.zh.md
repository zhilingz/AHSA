# AHSA

[English](./README.md)

AHSA 的全称是 Ad Hoc Sandboxed Agent。

这个项目研究的是一个简单但重要的问题：AI agent 在执行具体任务时，应该只拥有完成该任务真正需要的权限。

这个原型的长期目标不只是本地验证，而是推动整个 ClawHub 生态为每个 skill 增加一层结构化安全边界描述：

- `Situation`
- `Action`
- `Permission`
- `Scope`

这样可以让 skill 的行为边界更容易被理解、审查和执行。要让这件事真正落地，必须依赖 OpenClaw 官方推动两件事：

- ClawHub 需要标准化或要求 `Situation | Action | Permission | Scope`
- OpenClaw 需要在运行时加入底层权限检查机制，在执行前做真正的边界校验

## 项目内容

- `scraper.py`
  从 ClawHub 抓取 skill 元数据和 `SKILL.md`

- `cluster_compiler.py`
  读取分组 skill 数据，并调用 LLM 生成：
  - workflow markdown
  - policy json

- `security_interceptor.py`
  在运行时执行文件、命令和通用 capability 拦截

## 核心流程

研究链路是：

1. 收集 skill 或任务数据
2. 生成任务或技能簇的 policy
3. 用 policy 约束后续运行

目标安全模型是：

- 收集轨迹或分组 skill 描述
- 推断任务专属权限画像
- 阻断超出画像边界的运行时操作

当前仓库是这个方向的最小原型。

## 权限分类

当前项目使用的权限词表包括：

- 文件系统：`read`, `write`, `edit`
- 计算执行：`exec`, `process`
- 网络：`web_search`, `web_fetch`, `browser`
- 多媒体：`image`, `pdf`, `canvas`, `tts`
- 调度通信：`cron`, `message`, `nodes`
- 智能体：`sessions_spawn`, `sessions_list`, `sessions_send`, `subagents`
- 系统：`gateway`, `memory_search`, `memory_get`

## 仓库内示例

仓库内已经包含运行后的示例结果，放在 `examples/` 下。

- `examples/compiler_input/`
  分组 skill 输入样例

- `examples/compiler_run/`
  compiler 输出样例

- `examples/interceptor_run/`
  interceptor 输入、归一化 policy、结果和审计日志

- `examples/scraper_run/output/`
  scraper 抓取结果样例

可直接查看的文件：

- `examples/compiler_run/query_results_codex_vibe_workflow.md`
- `examples/compiler_run/query_results_codex_vibe_workflow.policy.json`
- `examples/interceptor_run/policy.json`
- `examples/interceptor_run/normalized_policy.json`
- `examples/interceptor_run/result.json`
- `examples/interceptor_run/audit.jsonl`
- `examples/scraper_run/output/index.json`

## 环境变量

LLM 接口必须由用户自己配置。

代码中不包含默认的 API 地址或 API key。

```bash
export OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
export OPENAI_API_KEY=your_key
export SKILL_CLUSTERING_MODEL=google/gemini-3.1-flash-lite-preview
```

## 运行 scraper

```bash
python3 scraper.py -n 100 --output .
```

预期输出：

- `output/skills/*.md`
- `output/descriptions/*.json`
- `output/index.json`
- `output/index.csv`

## 运行 compiler

输入 json 格式：

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

运行：

```bash
python3 cluster_compiler.py --input /path/to/skills --output /path/to/generated
```

预期输出：

- 一个 markdown 文件，包含：
  - `cluster_type`
  - `query`
  - `workflow`
  - `Situation | Action | Permission | Scope`
- 一个 policy json 文件，包含：
  - `cluster_type`
  - `permissions`

说明：

- compiler 结果依赖外部模型服务
- 仓库中 `examples/compiler_run/` 是一次成功运行后的样例结果

## 运行 interceptor

运行：

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

预期结果：

- 合法文件访问返回 `method` 和 `path`
- 合法命令执行返回 `command`
- 合法 capability 返回 `capability` 和 `target`
- 被拦截操作返回：
  - `error`
  - `capability`
  - `reason`
  - `target`

interceptor 会先读取 compiler 输出的 policy，再在运行时归一化为 enforcement schema 后执行检查。
