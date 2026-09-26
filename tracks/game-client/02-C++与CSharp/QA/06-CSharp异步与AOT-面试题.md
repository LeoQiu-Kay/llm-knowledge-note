---
slug: game-csharp-async-aot
title: C# 异步、线程与 AOT · 面试题
---
# C# 异步、线程与 AOT · 面试题

## Q1: 场景卸载时如何处理未完成 Task？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

用 CancellationToken 取消任务，回调前检查场景 generation/对象有效性；不要让旧任务继续更新新场景 UI，也不要同步等待阻塞主线程。

## Q2: Coroutine、Task、Job 的边界是什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

Coroutine 做主线程时序，Task 做 IO 编排，Job/Burst 做纯数据并行。选择时必须说明线程归属、取消和结果合并方式。
