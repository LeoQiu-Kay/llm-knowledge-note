---
slug: game-unity-assets-serialization
title: Unity 资源管线、场景与序列化 · 面试题
---
# Unity 资源管线、场景与序列化 · 面试题

## Q1: Addressables 句柄为什么必须成对管理？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

句柄代表资源依赖引用；只加载不释放会让 bundle 和依赖一直存活，只释放过早又会造成实例失效。应让 owner 管理句柄并覆盖异常路径。

## Q2: 运行时状态为什么不能写回 ScriptableObject？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

它是共享配置资产，写回会污染编辑器数据、影响其他实例，并可能在只读平台失败。存档应使用独立版本化数据。
