---
slug: game-unity-render-pipeline-shader
title: Unity 渲染管线、Shader 与材质
---
# Unity 渲染管线、Shader 与材质

> **优先级**：P0/P1。

## 1. 管线选择

Built-in、URP、HDRP 在功能、平台和扩展方式上不同；选择要结合目标设备、内容规模、后处理、光照和团队工具链。不要在项目中途无基线迁移。

## 2. Shader 与材质

材质实例共享 Shader 但覆盖参数；MaterialPropertyBlock 可避免复制材质。变体组合、关键字、动态分支、精度和纹理采样共同决定编译时间与 GPU 成本，移动端要控制变体和 overdraw。

## 3. 调试

Frame Debugger 看 pass、批处理与排序，RenderDoc 看真实 GPU 命令和资源，Shader 编译日志定位平台差异。每个质量档位应有明确分辨率、阴影、LOD、后处理和纹理预算。

### 高频追问

#### Q1. MaterialPropertyBlock 解决什么问题？
它在不复制共享材质的情况下为单个 Renderer 设置属性，适合实例化对象差异；但要注意 SRP Batcher/实例化兼容性和属性频率。

#### Q2. Shader 变体为什么会拖慢构建？
关键字组合可能指数增长，导致编译时间、包体和运行时 warmup 变大。应剔除无用变体、按平台保留并监控构建报告。
