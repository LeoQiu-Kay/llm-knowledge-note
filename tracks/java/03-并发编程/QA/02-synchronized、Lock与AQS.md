---
slug: java-lock-aqs
title: synchronized、Lock 与 AQS · 面试题
---
# synchronized、Lock 与 AQS · 面试题

## Q1: 请用一分钟说明synchronized、Lock 与 AQS的核心目标与工作机制。
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

synchronized 提供结构化互斥和内存语义，Lock 提供可中断、超时、公平和多条件队列等能力；AQS 以同步状态、CAS 和等待队列支撑 ReentrantLock、Semaphore、CountDownLatch 等同步器。

---

## Q2: 监视器与锁范围的核心机制是什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

进入 synchronized 前获取监视器，退出时释放并建立 happens-before。锁对象必须稳定且私有，临界区只覆盖共享不变量。

---

## Q3: AQS 队列为什么重要，实际如何落地？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

AQS 用 state 表示同步状态，获取失败的线程进入 FIFO 等待队列，并由子类定义独占或共享获取/释放逻辑。

---

## Q4: synchronized、Lock 与 AQS在工程落地时如何做取舍？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

优先使用 synchronized 的结构化释放，只有需要高级能力时再用 Lock；公平锁减少饥饿但降低吞吐，默认非公平锁通常更适合普通服务；锁粒度过粗影响并发，过细则增加组合一致性和死锁难度。

---

## Q5: synchronized、Lock 与 AQS最常见的故障与排查重点是什么？
> 难度 ⭐⭐⭐⭐ ｜ 高频 🔥🔥

Lock 未放在 finally 中释放；不同路径按不同顺序获取多个锁形成死锁；Condition 使用 if 而不是 while，虚假唤醒后破坏状态。排查时应先用指标和日志确认现象，再缩小到线程、资源、依赖或数据边界。
