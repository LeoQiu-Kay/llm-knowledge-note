---
slug: game-unity-render-pipeline-shader
title: Unity 渲染管线、Shader 与材质 · 面试题
---
# Unity 渲染管线、Shader 与材质 · 面试题

## Q1: MaterialPropertyBlock 的用途是什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

在不复制共享材质的情况下为单个 Renderer 设置属性，适合实例差异；还需验证与 SRP Batcher/Instancing 的兼容性。

## Q2: Shader 变体过多会造成什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

编译时间、包体、运行时 warmup 和内存都增加。应剔除无用关键字、按平台保留并检查构建报告。
