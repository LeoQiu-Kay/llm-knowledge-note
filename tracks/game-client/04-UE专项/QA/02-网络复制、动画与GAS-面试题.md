---
slug: game-ue-replication-animation-gas
title: UE 网络复制、动画、AI 与 GAS · 面试题
---
# UE 网络复制、动画、AI 与 GAS · 面试题

## Q1: 为什么勾选 Replicates 后属性仍不同步？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

Actor 复制只是基础开关，还要把属性加入复制列表、确认 Actor 对连接相关、组件/子对象可复制，并检查服务器是否真正修改了权威值。高频数据还受 relevancy、Dormancy 和更新频率影响。

## Q2: RepNotify 和可靠 RPC 如何选择？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

持续状态和晚加入者需要看到的内容优先复制属性/RepNotify；一次性、需要立即触发表现的事件才用 RPC。可靠 RPC 不适合每帧输入，Multicast 也要控制频率和连接范围。

## Q3: GAS 中 Ability、Effect、Attribute、Tag 分别是什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

Ability 描述可激活行为，Effect 描述属性修改和持续条件，AttributeSet 保存数值，Tag 表达状态/阻断/权限。预测激活只能先做可回滚表现，伤害和奖励仍需服务器确认。
