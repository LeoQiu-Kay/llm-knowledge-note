---
slug: game-csharp-collections-delegates
title: C# 集合、委托、事件与反射
---
# C# 集合、委托、事件与反射

> **优先级**：Unity P0/P1。

## 1. 集合与分配

泛型 `List<T>`、`Dictionary<TKey,TValue>` 避免大多数装箱；容量预估减少扩容。接口和非泛型枚举可能产生装箱或虚调用，LINQ 的 iterator、闭包和临时集合不适合每帧热点。

## 2. 委托与事件

委托是可组合的调用对象，事件限制外部只能订阅/退订。发布者长寿而订阅者短寿会造成泄漏；事件回调内不要修改订阅列表，也要定义异常传播和线程归属。

## 3. 反射与裁剪

反射适合编辑器、序列化和工具生成，但运行时成本高，AOT/IL2CPP 裁剪可能移除只被反射使用的类型。生产路径可用缓存、源生成、显式注册和 `link.xml`，并在裁剪构建上回归。

### 高频追问

#### Q1. foreach 一定会分配么？
不一定。泛型集合的结构体 Enumerator 可零分配；转成接口、非泛型 IEnumerable 或使用捕获闭包后才可能装箱/分配。应看实际类型和 Profiler。

#### Q2. 事件如何自动解绑？
让订阅返回 IDisposable/Subscription token，在组件 OnDisable/Dispose 时统一释放；或由生命周期容器托管订阅，避免依赖人工记忆。
