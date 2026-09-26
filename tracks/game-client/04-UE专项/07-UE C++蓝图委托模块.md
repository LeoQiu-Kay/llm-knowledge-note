---
slug: game-ue-cpp-blueprint-modules
title: UE C++、蓝图、委托与模块
---
# UE C++、蓝图、委托与模块

> **优先级**：P0/P1。

## 1. C++ 与蓝图边界

C++ 负责稳定、性能敏感和可测试的核心；蓝图负责组合、配置和内容迭代。`BlueprintCallable/ImplementableEvent/NativeEvent` 要定义权限、线程和生命周期，避免把关键规则藏在不可审计的蓝图 Tick。

## 2. 委托

单播、多播、动态委托在类型安全、反射、序列化和性能上不同。绑定 UObject 时要在销毁/EndPlay 解绑，异步回调使用弱引用或句柄，避免广播到已经离开世界的对象。

## 3. 模块与插件

Build.cs 的 Public/PrivateDependencyModuleNames 决定编译与打包边界；插件要区分 Editor/Runtime、加载阶段和平台条件。跨模块头文件保持最小依赖，避免热重载后 ABI/反射状态不一致。

### 高频追问

#### Q1. 动态委托与普通委托怎么选？
需要蓝图、反射或序列化时用动态委托；纯 C++ 热点优先普通委托，性能和类型控制更好。

#### Q2. 为什么模块依赖错误常在打包才暴露？
编辑器可能通过间接模块或已加载插件提供符号，Cook/Shipping 只包含声明的依赖。应在干净构建和目标平台 CI 中验证。
