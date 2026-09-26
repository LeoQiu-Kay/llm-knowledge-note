---
slug: game-unity-animation-physics-ai
title: Unity 动画、物理、输入与 AI
---
# Unity 动画、物理、输入与 AI

> **优先级**：Gameplay P0。

## 1. 动画

Animator 负责状态机和混合，战斗逻辑应独立；Root Motion 要明确由动画还是移动系统写 Transform。动画事件属于表现回调，不能直接决定服务器伤害结果。

## 2. 物理

Rigidbody、CharacterController 和自定义运动学只能有一个权威移动者；碰撞层、触发器、连续碰撞检测和 Fixed Timestep 按速度与重要性配置。渲染帧与物理帧之间用插值表现平滑。

## 3. 输入与 AI

输入先映射成动作，再交给 Gameplay；按键、手柄和触屏共享动作语义。AI 拆感知、决策、执行，行为树/状态机负责决策，导航和群体避障按距离与 tick 频率分级。

### 高频追问

#### Q1. Root Motion 和代码移动如何共存？
必须明确一帧内唯一写入者，或把动画位移作为输入交给运动组件统一碰撞/网络校验；不能动画和脚本同时改 Transform。

#### Q2. AI 为什么要做分级 tick？
远处、不可见或低威胁 AI 不需要每帧感知和寻路；按距离、战斗状态和屏幕可见性降频，可把 CPU 预算留给关键实体。
