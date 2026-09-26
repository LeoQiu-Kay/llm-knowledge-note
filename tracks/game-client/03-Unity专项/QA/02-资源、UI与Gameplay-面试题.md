---
slug: game-unity-assets-ui-gameplay
title: Unity 资源、UI、动画物理与 Gameplay · 面试题
---
# Unity 资源、UI、动画物理与 Gameplay · 面试题

## Q1: Resources 和 Addressables 的核心差别？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

Resources 通过固定目录打包和查找，依赖、包体与卸载边界不清晰；Addressables 用 catalog、分组、依赖和句柄支持异步按需加载，更适合大项目，但需要管理版本、失败和释放。

## Q2: UI 为什么要和战斗逻辑解耦？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

UI 会随场景、分辨率和输入模式变化，战斗状态则要可测试、可同步、可回放。通过 ViewModel、命令或领域事件连接，可以避免按钮回调绕过权限和服务器校验。

## Q3: 角色移动应放 Animator、Rigidbody 还是 Character Controller？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

先确定移动权责：Rigidbody 交给物理，Character Controller/引擎移动组件交给运动学；Animator 负责表现和可选 Root Motion。网络游戏还要补充预测、校正与服务器碰撞验证。
