---
slug: java-lock-aqs
title: synchronized、Lock 与 AQS
---
# synchronized、Lock 与 AQS

> **先记住**：synchronized 提供结构化互斥和内存语义，Lock 提供可中断、超时、公平和多条件队列等能力；AQS 以同步状态、CAS 和等待队列支撑 ReentrantLock、Semaphore、CountDownLatch 等同步器。

---

## 1. 它在解决什么问题？

synchronized 提供结构化互斥和内存语义，Lock 提供可中断、超时、公平和多条件队列等能力；AQS 以同步状态、CAS 和等待队列支撑 ReentrantLock、Semaphore、CountDownLatch 等同步器。

读这一节时，先带着三个问题：

1. **核心对象是什么？** 哪些状态会在处理过程中发生变化？
2. **主链路怎么走？** 一次处理从哪里开始，到哪里才算结束？
3. **边界在哪里？** 数据量、并发或故障出现后，哪一环最先承压？

---

## 2. 先看全貌

![并发更新中的竞争窗口](./assets/lock_free_list.png)

<p class="diagram-caption">先建立整体位置感：线程尝试 CAS 获取同步状态 → 失败后封装为节点入队 → 前驱释放时唤醒后继 → finally 释放状态并传播唤醒</p>

### 主链路

```text
[线程尝试 CAS 获取同步状态]
    │
    ▼
[失败后封装为节点入队]
    │
    ▼
[前驱释放时唤醒后继]
    │
    ▼
[线程重试并获得锁]
    │
    ▼
[finally 释放状态并传播唤醒]
```

先把这条链路记住即可。接下来再逐层拆开每一步为什么这样设计。

---

## 3. 核心机制，逐层拆开

### 监视器与锁范围

进入 synchronized 前获取监视器，退出时释放并建立 happens-before。锁对象必须稳定且私有，临界区只覆盖共享不变量。

### AQS 队列

AQS 用 state 表示同步状态，获取失败的线程进入 FIFO 等待队列，并由子类定义独占或共享获取/释放逻辑。

### Condition 与中断

Condition 可建立多个条件等待队列；await 应放在 while 条件循环中处理虚假唤醒，并明确响应或恢复中断。

---

## 4. 用一段实现把概念落地

下面只保留最关键的主干。阅读时，把代码与上一节的流程一一对应：

```java
private final Lock lock = new ReentrantLock();
private final Condition notEmpty = lock.newCondition();

E take() throws InterruptedException {
    lock.lockInterruptibly();
    try {
        while (queue.isEmpty()) notEmpty.await();
        return queue.removeFirst();
    } finally {
        lock.unlock();
    }
}
```

### 对照着看

- **从哪里开始**：线程尝试 CAS 获取同步状态
- **关键状态变化**：前驱释放时唤醒后继
- **怎样才算完成**：finally 释放状态并传播唤醒

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

- 优先使用 synchronized 的结构化释放，只有需要高级能力时再用 Lock。
- 公平锁减少饥饿但降低吞吐，默认非公平锁通常更适合普通服务。
- 锁粒度过粗影响并发，过细则增加组合一致性和死锁难度。

### 上线前检查

- 队列、等待、重试和并发度全部有界。
- 中断、取消、超时沿调用链传播，finally 释放锁与资源。
- 按依赖隔离执行器，避免一个慢下游占满全部线程。
- 压测同时观察吞吐、排队、上下文切换、锁竞争和尾延迟。

---

## 7. 常见误区与排查

### 容易踩的坑

1. Lock 未放在 finally 中释放。
2. 不同路径按不同顺序获取多个锁形成死锁。
3. Condition 使用 if 而不是 while，虚假唤醒后破坏状态。

### 出现问题时，按这个顺序看

1. **还原现场**：确认受影响的请求、数据、时间窗，以及最近是否有发布或流量变化。
2. **沿链路定位**：从“线程尝试 CAS 获取同步状态”一路检查到“finally 释放状态并传播唤醒”，找出状态第一次偏离预期的位置。
3. **验证修复**：用最小复现、压力测试或故障注入证明问题消失，同时保留回滚方案。

---

## 8. 最后做一次复盘

> **一句话**：synchronized 提供结构化互斥和内存语义，Lock 提供可中断、超时、公平和多条件队列等能力；AQS 以同步状态、CAS 和等待队列支撑 ReentrantLock、Semaphore、CountDownLatch 等同步器。
>
> **主链路**：线程尝试 CAS 获取同步状态 → 失败后封装为节点入队 → 前驱释放时唤醒后继 → 线程重试并获得锁 → finally 释放状态并传播唤醒
>
> **关键状态**：前驱释放时唤醒后继
>
> **最容易踩的坑**：Lock 未放在 finally 中释放。

---

## 9. 高频追问

### Q1. 请用一分钟说明synchronized、Lock 与 AQS的核心目标与工作机制。

synchronized 提供结构化互斥和内存语义，Lock 提供可中断、超时、公平和多条件队列等能力；AQS 以同步状态、CAS 和等待队列支撑 ReentrantLock、Semaphore、CountDownLatch 等同步器。

### Q2. 监视器与锁范围的核心机制是什么？

进入 synchronized 前获取监视器，退出时释放并建立 happens-before。锁对象必须稳定且私有，临界区只覆盖共享不变量。

### Q3. AQS 队列为什么重要，实际如何落地？

AQS 用 state 表示同步状态，获取失败的线程进入 FIFO 等待队列，并由子类定义独占或共享获取/释放逻辑。

### Q4. synchronized、Lock 与 AQS在工程落地时如何做取舍？

优先使用 synchronized 的结构化释放，只有需要高级能力时再用 Lock；公平锁减少饥饿但降低吞吐，默认非公平锁通常更适合普通服务；锁粒度过粗影响并发，过细则增加组合一致性和死锁难度。

### Q5. synchronized、Lock 与 AQS最常见的故障与排查重点是什么？

Lock 未放在 finally 中释放；不同路径按不同顺序获取多个锁形成死锁；Condition 使用 if 而不是 while，虚假唤醒后破坏状态。排查时应先用指标和日志确认现象，再缩小到线程、资源、依赖或数据边界。
