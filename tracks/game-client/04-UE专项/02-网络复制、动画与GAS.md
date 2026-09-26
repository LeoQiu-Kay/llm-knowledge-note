---
slug: game-ue-replication-animation-gas
title: UE 网络复制、动画、AI 与 GAS
---
# UE 网络复制、动画、AI 与 GAS

> **优先级**：复制 P0；动画/移动/AI 为 Gameplay P0/P1；GAS 在战斗岗位通常 P1，明确要求时升为 P0。

## 1. 服务器权威与复制

UE 多人游戏采用 client-server 模型：服务器保存权威世界，客户端发送输入或 Server RPC，服务器验证后通过属性复制、RepNotify 和 RPC 把结果发回。复制不是“勾上 Replicates 就全自动”：属性、组件、子对象、相关性、优先级、Dormancy 和频率都要设计。

高频移动使用预测与校正，低频结果可用可靠 RPC；Multicast 要谨慎，只有确实需要让所有相关连接同时表现的事件才使用。可靠 RPC 绑定每帧输入可能撑爆队列，常规移动和瞄准应使用压缩状态或不可靠消息。

## 2. 动画与角色移动

CharacterMovementComponent 已提供网络移动、预测和纠正框架；自定义移动模式要明确服务器/客户端各自执行的步骤、根运动来源和碰撞验证。动画蓝图更偏表现层，技能、受击和移动状态的权威数据应来自 Gameplay 层，再驱动动画参数。

## 3. AI 与物理

AIController、Behavior Tree、Blackboard、EQS/NavMesh 形成感知—决策—执行链路。大规模 AI 要做感知分层、tick 限频和导航查询缓存。物理网络同步要区分服务器模拟、客户端预测和视觉插值，快速物体需要连续碰撞检测与权威命中判定。

## 4. GAS 面试抓手

Gameplay Ability System 用 Ability、Attribute、Gameplay Effect、Gameplay Tag 组织技能与数值：Ability 描述可激活行为，AttributeSet 保存属性，Effect 负责修改/周期/条件，Tag 表达状态和阻断规则。网络上要区分预测激活、服务器确认、预测窗口和回滚；表现层粒子/音效应可重建，不要把不可逆副作用放在客户端预测路径。

### 高频追问

#### Q1. RepNotify 与 Multicast RPC 怎么选？

持续状态或晚加入者也需要看到的内容用复制属性/RepNotify；一次性的、由服务器确认的表现事件才考虑 Multicast。RepNotify 还能在重连、相关性变化后恢复状态，Multicast 只在发送时覆盖在线连接。

#### Q2. GAS 为什么要用 Gameplay Tag？

Tag 把“眩晕、沉默、无敌、技能冷却”等状态从硬编码布尔值提升为可组合的层级标签，Ability 和 Effect 可以统一做条件、阻断和查询；同时便于蓝图、配置和网络序列化。
