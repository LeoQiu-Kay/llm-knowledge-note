---
slug: java-completable-future
title: CompletableFuture 与异步编排 · 面试题
---
# CompletableFuture 与异步编排 · 面试题

## Q1: 请用一分钟说明CompletableFuture 与异步编排的核心目标与工作机制。
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

CompletableFuture 同时表达异步结果和依赖图，可串行转换、并行汇聚并统一处理异常。可靠编排要显式指定执行器、超时、取消与异常策略，并避免在公共 ForkJoinPool 中执行阻塞 I/O。

---

## Q2: 阶段组合的核心机制是什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

thenApply 转换结果，thenCompose 展平依赖异步，thenCombine 合并独立结果；allOf 只表示完成，需要自行收集各阶段结果。

---

## Q3: 异常传播为什么重要，实际如何落地？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

阶段异常会包装进 CompletionException；exceptionally 用于恢复，handle 同时处理成功失败，whenComplete 更适合观察而非改变结果。

---

## Q4: CompletableFuture 与异步编排在工程落地时如何做取舍？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

并行调用先看下游容量，不能把串行延迟问题变成下游雪崩；为整条链路和单个分支设置不同超时，并决定部分成功是否可接受；复杂业务流程超过可读阈值时应转为显式工作流或状态机。

---

## Q5: CompletableFuture 与异步编排最常见的故障与排查重点是什么？
> 难度 ⭐⭐⭐⭐ ｜ 高频 🔥🔥

join 阻塞在同一小线程池中等待其子任务，形成线程饥饿死锁；异常被 exceptionally 吞掉并返回空值，后续逻辑误判成功；取消上层 Future 却没有传播到下游 RPC。排查时应先用指标和日志确认现象，再缩小到线程、资源、依赖或数据边界。
