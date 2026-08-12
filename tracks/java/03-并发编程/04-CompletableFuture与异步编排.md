---
slug: java-completable-future
title: CompletableFuture 与异步编排
---
# CompletableFuture 与异步编排

## 30 秒回答

CompletableFuture 同时表达异步结果和依赖图，可串行转换、并行汇聚并统一处理异常。可靠编排要显式指定执行器、超时、取消与异常策略，并避免在公共 ForkJoinPool 中执行阻塞 I/O。

## 核心原理

### 阶段组合

thenApply 转换结果，thenCompose 展平依赖异步，thenCombine 合并独立结果；allOf 只表示完成，需要自行收集各阶段结果。

### 异常传播

阶段异常会包装进 CompletionException；exceptionally 用于恢复，handle 同时处理成功失败，whenComplete 更适合观察而非改变结果。

### 执行器与上下文

无 Async 后缀的阶段可能在完成前一阶段的线程执行；Async 默认可能使用公共池。MDC、安全上下文和追踪信息通常需要显式传播。

## 工程权衡

- 并行调用先看下游容量，不能把串行延迟问题变成下游雪崩。
- 为整条链路和单个分支设置不同超时，并决定部分成功是否可接受。
- 复杂业务流程超过可读阈值时应转为显式工作流或状态机。

## 常见故障

1. join 阻塞在同一小线程池中等待其子任务，形成线程饥饿死锁。
2. 异常被 exceptionally 吞掉并返回空值，后续逻辑误判成功。
3. 取消上层 Future 却没有传播到下游 RPC。

## 面试追问

- 阶段组合在高并发或大规模场景下还需要考虑什么？
- 异常传播在高并发或大规模场景下还需要考虑什么？
- 执行器与上下文在高并发或大规模场景下还需要考虑什么？
- 如何为CompletableFuture 与异步编排设计压测、监控与回滚方案？
