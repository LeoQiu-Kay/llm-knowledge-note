---
slug: game-ue-gameplay-framework
title: UE Gameplay Framework 深入 · 面试题
---
# UE Gameplay Framework 深入 · 面试题

## Q1: PlayerController 与 PlayerState 怎么区分？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

Controller 表示玩家意图和连接，主要由所属客户端拥有；PlayerState 是可公开复制的玩家数据，所有客户端通常都能看到。

## Q2: Subsystem 比全局单例好在哪里？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

Subsystem 有引擎/游戏实例/世界/本地玩家等明确生命周期，依赖和销毁更可控，也更容易测试 PIE 多实例。
