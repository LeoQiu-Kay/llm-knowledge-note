---
slug: game-ue-lifecycle-gc
title: UE 生命周期、GC 与智能指针 · 面试题
---
# UE 生命周期、GC 与智能指针 · 面试题

## Q1: 为什么 UObject 不能直接 delete？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

引擎需要维护注册表、反射和 GC 引用图；应使用 UObject/Actor 生命周期 API，并解除 owner、事件和异步任务。

## Q2: 异步回调使用 UObject 前检查什么？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

检查对象有效性、World、请求句柄、generation 和 owner 是否仍存在，避免旧场景结果写入新场景。
