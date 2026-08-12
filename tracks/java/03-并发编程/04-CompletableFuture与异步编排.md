---
slug: java-completable-future
title: CompletableFuture 与异步编排
---
# CompletableFuture 与异步编排

> **先记住**：CompletableFuture 同时表达异步结果和依赖图，可串行转换、并行汇聚并统一处理异常。

---

## 1. 它在解决什么问题？

CompletableFuture 同时表达异步结果和依赖图，可串行转换、并行汇聚并统一处理异常。可靠编排要显式指定执行器、超时、取消与异常策略，并避免在公共 ForkJoinPool 中执行阻塞 I/O。

读这一节时，先带着三个问题：

1. **核心对象是什么？** 哪些状态会在处理过程中发生变化？
2. **主链路怎么走？** 一次处理从哪里开始，到哪里才算结束？
3. **边界在哪里？** 数据量、并发或故障出现后，哪一环最先承压？

---

## 2. 先看全貌

![异步任务依赖与结果汇总](./assets/task_orchestration.png)

<p class="diagram-caption">先建立整体位置感：创建异步阶段 → 独立 I/O 并行执行 → thenCompose / thenCombine 建立依赖 → 超时或取消后汇总结果</p>

### 主链路

```text
[创建异步阶段]
    │
    ▼
[独立 I/O 并行执行]
    │
    ▼
[thenCompose / thenCombine 建立依赖]
    │
    ▼
[异常沿链传播并集中恢复]
    │
    ▼
[超时或取消后汇总结果]
```

先把这条链路记住即可。接下来再逐层拆开每一步为什么这样设计。

---

## 3. 核心机制，逐层拆开

### 阶段组合

thenApply 转换结果，thenCompose 展平依赖异步，thenCombine 合并独立结果；allOf 只表示完成，需要自行收集各阶段结果。

### 异常传播

阶段异常会包装进 CompletionException；exceptionally 用于恢复，handle 同时处理成功失败，whenComplete 更适合观察而非改变结果。

### 执行器与上下文

无 Async 后缀的阶段可能在完成前一阶段的线程执行；Async 默认可能使用公共池。MDC、安全上下文和追踪信息通常需要显式传播。

---

## 4. 用一段实现把概念落地

下面只保留最关键的主干。阅读时，把代码与上一节的流程一一对应：

```java
CompletableFuture<User> user =
    CompletableFuture.supplyAsync(() -> userClient.get(id), ioPool);
CompletableFuture<List<Order>> orders =
    CompletableFuture.supplyAsync(() -> orderClient.list(id), ioPool);

return user.thenCombine(orders, UserPage::new)
           .orTimeout(800, TimeUnit.MILLISECONDS)
           .exceptionally(error -> fallback(id, error))
           .join();
```

### 对照着看

- **从哪里开始**：创建异步阶段
- **关键状态变化**：thenCompose / thenCombine 建立依赖
- **怎样才算完成**：超时或取消后汇总结果

---

## 5. 怎么选才不容易错

| 关注点 | 怎么理解 | 怎么验证 |
|---|---|---|
| **正确性** | 先定义共享状态、不变量和 happens-before | 用压力测试、竞态测试和线程转储验证 |
| **吞吐** | 线程数不能突破 CPU、连接池和下游容量 | 观察排队时间而非只看完成量 |
| **延迟** | 区分锁等待、队列等待、I/O 等待和调度 | 记录 p95/p99 与超时、取消传播 |
| **故障隔离** | 任务必须有界、可取消、可拒绝 | 按依赖拆池，禁止无限队列与无限重试 |

没有脱离场景的“最佳方案”。先写清数据规模、读写比例、故障模型和延迟目标，再做选择。

---

## 6. 放进真实系统，还要考虑什么

- 并行调用先看下游容量，不能把串行延迟问题变成下游雪崩。
- 为整条链路和单个分支设置不同超时，并决定部分成功是否可接受。
- 复杂业务流程超过可读阈值时应转为显式工作流或状态机。

### 上线前检查

- 队列、等待、重试和并发度全部有界。
- 中断、取消、超时沿调用链传播，finally 释放锁与资源。
- 按依赖隔离执行器，避免一个慢下游占满全部线程。
- 压测同时观察吞吐、排队、上下文切换、锁竞争和尾延迟。

---

## 7. 常见误区与排查

### 容易踩的坑

1. join 阻塞在同一小线程池中等待其子任务，形成线程饥饿死锁。
2. 异常被 exceptionally 吞掉并返回空值，后续逻辑误判成功。
3. 取消上层 Future 却没有传播到下游 RPC。

### 出现问题时，按这个顺序看

1. **还原现场**：确认受影响的请求、数据、时间窗，以及最近是否有发布或流量变化。
2. **沿链路定位**：从“创建异步阶段”一路检查到“超时或取消后汇总结果”，找出状态第一次偏离预期的位置。
3. **验证修复**：用最小复现、压力测试或故障注入证明问题消失，同时保留回滚方案。

---

## 8. 最后做一次复盘

> **一句话**：CompletableFuture 同时表达异步结果和依赖图，可串行转换、并行汇聚并统一处理异常。
>
> **主链路**：创建异步阶段 → 独立 I/O 并行执行 → thenCompose / thenCombine 建立依赖 → 异常沿链传播并集中恢复 → 超时或取消后汇总结果
>
> **关键状态**：thenCompose / thenCombine 建立依赖
>
> **最容易踩的坑**：join 阻塞在同一小线程池中等待其子任务，形成线程饥饿死锁。

---

## 9. 高频追问

### Q1. 请用一分钟说明CompletableFuture 与异步编排的核心目标与工作机制。

CompletableFuture 同时表达异步结果和依赖图，可串行转换、并行汇聚并统一处理异常。可靠编排要显式指定执行器、超时、取消与异常策略，并避免在公共 ForkJoinPool 中执行阻塞 I/O。

### Q2. 阶段组合的核心机制是什么？

thenApply 转换结果，thenCompose 展平依赖异步，thenCombine 合并独立结果；allOf 只表示完成，需要自行收集各阶段结果。

### Q3. 异常传播为什么重要，实际如何落地？

阶段异常会包装进 CompletionException；exceptionally 用于恢复，handle 同时处理成功失败，whenComplete 更适合观察而非改变结果。

### Q4. CompletableFuture 与异步编排在工程落地时如何做取舍？

并行调用先看下游容量，不能把串行延迟问题变成下游雪崩；为整条链路和单个分支设置不同超时，并决定部分成功是否可接受；复杂业务流程超过可读阈值时应转为显式工作流或状态机。

### Q5. CompletableFuture 与异步编排最常见的故障与排查重点是什么？

join 阻塞在同一小线程池中等待其子任务，形成线程饥饿死锁；异常被 exceptionally 吞掉并返回空值，后续逻辑误判成功；取消上层 Future 却没有传播到下游 RPC。排查时应先用指标和日志确认现象，再缩小到线程、资源、依赖或数据边界。
