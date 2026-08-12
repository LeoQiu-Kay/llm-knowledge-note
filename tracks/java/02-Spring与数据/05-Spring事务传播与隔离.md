---
slug: java-spring-transaction
title: Spring 事务传播与隔离
---
# Spring 事务传播与隔离

## 30 秒回答

Spring 声明式事务由代理和 TransactionManager 管理。传播行为决定嵌套调用如何加入、挂起或创建物理事务，隔离级别约束并发可见性；事务边界必须围绕一致性用例，并避免把慢 RPC 放入数据库事务。

## 核心原理

### 逻辑与物理事务

REQUIRED 的多个方法可形成多个逻辑事务范围但共享同一物理事务；内部范围标记 rollback-only 后，外层提交可能得到 UnexpectedRollbackException。

### REQUIRES_NEW 与 NESTED

REQUIRES_NEW 挂起外层并占用独立连接；NESTED 通常依赖保存点并仍处于同一物理事务。两者语义和连接池压力完全不同。

### 隔离与回滚规则

隔离级别最终受数据库支持；默认通常只对 RuntimeException 和 Error 回滚。自调用、private 方法和异常被吞都会让声明式事务偏离预期。

## 工程权衡

- 事务应尽量短，先完成外部准备再进入事务，提交后再异步触发非关键动作。
- REQUIRES_NEW 需要为并发外层事务额外预留连接，否则可能形成连接池死锁。
- 跨库、消息和远程服务不能仅靠本地 @Transactional，应使用 outbox、Saga 或补偿。

## 常见故障

1. 同类自调用绕过事务代理。
2. 捕获异常正常返回导致事务提交。
3. 事务中等待外部接口，锁和连接长期占用。

## 面试追问

- 逻辑与物理事务在高并发或大规模场景下还需要考虑什么？
- REQUIRES_NEW 与 NESTED在高并发或大规模场景下还需要考虑什么？
- 隔离与回滚规则在高并发或大规模场景下还需要考虑什么？
- 如何为Spring 事务传播与隔离设计压测、监控与回滚方案？

## 参考规范

- Spring Transaction Propagation：https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html
