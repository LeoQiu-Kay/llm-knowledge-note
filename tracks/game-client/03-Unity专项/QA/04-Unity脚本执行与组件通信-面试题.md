---
slug: game-unity-script-communication
title: Unity 脚本执行顺序与组件通信 · 面试题
---
# Unity 脚本执行顺序与组件通信 · 面试题

## Q1: 为什么要用批量 Update？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

减少回调调度和虚调用，便于按距离/状态降频、统计和 Job 化；系统还要处理实体加入、移除和暂停。

## Q2: 事件如何避免泄漏？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

让订阅返回 token/Dispose，在 OnDisable/销毁时统一解绑，并明确事件线程与异常策略。
