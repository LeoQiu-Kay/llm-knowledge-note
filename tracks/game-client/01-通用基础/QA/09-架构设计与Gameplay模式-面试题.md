---
slug: game-architecture-gameplay-patterns
title: 客户端架构、设计模式与 Gameplay · 面试题
---
# 客户端架构、设计模式与 Gameplay · 面试题

## Q1: 状态机比多个 bool 好在哪里？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

状态机显式定义互斥状态、迁移、进入和退出动作，避免 `isDead/isStunned/isAttacking` 组合出非法状态，并便于回放和测试。

## Q2: 全局事件总线的主要风险是什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

依赖不可见、顺序难追踪、订阅泄漏和线程边界不清。应限制作用域、定义事件契约，并由生命周期 owner 自动解绑。
