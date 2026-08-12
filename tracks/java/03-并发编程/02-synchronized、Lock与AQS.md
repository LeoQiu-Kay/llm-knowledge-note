---
slug: java-lock-aqs
title: synchronized、Lock 与 AQS
---
# synchronized、Lock 与 AQS

## 30 秒回答

synchronized 提供结构化互斥和内存语义，Lock 提供可中断、超时、公平和多条件队列等能力；AQS 以同步状态、CAS 和等待队列支撑 ReentrantLock、Semaphore、CountDownLatch 等同步器。

## 核心原理

### 监视器与锁范围

进入 synchronized 前获取监视器，退出时释放并建立 happens-before。锁对象必须稳定且私有，临界区只覆盖共享不变量。

### AQS 队列

AQS 用 state 表示同步状态，获取失败的线程进入 FIFO 等待队列，并由子类定义独占或共享获取/释放逻辑。

### Condition 与中断

Condition 可建立多个条件等待队列；await 应放在 while 条件循环中处理虚假唤醒，并明确响应或恢复中断。

## 工程权衡

- 优先使用 synchronized 的结构化释放，只有需要高级能力时再用 Lock。
- 公平锁减少饥饿但降低吞吐，默认非公平锁通常更适合普通服务。
- 锁粒度过粗影响并发，过细则增加组合一致性和死锁难度。

## 常见故障

1. Lock 未放在 finally 中释放。
2. 不同路径按不同顺序获取多个锁形成死锁。
3. Condition 使用 if 而不是 while，虚假唤醒后破坏状态。

## 面试追问

- 监视器与锁范围在高并发或大规模场景下还需要考虑什么？
- AQS 队列在高并发或大规模场景下还需要考虑什么？
- Condition 与中断在高并发或大规模场景下还需要考虑什么？
- 如何为synchronized、Lock 与 AQS设计压测、监控与回滚方案？
