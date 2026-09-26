---
slug: game-unity-ui-system
title: Unity UI 系统与高性能界面 · 面试题
---
# Unity UI 系统与高性能界面 · 面试题

## Q1: Canvas 拆分为什么可能提升性能？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

把高频变化与静态元素拆开，减少 Canvas rebuild 范围；但 Canvas 太多会增加提交，必须通过 Profiler 找到平衡。

## Q2: UI 是否应该直接扣血？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

不应该。UI 发出命令或意图，Gameplay/服务器验证并修改状态，UI 只订阅结果，避免绕过权限、预测和回放逻辑。
