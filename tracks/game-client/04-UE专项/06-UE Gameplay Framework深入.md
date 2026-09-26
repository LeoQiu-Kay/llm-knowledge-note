---
slug: game-ue-gameplay-framework
title: UE Gameplay Framework 深入
---
# UE Gameplay Framework 深入

> **优先级**：P0。

## 1. 玩家链路

输入进入 PlayerController，Controller possess Pawn/Character；Pawn 组合碰撞、网格和 Movement Component；PlayerState 保存公开玩家状态；GameState 保存比赛状态；GameMode 只在服务器组织规则和生成。

## 2. 生命周期与网络

GameInstance 跨关卡存在，World/Level/Actor 随地图变化。PlayerController 在服务器和所属客户端有特殊存在关系，PlayerState 则通常在所有端可见。回答时要指出类存在在哪些机器、谁拥有权威写入。

## 3. Subsystem

Subsystem 按 Engine、GameInstance、World、LocalPlayer 等生命周期承载服务，比到处写单例更容易测试和释放。服务启动顺序、依赖和 PIE 多实例必须明确。

### 高频追问

#### Q1. PlayerController 与 PlayerState 的区别？
Controller 代表玩家意图和连接，客户端主要拥有自己的 Controller；PlayerState 是可公开复制的玩家数据，所有客户端通常都能看到。

#### Q2. 为什么 GameMode 不能放客户端 UI 所需数据？
GameMode 只在服务器存在，客户端拿不到它。需要展示的数据应放 GameState/PlayerState 并通过复制同步。
