# AHSA

[English](./README.md)

## 摘要

AHSA 的全称是 Ad Hoc Sandboxed Agent。

它是一个面向 AI 智能体技能安全的零信任执行研究原型。

核心思想是：

- 一个具体任务实际需要的权限，只是系统全量权限的严格子集
- 这个子集可以通过执行轨迹近似推断
- 后续正式执行应当被约束在该任务专属的能力边界内

AHSA 分为 3 个阶段：

1. trace run
2. profile generation
3. sandboxed execution

## 问题定义

现代 AI agent 可以读文件、执行命令、调用工具、访问外部服务。

这带来 3 类核心风险：

- 恶意第三方技能
- prompt injection
- 模型规划错误

根本问题是权限过宽：

- 任务所需权限远小于系统全量权限
- 但现有 agent 框架通常以更大的权限运行

AHSA 的目标是把安全边界从 prompt 级软约束，移动到代码级硬约束。

## 研究问题

### 形式化目标

给定：

- 任务 `T`
- 智能体 `A`
- 全能力集合 `C`

AHSA 希望近似得到一个任务专属能力画像 `P(T, A)`，满足：

- `P(T, A) ⊆ C`
- `P(T, A)` 只包含完成任务 `T` 所需权限

### 核心问题

- 如何收集一个任务的代表性执行轨迹
- 如何把轨迹转换成稳定的 capability profile
- 如何在运行时高效执行 profile 约束
- 如何降低误拦截和漏拦截

## 架构

AHSA 有 2 层：

- policy layer
- enforcement layer

### policy layer

这一层负责：

- 收集分组后的 skill 或任务数据
- 提取 workflow 结构
- 将 workflow 映射为 `Situation | Action | Permission | Scope`
- 编译为 policy json

### enforcement layer

这一层负责：

- 按路径规则检查文件访问
- 按黑名单和开关检查命令执行
- 按目标范围检查通用 capability
- 阻断超出 profile 的操作
- 对 pass 和 block 写审计日志

## 三阶段机制

### phase 1: trace run

在受控环境中执行任务并记录：

- tool 调用
- 文件读写
- 网络请求
- 命令执行
- 输入和输出之间的数据流

### phase 2: profile generation

从轨迹生成 capability profile：

- 聚合观测到的动作
- 将精确资源泛化为可复用的 scope 模式
- 移除冗余或明显无关的权限

示例 policy 结构：

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

每次运行时操作发生前：

- 规范化目标
- 检查是否在 profile 内
- 执行 allow、block 或 escalate

当前原型已经支持：

- 文件系统拦截
- 命令拦截
- 通用 capability 检查
- 审计日志

## 权限分类

- 文件系统：`read`, `write`, `edit`
- 计算执行：`exec`, `process`
- 网络浏览：`web_search`, `web_fetch`, `browser`
- 多媒体：`image`, `pdf`, `canvas`, `tts`
- 调度通信：`cron`, `message`, `nodes`
- 智能体能力：`sessions_spawn`, `sessions_list`, `sessions_send`, `subagents`
- 系统能力：`gateway`, `memory_search`, `memory_get`

## 核心挑战

### 轨迹覆盖不完整

有限次运行可能漏掉合法操作。

可行方向：

- 使用更多样化输入
- 估计轨迹覆盖率
- 从精确资源泛化到语义 scope
- 在监督下动态更新 profile

### profile 污染

如果 trace 环境被污染，生成的 profile 可能继承恶意权限。

可行方向：

- 使用隔离的 trace 环境
- 人工审查 profile
- 用任务先验约束校验 profile
- 多次独立 trace 交叉验证

### 间接注入残余风险

即使每一步单独都合法，攻击者仍可能通过合法步骤组合完成恶意目标。

可行方向：

- 约束操作序列模式
- 跟踪输入到输出的数据流
- 与输入层 injection 防御协同
- 验证当前动作是否与原始任务语义一致

## 预期贡献

### 研究贡献

- 面向 agent 的任务专属 capability profile 概念
- trace 到 profile 再到 sandbox 的完整链路
- profile 精度与覆盖率的评估框架
- skill 与 capability 分析数据集

### 工程贡献

- ClawHub 技能抓取器
- 基于 LLM 的 policy 编译器
- 运行时安全拦截器
- 可审计的 agent 执行边界

## 路线图

### phase 0

- 文献调研
- 形式化定义
- 原型设计

### phase 1

- 实现 trace 收集
- 构建 skill 与元数据数据集

### phase 2

- 实现 profile generation
- 增强语义泛化能力

### phase 3

- 实现运行时 enforcement
- 增加 policy enforcement point

### evaluation

- 构建测试集
- 测量 false positive 和 false negative
- 进行攻击实验

## 文件

- `scraper.py`: 抓取 ClawHub skill 元数据和 `SKILL.md`
- `cluster_compiler.py`: 读取分组 skill json，用 LLM 生成 workflow markdown 和 policy json
- `security_interceptor.py`: 在运行前执行文件、命令和 capability 拦截

## 环境变量

```bash
export OPENAI_BASE_URL=https://ie-crs.haoxiang.ai/v1
export OPENAI_API_KEY=your_key
export SKILL_CLUSTERING_MODEL=google/gemini-3.1-flash-lite-preview
```

## 运行 scraper

```bash
python3 scraper.py -n 100 --output .
```

输出：

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

输出：

- `generated/*.md`
- `generated/*.policy.json`

## 运行 interceptor

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

## 当前状态

这个仓库是一个与 AHSA 研究方案对齐的最小原型。

当前已包含：

- 数据集构建
- 基于 LLM 的 policy 编译
- 运行时 policy enforcement

当前还未包含：

- 完整 trace-run 基础设施
- 超出当前 prompt 输出能力的语义泛化
- hitl 审批流
- benchmark 自动化
