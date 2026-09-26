---
slug: game-ue-ui-assets-levels
title: UE UI、资源与关卡管理
---
# UE UI、资源与关卡管理

> **优先级**：P0/P1。

## 1. UMG/Slate

UMG 面向内容和蓝图，Slate 提供底层 C++ Widget。高频列表做 Entry 复用、Invalidation、可见性裁剪和数据驱动刷新；Widget 不应在 Tick 里轮询整个世界。

## 2. Asset Manager

硬引用扩大加载链，软引用配合 Primary Asset、Label、Chunk 和异步加载控制首包与补丁。加载句柄由 owner 持有，失败、取消和版本切换都要回收。

## 3. 关卡与流送

World Partition、Data Layer、Level Streaming 按空间、任务和玩家状态加载内容；加载范围要和网络 relevancy、内存和服务器兴趣管理协调，不能只按磁盘目录拆分。

### 高频追问

#### Q1. UMG 列表卡顿先看什么？
看 Widget 数量、重建、布局、Tick、纹理/字体和 GC；优先虚拟化、Entry 复用和批量刷新，再看材质和提交。

#### Q2. 软引用的缺点是什么？
需要异步加载、错误和版本处理，调用方不能假设资源立即存在；但它能解耦依赖、降低首屏和支持按需内容。
