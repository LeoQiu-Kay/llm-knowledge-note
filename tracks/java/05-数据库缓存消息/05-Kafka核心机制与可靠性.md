---
slug: java-kafka-reliability
title: Kafka 核心机制与可靠性
---
# Kafka 核心机制与可靠性

## 30 秒回答

Kafka 以分区追加日志实现高吞吐和顺序读写，副本机制提供容错，消费组让同一分区在组内由一个消费者处理。可靠性要联合配置生产确认、幂等、事务、复制、消费位点和下游幂等，不能笼统声称端到端 exactly-once。

## 核心原理

### 分区与消费组

分区是并行和局部有序的单位；组内消费者通过协调器分配分区。扩缩容会触发 rebalance，处理时间和位点提交必须配合。

### 生产可靠性

acks、min.insync.replicas、重试和幂等生产者共同决定丢失与重复风险；事务生产者可原子写多个分区并提交消费位点。

### 消费语义

先提交位点再处理可能丢数据，处理后提交可能重复。跨 Kafka 外部数据库的端到端一致性仍需幂等、outbox/inbox 或事务协调。

## 工程权衡

- 分区数决定并行上限和元数据成本，扩分区会改变 key 到分区映射。
- 追求低延迟与批量吞吐需权衡 linger、batch 和压缩。
- 消息保留、重放和 schema 演进应作为数据产品治理。

## 常见故障

1. 消费者处理超过 max.poll.interval 导致频繁 rebalance。
2. 只依赖 Kafka 幂等生产者，却在数据库落库时产生重复。
3. 热点 key 让单分区积压。

## 面试追问

- 分区与消费组在高并发或大规模场景下还需要考虑什么？
- 生产可靠性在高并发或大规模场景下还需要考虑什么？
- 消费语义在高并发或大规模场景下还需要考虑什么？
- 如何为Kafka 核心机制与可靠性设计压测、监控与回滚方案？

## 参考规范

- Apache Kafka Design：https://kafka.apache.org/41/design/design/
- KafkaProducer idempotence and transactions：https://kafka.apache.org/41/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html
