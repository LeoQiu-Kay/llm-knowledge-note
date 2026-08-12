---
slug: agent-observability
title: Trace、日志、指标与告警
---
# Trace、日志、指标与告警

## 30 秒回答

Agent 可观测性要把一次 run 下的模型调用、检索、工具、审批、子 Agent 和状态转移串成 Trace，并用结构化日志解释事件、指标监控趋势。除延迟和错误率，还需跟踪任务成功、循环、拒答、工具副作用、token 与成本；语义约定仍在演进，内部 schema 应版本化。

## 核心原理

### Trace 模型

run 作为根 span，model、tool、retrieval、approval 和 workflow node 作为子 span，记录状态、版本、耗时、token 和关联 ID。跨队列传播 trace context，异步恢复仍能连接原任务。

### 日志与指标

日志保存结构化事件和错误上下文，指标聚合成功率、P95/P99、队列、循环次数、工具错误、缓存命中和单位成功成本。高基数字段进入 trace/log，不直接作为指标 label。

### 质量与告警

建立面向用户结果的 SLI，如任务完成率、正确引用率和人工接管率。告警结合错误预算与异常基线，严重写操作、越权拒绝和数据外发单独设安全告警。

## 工程权衡

- 保存完整提示便于调试但风险高，生产默认脱敏、采样和分级访问。
- 全量 trace 成本高，可对错误、高价值任务和异常行为提高采样率。
- 标准语义便于跨平台，当前 GenAI Agent Spans 仍在开发阶段，内部适配层要隔离变化。

## 常见故障

1. 只记录最终答案，无法定位具体工具和证据。
2. 模型名、用户 ID 等高基数字段作为指标标签导致时序库膨胀。
3. 异步 worker 未传播 trace context，长任务链路断裂。

## 面试追问

- Trace 模型在生产环境中如何验证效果？
- 日志与指标在生产环境中如何验证效果？
- 质量与告警在生产环境中如何验证效果？
- 如何为Trace、日志、指标与告警设计评测、监控与回滚方案？

## 参考规范

- OpenTelemetry GenAI Agent Spans：https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
