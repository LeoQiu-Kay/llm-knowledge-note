---
slug: game-ue-gas-skills
title: UE GAS 技能系统 · 面试题
---
# UE GAS 技能系统 · 面试题

## Q1: Ability、Effect、Attribute、Tag 的关系？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

Ability 描述行为，Effect 修改属性，AttributeSet 保存数值，Tag 表达状态和阻断；ASC 负责承载、预测和网络交互。

## Q2: 预测失败时应该回滚什么？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

回滚可逆的动画、粒子、输入锁和 UI；伤害、扣费、掉落等不可逆结果只由服务器确认产生。
