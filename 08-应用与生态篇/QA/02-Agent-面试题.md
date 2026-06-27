# Agent · 面试题

> 对应原理文档：[02-Agent.md](../02-Agent.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: 什么是 Agent？它和普通 LLM 对话有什么本质区别？
> 难度 ⭐ ｜ 高频 🔥🔥🔥

**Agent**（智能体）：让 LLM 通过调用**工具**、感知**环境**、做出**决策**，完成多步骤任务的系统。

**四要素**：
1. **LLM**：大脑，做规划和决策
2. **工具**：API、函数、其他模型
3. **记忆**：短期（上下文）+ 长期（向量存储）
4. **环境**：可交互的外部系统（浏览器、文件、代码执行）

**与普通对话区别**：

| | 普通 LLM 对话 | Agent |
|---|---|---|
| 输入 | 一句话问题 | 一个目标 |
| 过程 | 单轮生成 | 多步行动循环 |
| 能力 | 仅生成文本 | 调用工具改变世界 |
| 反馈 | 无 | 有（环境观察） |

**追问：Agent 必须多轮吗？** 是。本质特征是"感知 → 行动 → 观察"的闭环，单轮 Function Calling 严格说算工具调用，不算 Agent。

---

## Q2: 什么是 ReAct 模式？为什么早期 Agent 都用它？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**ReAct**（Reasoning + Acting, Yao et al. 2022）：交替进行**推理**（Thought）和**行动**（Action）。

**循环结构**：

```
Thought: 我需要查询北京天气
Action: search_weather("北京")
Observation: 北京今天 22°C，多云
Thought: 用户想去公园，可以建议
Final Answer: 北京今天天气适合去公园，建议带件薄外套。
```

**为什么早期主流**：
1. **显式思考链**：CoT（Chain of Thought，思维链）+ 行动结合，推理过程可见
2. **可解释、可调试**：每一步都明示，错在哪一眼看出
3. **纯 prompt 实现**：不需要模型原生支持工具调用，任何 LLM 都能跑

**缺点**：
- token 开销大（每步都写 Thought）
- 链式串行，无法并行
- 错一步全错（错误累积）

---

## Q3: Function Calling 和 ReAct 是什么关系？OpenAI Function Calling 的流程？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**关系**：Function Calling 是 ReAct 的"工程化升级版"——把 ReAct 的 Action 步骤从 prompt 里的文本解析，升级为模型**原生输出结构化调用**。

**OpenAI Function Calling 流程**：

```
1. 给 LLM 工具描述（JSON Schema）
2. LLM 决定调用哪个工具，输出工具名 + 参数
   { "name": "get_weather", "arguments": {"city": "北京"} }
3. 应用层执行工具
4. 工具结果回传给 LLM
5. LLM 继续调用 / 给最终答案
```

**对比**：

| | ReAct（prompt） | Function Calling（原生） |
|---|---|---|
| 工具定义 | 文本描述 | JSON Schema |
| 输出 | 文本（要正则解析） | 结构化 JSON |
| 可靠性 | 中（解析失败） | 高（强约束） |
| 并行 | 难 | 可（parallel tool calls） |

**主流支持**：OpenAI Function Calling、Anthropic Tool Use、Qwen/DeepSeek 等开源；MCP 是跨厂商的标准化协议。

---

## Q4: 什么是 MCP？为什么说它是 LLM 的"USB-C"？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**MCP**（Model Context Protocol，模型上下文协议）：Anthropic 2024 年提出的**标准化 LLM-工具协议**。

**类比**：
- 类似 **LSP**（Language Server Protocol）之于 IDE——VSCode/Vim/Emacs 都能用同一个 Python LSP server
- 工具服务器实现标准接口，任何 LLM 客户端都能调用任何 MCP 服务器
- "USB-C"：以前每个 LLM 框架自己定义工具格式（OpenAI / LangChain / Anthropic 各不相同），现在用统一接口

**好处**：
1. **工具复用**：一次实现，多 LLM 客户端可用
2. **解耦**：工具开发者不用关心调用方
3. **生态**：第三方 MCP server 越来越多（GitHub、Slack、Database、文件系统）

**当前支持**：Claude Desktop、Claude Code 原生支持；越来越多框架（如 mcp-agent）适配。

**追问：MCP 之前各家不也都能调工具吗，为什么还要标准化？** 类比 USB 之前各家都有充电口，但互不通用——重复造轮子、生态分散。MCP 让"工具市场"成为可能，类似 npm 之于 Node。

---

## Q5: Planning 模式有哪些？Plan-and-Execute vs ReAct 怎么选？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**主流 Planning 模式**：

| 模式 | 思路 |
|---|---|
| **ReAct** | 边走边想，单步决策 |
| **Plan-and-Execute** | 先列完整计划，再逐步执行 |
| **ReWOO** | 先规划全部工具调用，再**并行**执行 |
| **LLM Compiler** | 编译成 DAG 并行执行 |
| **Tree of Thoughts (ToT)** | 树搜索式规划，多分支探索 |

**Plan-and-Execute vs ReAct**：

| | ReAct | Plan-and-Execute |
|---|---|---|
| 规划 | 隐式、单步 | 显式、全局 |
| 适合 | 简单、强反馈任务 | 复杂、可拆分任务 |
| 容错 | 错一步全错 | 子步可重试 |
| token 成本 | 中 | 高（要先列 plan） |

**实践**：
- 简单 QA / 工具查询 → ReAct
- 长任务（写代码、做研究）→ Plan-and-Execute
- 可并行任务（多工具查询）→ ReWOO / LLM Compiler

---

## Q6: 多 Agent 系统的典型角色和通信方式？什么时候比单 Agent 强？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**典型角色**：
- **Planner**：拆解任务
- **Researcher**：搜集信息
- **Coder**：写代码
- **Reviewer**：检查
- **Coordinator**：协调

**通信方式**：
- **顺序（pipeline）**：A → B → C 流水线
- **黑板（blackboard）**：共享状态，多 Agent 读写
- **消息（message passing）**：事件驱动，类似 actor 模型

**主流框架**：AutoGen（MS）、MetaGPT、CrewAI。

**多 Agent 强在哪**：
- 角色专精（system prompt 针对性强）
- 互相 review 减少幻觉
- 可并行

**多 Agent 弱在哪**：
- 协调开销大（token 翻倍）
- 错误累积（一个 Agent 错全链路错）
- 调试困难

**实践结论**：简单任务单 Agent + 工具就够；复杂任务（写整个项目、做调研报告）多 Agent 才有优势。不要为了多而多。

---

## Q7: Agent 的"工具使用"有哪些常见坑？怎么提高可靠性？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**常见问题**：

| 问题 | 表现 | 对策 |
|---|---|---|
| 参数错误 | 类型/格式不对 | JSON Schema 严格约束、grammar-constrained decoding |
| **幻觉工具** | 调用不存在的工具 | prompt 明确列出可用工具、白名单 |
| **死循环** | 反复调同一工具 | 限制最大步数、检测重复 |
| 过度保守/激进 | 该调不调 / 不该调乱调 | 改 prompt 中的工具说明 |
| 结果解析失败 | 工具返回大段文本难提取 | 工具返回结构化结果 |

**提高可靠性的通用手段**：
1. **约束输出**：Function Calling / structured output
2. **工具白名单**：明确列可用工具
3. **自我反思**：每步后让模型自检
4. **关键步骤人工 review**：尤其涉及写入/删除/付款
5. **限制步数 + 超时**：防止跑飞
6. **沙箱执行**：代码、shell 命令在隔离环境跑

**追问：Agent 怎么避免"调用 get_wether 这种拼错的工具名"？** ① constrained decoding 强制选可用工具；② JSON Schema 校验失败重试；③ 在 prompt 中明确"以下是仅有的工具列表"。

---

## Q8: Agent 的短期/长期记忆怎么实现？MemGPT 解决什么问题？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**短期记忆**：
- 即对话上下文（system prompt + 历史轮）
- 受 context 长度限制
- 超长后必须**总结**或**裁剪**

**长期记忆**：
- **向量存储**：摘要/事实存 embedding，相似检索（本质是 RAG）
- **结构化 DB**：用户画像、偏好键值对
- **知识图谱**：实体-关系-实体

**Memory 分类**（认知科学借词）：
- **Working Memory**：当前任务工作内存
- **Episodic Memory**：过去的对话/事件
- **Semantic Memory**：抽象知识、事实

**MemGPT**（2023）解决什么：
- LLM context 有限（比如 8K），但想要"无限记忆"
- 类比操作系统**虚拟内存**：把 context 当 RAM，外存当硬盘
- LLM 自己决定**换入换出**（用工具调用 `read_memory` / `write_memory`）
- 实现"看起来无限长的对话"

**实践**：LangChain 的 `ConversationBufferMemory` / `VectorStoreMemory`；Letta（前 MemGPT）专门做分层记忆。

---

## Q9: Computer Use / GUI Agent 是什么？挑战在哪？
> 难度 ⭐⭐⭐ ｜ 高频 🔥

**Computer Use**（Anthropic 2024.10）：让 Claude 直接操作计算机。

**流程**：
```
截屏 → VLM 识别 UI 元素 → 输出点击坐标 / 输入文字 / 滚动
        → 执行 → 新截屏 → 循环
```

**类似工作**：OpenAI Operator、Google Project Mariner、各种 Web Agent（WebVoyager、Browse-RL）。

**比传统 RPA 强在哪**：
- 不依赖 selector（页面改了不挂）
- 通用——任何 GUI 程序都行（不限浏览器）
- 像人一样"看"屏幕，能处理动态内容

**核心挑战**：
1. **视觉识别精度**：小图标、密集 UI、字体识别
2. **坐标准确性**：1 像素偏差点错按钮
3. **容错**：页面加载延迟、弹窗、网络抖动
4. **安全**：易被"间接 prompt injection"劫持（网页里嵌恶意指令）
5. **成本**：每步要传图，token 暴涨

**实践**：现在主要 demo，量产可靠性还差；OS-Atlas、ShowUI 等专门 GUI 模型在快速进步。

---

## Q10: Agent 怎么评估？主流 benchmark 有哪些？
> 难度 ⭐⭐ ｜ 高频 🔥

**主流 Benchmark**：

| Benchmark | 测什么 |
|---|---|
| **AgentBench** | 综合 Agent 能力（OS、DB、代码、网页等 8 大场景） |
| **GAIA** | 真实世界助手任务（多步推理 + 工具） |
| **WebArena / WebShop** | 网页交互 |
| **SWE-Bench** | 解决真实 GitHub issue（代码 Agent 主流） |
| **BFCL** | Berkeley Function Calling Leaderboard，专测工具调用 |

**核心指标**：
1. **任务完成率**：成功完成的比例（最重要）
2. **步数**：效率（更少步数完成更优）
3. **工具调用准确率**：调对工具的比例
4. **成本**：token 消耗、API 调用费

**追问：SWE-Bench 为什么是代码 Agent 的"高考"？** ① 真实 GitHub issue + 真实 patch + 真实测试，无法 cheat；② 涉及阅读大代码库、定位 bug、改代码、过测试，覆盖完整工程能力；③ Claude/GPT/o-series 都在卷这个榜。

---

## 🎯 自测清单

- [ ] 能说清 Agent 的四要素 + 和普通对话的区别
- [ ] 能讲 ReAct 循环 Thought-Action-Observation
- [ ] 能讲 Function Calling 流程 + MCP 解决什么问题
- [ ] 能对比 Plan-and-Execute / ReAct / ReWOO 的适用场景
- [ ] 能列出工具使用的常见坑 + 5 种可靠性提升手段
