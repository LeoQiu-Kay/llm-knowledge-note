---
slug: java-spring-transaction
title: Spring 事务传播与隔离
---
# Spring 事务传播与隔离

> **先记住**：Spring 声明式事务由代理和 TransactionManager 管理。

---

## 1. 它在解决什么问题？

Spring 声明式事务由代理和 TransactionManager 管理。传播行为决定嵌套调用如何加入、挂起或创建物理事务，隔离级别约束并发可见性；事务边界必须围绕一致性用例，并避免把慢 RPC 放入数据库事务。

读这一节时，先带着三个问题：

1. **核心对象是什么？** 哪些状态会在处理过程中发生变化？
2. **主链路怎么走？** 一次处理从哪里开始，到哪里才算结束？
3. **边界在哪里？** 数据量、并发或故障出现后，哪一环最先承压？

---

## 2. 先看全貌

![REQUIRED 传播下的事务边界](./assets/spring_tx_required.png)

<p class="diagram-caption">先建立整体位置感：代理拦截 @Transactional 方法 → 事务管理器获取连接并开启事务 → 内层调用按传播行为加入或新建事务 → 提交并释放连接</p>

### 主链路

```text
[代理拦截 @Transactional 方法]
    │
    ▼
[事务管理器获取连接并开启事务]
    │
    ▼
[内层调用按传播行为加入或新建事务]
    │
    ▼
[异常触发回滚规则]
    │
    ▼
[提交并释放连接]
```

先把这条链路记住即可。接下来再逐层拆开每一步为什么这样设计。

---

## 3. 核心机制，逐层拆开

### 逻辑与物理事务

REQUIRED 的多个方法可形成多个逻辑事务范围但共享同一物理事务；内部范围标记 rollback-only 后，外层提交可能得到 UnexpectedRollbackException。

### REQUIRES_NEW 与 NESTED

REQUIRES_NEW 挂起外层并占用独立连接；NESTED 通常依赖保存点并仍处于同一物理事务。两者语义和连接池压力完全不同。

### 隔离与回滚规则

隔离级别最终受数据库支持；默认通常只对 RuntimeException 和 Error 回滚。自调用、private 方法和异常被吞都会让声明式事务偏离预期。

---

## 4. 用一段实现把概念落地

下面只保留最关键的主干。阅读时，把代码与上一节的流程一一对应：

```java
@Transactional
public void placeOrder(Command command) {
    orderRepository.insert(command.order());
    outboxRepository.append(OrderPlaced.from(command));
}

@Transactional(propagation = Propagation.REQUIRES_NEW)
public void writeAudit(AuditEvent event) {
    auditRepository.insert(event);
}

// 注意：同类内部 this.writeAudit(...) 不经过代理。
```

### 对照着看

- **从哪里开始**：代理拦截 @Transactional 方法
- **关键状态变化**：内层调用按传播行为加入或新建事务
- **怎样才算完成**：提交并释放连接

---

## 5. 怎么选才不容易错

| 关注点 | 怎么理解 | 怎么验证 |
|---|---|---|
| **边界** | 明确容器、代理、Web、事务和数据访问各自负责什么 | 避免把业务规则藏进框架回调 |
| **代理** | 说明哪些调用会穿过代理，哪些会绕过 | 用集成测试覆盖 self-invocation、final 与异常路径 |
| **数据** | 从索引访问路径、事务边界和连接占用解释性能 | 核对执行计划、锁等待与连接池指标 |
| **可替换性** | 抽象应允许测试替身和实现替换 | 避免全局静态访问与过度自动配置 |

没有脱离场景的“最佳方案”。先写清数据规模、读写比例、故障模型和延迟目标，再做选择。

---

## 6. 放进真实系统，还要考虑什么

- 事务应尽量短，先完成外部准备再进入事务，提交后再异步触发非关键动作。
- REQUIRES_NEW 需要为并发外层事务额外预留连接，否则可能形成连接池死锁。
- 跨库、消息和远程服务不能仅靠本地 @Transactional，应使用 outbox、Saga 或补偿。

### 上线前检查

- 用集成测试验证代理、事务、MVC 与数据库真实边界。
- 配置提供默认值、校验、版本和回滚，不把环境差异写死。
- 监控连接池、慢 SQL、事务时长、错误分类和请求 Trace。
- 对自动装配和动态 SQL 保留可解释的启动报告与执行计划。

---

## 7. 常见误区与排查

### 容易踩的坑

1. 同类自调用绕过事务代理。
2. 捕获异常正常返回导致事务提交。
3. 事务中等待外部接口，锁和连接长期占用。

### 出现问题时，按这个顺序看

1. **还原现场**：确认受影响的请求、数据、时间窗，以及最近是否有发布或流量变化。
2. **沿链路定位**：从“代理拦截 @Transactional 方法”一路检查到“提交并释放连接”，找出状态第一次偏离预期的位置。
3. **验证修复**：用最小复现、压力测试或故障注入证明问题消失，同时保留回滚方案。

---

## 8. 延伸阅读

- Spring Transaction Propagation：https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html

---

## 9. 最后做一次复盘

> **一句话**：Spring 声明式事务由代理和 TransactionManager 管理。
>
> **主链路**：代理拦截 @Transactional 方法 → 事务管理器获取连接并开启事务 → 内层调用按传播行为加入或新建事务 → 异常触发回滚规则 → 提交并释放连接
>
> **关键状态**：内层调用按传播行为加入或新建事务
>
> **最容易踩的坑**：同类自调用绕过事务代理。

---

## 10. 高频追问

### Q1. 请用一分钟说明Spring 事务传播与隔离的核心目标与工作机制。

Spring 声明式事务由代理和 TransactionManager 管理。传播行为决定嵌套调用如何加入、挂起或创建物理事务，隔离级别约束并发可见性；事务边界必须围绕一致性用例，并避免把慢 RPC 放入数据库事务。

### Q2. 逻辑与物理事务的核心机制是什么？

REQUIRED 的多个方法可形成多个逻辑事务范围但共享同一物理事务；内部范围标记 rollback-only 后，外层提交可能得到 UnexpectedRollbackException。

### Q3. REQUIRES_NEW 与 NESTED为什么重要，实际如何落地？

REQUIRES_NEW 挂起外层并占用独立连接；NESTED 通常依赖保存点并仍处于同一物理事务。两者语义和连接池压力完全不同。

### Q4. Spring 事务传播与隔离在工程落地时如何做取舍？

事务应尽量短，先完成外部准备再进入事务，提交后再异步触发非关键动作；REQUIRES_NEW 需要为并发外层事务额外预留连接，否则可能形成连接池死锁；跨库、消息和远程服务不能仅靠本地 @Transactional，应使用 outbox、Saga 或补偿。

### Q5. Spring 事务传播与隔离最常见的故障与排查重点是什么？

同类自调用绕过事务代理；捕获异常正常返回导致事务提交；事务中等待外部接口，锁和连接长期占用。排查时应先用指标和日志确认现象，再缩小到线程、资源、依赖或数据边界。
