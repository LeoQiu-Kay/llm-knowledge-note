---
slug: game-ue-object-gameplay
title: UObject、反射与 Gameplay Framework · 面试题
---
# UObject、反射与 Gameplay Framework · 面试题

## Q1: GameMode、GameState、PlayerState 如何分工？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

GameMode 只在服务器定义规则和生成流程；GameState 在服务器与客户端存在，保存比赛全局状态；PlayerState 表示每个参与者的公开数据并可复制。规则不应依赖客户端本地 GameMode。

## Q2: NewObject 与 SpawnActor 有什么区别？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

NewObject 创建 UObject，不自动进入世界；SpawnActor 创建可放入世界、拥有 Transform、组件和网络生命周期的 Actor。需要世界、碰撞或复制时应使用 SpawnActor，并处理 owner、instigator 和销毁。

## Q3: 什么时候使用 TObjectPtr 或软引用？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

需要 GC 跟踪的 UObject 成员用 TObjectPtr/UPROPERTY；可选或大资源用软引用，按需异步加载。裸指针只适合作为短期、非拥有观察者，并在使用前验证有效性。
