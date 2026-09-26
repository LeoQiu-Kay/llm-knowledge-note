---
slug: game-ue-lifecycle-gc
title: UE 生命周期、GC 与智能指针
---
# UE 生命周期、GC 与智能指针

> **优先级**：P0。

## 1. 创建与销毁

构造函数不应依赖 World、Player 或其他 Actor；组件注册、属性初始化、BeginPlay 和 EndPlay 各有时机。Actor 销毁通常延迟到当前帧结束，异步回调要判断 `IsValid`、World 和请求 generation。

## 2. GC 引用链

`UPROPERTY`/`TObjectPtr` 让 GC 看到强引用；弱对象指针不会阻止回收。静态缓存、委托、Subsystem 和异步任务是常见泄漏/悬空来源。释放不是简单 delete，而是解除 owner、取消任务、解绑事件和等待引用链断开。

## 3. 非 UObject 资源

普通 C++ 对象使用 RAII/智能指针，不能用 UObject 的 GC 规则推断它们；UObject 也不能随意交给 `shared_ptr` 管理。跨边界引用要写清拥有者、线程和销毁顺序。

### 高频追问

#### Q1. 为什么 UObject 不建议手动 delete？
引擎需要维护对象注册、反射和 GC 引用图；手动 delete 会破坏内部状态。应使用引擎创建/销毁 API和引用管理。

#### Q2. 异步加载完成时对象可能发生什么？
对象可能被销毁、换世界、换版本或请求被新请求覆盖。回调必须验证句柄、World、generation 和 owner，再决定是否应用结果。
