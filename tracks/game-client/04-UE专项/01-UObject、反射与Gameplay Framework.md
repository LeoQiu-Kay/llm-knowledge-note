---
slug: game-ue-object-gameplay
title: UObject、反射与 Gameplay Framework
---
# UObject、反射与 Gameplay Framework

> **优先级**：P0。UE 面试的主线是 UObject 生命周期、反射/蓝图边界，以及框架类各自拥有的状态。

![Unreal Engine Gameplay Framework](https://d1iv7db44yhgxn.cloudfront.net/documentation/images/368221fe-2c19-4087-b037-23aead954afe/gameframework.png)

*图示来源： [Epic Games — Gameplay Framework Quick Reference](https://dev.epicgames.com/documentation/unreal-engine/gameplay-framework-quick-reference)。*

## 1. UObject 与反射

`UObject` 提供反射、序列化、编辑器属性和 GC 集成；`AActor` 是能放入世界并参与网络复制的 UObject 子类，`UActorComponent` 是挂在 Actor 上的可复用能力。`USTRUCT` 适合值语义数据，`UCLASS`/`UPROPERTY`/`UFUNCTION` 宏把类型暴露给反射系统。

反射字段要考虑 `EditAnywhere`、`BlueprintReadOnly`、复制、存档和版本迁移。不要用裸指针假设 UObject 永远存在；引用关系要通过 `UPROPERTY`、`TObjectPtr` 或明确的弱引用表达。

## 2. Gameplay Framework 的分工

Epic 文档中的核心关系可以这样记：

| 类 | 主要职责 | 联机存在性 |
|---|---|---|
| `GameInstance` | 跨关卡的会话服务、存档/在线子系统 | 各端各自存在，不复制 |
| `GameMode` | 规则、胜负、生成流程 | 仅服务器 |
| `GameState` | 全局比赛状态 | 服务器和客户端，可复制 |
| `PlayerController` | 玩家意图、输入、拥有连接 | 服务器 + 所属客户端 |
| `PlayerState` | 玩家分数、队伍、可公开状态 | 所有端，可复制 |
| `Pawn/Character` | 世界中的物理化身与移动 | 按 Actor 复制 |

把“规则”放 GameMode，把“客户端要看到的比赛状态”放 GameState，把“玩家公开数据”放 PlayerState；不要把客户端必须读取的数据放在只存在服务器的类里。

## 3. 创建与销毁

`NewObject` 用于 UObject，`SpawnActor` 用于世界中的 Actor；构造函数适合默认子对象和不依赖世界的初始化，`BeginPlay` 适合世界已经准备好的逻辑。Actor 销毁、关卡卸载、PIE 多世界和编辑器对象会让生命周期更复杂，异步回调要检查对象有效性和世界上下文。

### 高频追问

#### Q1. GameMode 和 GameState 的区别？

GameMode 定义规则并只在服务器运行；GameState 保存比赛过程中客户端也需要知道的状态，并在服务器和客户端存在、可复制。把分数放 GameMode 会导致客户端拿不到，把规则判断放 GameState 又会削弱服务器权威。

#### Q2. 为什么不能把所有成员都标成 `UPROPERTY`？

反射字段会影响 GC、序列化、复制和内存布局，暴露过多会增加耦合和运行成本。只有需要被 GC 跟踪、编辑器/蓝图访问、复制或保存的字段才选择合适的 specifier。
