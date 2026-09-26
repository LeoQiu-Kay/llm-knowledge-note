---
slug: game-ue-animation-movement-ai
title: UE 动画、角色移动、AI 与物理
---
# UE 动画、角色移动、AI 与物理

> **优先级**：Gameplay P0/P1。

## 1. 角色移动

CharacterMovementComponent 处理预测、校正、地面检测和自定义移动模式。扩展时要明确客户端输入、服务器验证、模拟代理表现和根运动来源，不能只在客户端修改位置。

## 2. 动画

Animation Blueprint 读取 Gameplay 状态并驱动姿态；Montage、Notify、Layer 和 IK 负责表现。技能命中、伤害和状态改变由权威 Gameplay 系统产生，动画 Notify 只发起可验证请求或表现事件。

## 3. AI 与物理

AIController、Behavior Tree/State Tree、Blackboard、EQS 和 NavMesh 形成决策链。大规模 AI 做感知缓存、查询限频和 LOD。网络物理要区分服务器模拟、客户端预测、纠正和视觉插值。

### 高频追问

#### Q1. 自定义移动模式要注意什么？
定义输入、速度、碰撞、预测数据、服务器校验、回滚和模拟代理表现；否则单机看似正常，弱网下会漂移或被服务器频繁纠正。

#### Q2. 动画 Notify 能直接造成伤害吗？
不能把客户端 Notify 当权威命中。它可以请求或触发表现，真正伤害应由服务器按技能状态、时间窗和碰撞重新计算。
