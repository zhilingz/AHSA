# agentic_coding_workflow

query: 一个向codex自动发送指令，并监控vibe coding动态的工作流

workflow: 构建一个以 Codex 后台任务为核心、以 Vibe Coding 状态监控和协作为辅助的自动化工作流：使用 codex-dev 负责向 Codex 自动发送开发指令并保存日志/补丁产物；使用 vibe-3k 约束任务进入 PLAN/ACT 分离、状态跟踪与验收；可选结合 Feishu 做通知与看板同步，结合 multi-agent-cn 或 multi-team-coding 做多任务拆分与并行执行，结合 cron-job-guardian 审查定时触发配置的频率、重试、幂等与日志策略。整体流程为：接收任务 -> 生成/校验 Vibe Coding 计划 -> 投递 Codex 后台作业 -> 记录 receipt、日志、patch artifacts -> 监控任务动态与阶段状态 -> 完成后通知/汇总 -> 人工或自动进入验收与后续迭代。

| Situation | Action | Permission | Scope |
| --- | --- | --- | --- |
| 用户希望自动向 Codex 发送编码、重构、修复或执行类指令，并希望任务在本地后台运行且可追踪。 | 启用 codex-dev 创建后台本地任务，立即返回 receipt，指定 workdir，保存日志和 patch artifacts，作为主执行通道。 | run_codex_background_jobs, write_task_logs, write_patch_artifacts, read_workdir, write_workdir | local_workdir, codex_job_runtime, task_logs, patch_artifacts |
| 用户提到需要监控 vibe coding 动态、阶段推进、PLAN/ACT 分离、故障恢复或 AI 编码规范。 | 应用 vibe-3k 作为流程规范层，对任务进行计划拆分、执行阶段标记、状态回写、故障恢复和验收检查。 | read_project_rules, write_project_rules, read_task_state, write_task_state | project_rule_files, workflow_state, acceptance_checklist |
| 用户希望在任务完成、失败或关键阶段变化时收到消息提醒，或把动态同步到协作平台。 | 使用 Feishu 发送任务状态通知、日报摘要、异常提醒，必要时同步文档、表格或群消息。 | send_notifications, read_notification_targets, write_collaboration_updates | feishu_messages, feishu_docs, feishu_tables, status_recipients |
| 用户希望将一个大任务拆成多个子任务并行执行，统一监控多个 Codex/Vibe Coding 动态。 | 使用 multi-agent-cn 或 multi-team-coding 做任务拆分、并行调度和状态聚合，由主流程统一汇总进度和产出。 | spawn_subtasks, coordinate_multi_agent_sessions, read_subtask_status, aggregate_results | agent_sessions, parallel_task_queue, aggregated_status_board |
| 用户要把该工作流做成定时任务或长期守护流程，需要避免频率、并发、幂等和日志策略问题。 | 使用 cron-job-guardian 审查计划任务配置，确保触发频率合理、支持重试和日志留存，避免把高风险或不幂等任务直接做成失控定时器。 | read_scheduler_config, validate_cron_safety, read_job_logs | cron_config, timer_config, scheduler_logs |
