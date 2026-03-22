# agentic_coding_monitoring

query: 一个向codex自动发送指令，并监控vibe coding动态的工作流

workflow: 使用 codex-dev 作为后台 Codex 指令执行器，接收立即回执并保存日志；用 schedule.cron 建立定时监控任务，周期性检查 Codex 任务日志、补丁产物和 vibe coding 相关开发动态；如需团队编排，可结合 multi-agent-cn 或 feishu-ai-coding-assistant 做任务分发与状态汇总；通过 feishu 在关键事件（启动、完成、失败、异常）时发送消息通知。监控以本地日志与任务状态为主，若需外部开发动态补充，可按需启用 web_search/web_fetch。

| Situation | Action | Permission | Scope |
| --- | --- | --- | --- |
| 用户要求自动向 Codex 发送开发/重构/测试类指令，并异步运行 | 调用 codex-dev 将指令作为后台本地任务启动，记录 workdir、日志路径、任务回执和补丁产物位置 | exec, process, write, read | compute, filesystem |
| 用户要求持续监控 vibe coding 动态，包含任务进度、日志变化、产物更新 | 创建定时轮询工作流，周期读取本地日志、任务状态和补丁文件变化，生成进度摘要 | cron, read, process | schedule, filesystem, compute |
| 用户要求在任务完成、失败或异常时自动通知 | 通过 Feishu 或消息节点发送状态通知，附带任务摘要、日志路径和下一步建议 | message, read | schedule, filesystem |
| 用户要求并行跟踪多个 coding 子任务或多个 Codex 会话 | 使用 sessions_spawn 创建子会话分别下发指令，定期汇总各会话状态并输出统一看板摘要 | sessions_spawn, sessions_list, sessions_send, subagents | agent |
| 用户要求补充外部的 vibe coding 最佳实践、社区动态或相关资料 | 按需执行网页搜索与抓取，提炼与当前任务相关的最佳实践、故障处理经验或规范更新 | web_search, web_fetch | network |
| 用户要求将监控策略做成稳定可复用的长期运行工作流 | 固化为 cron 计划任务，设置执行频率、日志落盘、重试和幂等规则，并避免高风险自动外发 | cron, write, read | schedule, filesystem |
