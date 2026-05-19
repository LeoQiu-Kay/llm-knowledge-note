# Agent（智能体）

> LLM 调用工具完成复杂任务的核心范式。

---

## Q1: 什么是 Agent？

**答**：
**定义**：让 LLM 通过调用**工具**、感知**环境**、做出**决策**，完成多步骤任务的系统。

**核心要素**：
1. **LLM**：大脑，做规划和决策
2. **工具**：API、函数、其他模型
3. **记忆**：短期（上下文）+ 长期（向量存储）
4. **环境**：可交互的外部系统（浏览器、文件系统、代码执行）

**与普通 LLM 对话的区别**：
- 单轮对话：用户问、LLM 答
- Agent：用户给目标 → LLM 多步骤行动 → 完成任务

---

## Q2: ReAct 模式？

**答**：
**ReAct**（Reasoning + Acting, Yao et al. 2022）：交替进行推理和行动。

**循环**：
```
Thought: 我需要查询天气
Action: search_weather("北京")
Observation: 北京今天 22°C，多云
Thought: 用户想去公园，我可以建议
Final Answer: 北京今天天气适合去公园，建议带件薄外套。
```

**特点**：
- 显式的"思考链"（CoT）+ 行动
- 可解释、可调试
- 早期 Agent 主流模式

---

## Q3: Function Calling？

**答**：
**OpenAI Function Calling**（2023.06）：LLM 输出结构化函数调用而非文本。

**流程**：
1. 给 LLM 工具描述（JSON Schema）
2. LLM 决定调用哪个工具，输出工具名 + 参数
3. 应用层执行工具
4. 结果回传给 LLM
5. LLM 决定继续调用 / 给最终答案

**示例**：
```json
{
  "name": "get_weather",
  "arguments": {"city": "北京"}
}
```

**主流支持**：
- OpenAI Function Calling
- Anthropic Tool Use
- Qwen / DeepSeek 等开源模型
- **MCP**（Model Context Protocol）：Anthropic 提出的标准化协议

---

## Q4: 主流 Agent 框架？

**答**：

| 框架 | 特点 |
|------|------|
| **LangChain** | 工具链最全，社区大，但抽象繁琐 |
| **LangGraph** | LangChain 的状态图版本，处理复杂流 |
| **LlamaIndex** | 偏 RAG 起家，Agent 也支持 |
| **AutoGen**（MS） | 多 Agent 对话框架 |
| **CrewAI** | 角色化多 Agent |
| **SmolAgents**（HF） | 轻量、代码生成式 |
| **OpenAI Assistants API** | 一站式托管 |
| **Cline / Aider** | 编码 Agent |
| **Claude Code** | Anthropic 的代码 Agent |

---

## Q5: 多 Agent 系统？

**答**：
**思路**：多个 LLM Agent 分工协作。

**典型角色**：
- **Planner**：拆解任务
- **Researcher**：搜集信息
- **Coder**：写代码
- **Reviewer**：检查
- **Coordinator**：协调

**通信方式**：
- 顺序（pipeline）
- 黑板（共享状态）
- 消息（事件驱动）

**框架**：
- **AutoGen**：对话式协作
- **MetaGPT**：模拟软件开发团队
- **CrewAI**：明确角色和任务

**问题**：
- 协调开销大
- 错误累积
- 调试困难

---

## Q6: Planning 与任务分解？

**答**：

**Plan-and-Execute**：
1. Planner LLM 输出完整计划（一系列步骤）
2. Executor 逐步执行
3. 中间结果反馈给 Planner（必要时重规划）

**优势**：相比 ReAct 一边走一边想，整体规划性强。

**变种**：
- **ReWOO**：先规划全部工具调用，并行执行
- **LLM Compiler**：编译成 DAG 并行执行
- **Tree of Thoughts (ToT)**：树搜索式规划

---

## Q7: Agent 的记忆？

**答**：

**短期记忆**：
- 当前对话上下文
- 受 context 长度限制
- 超长后需要总结或裁剪

**长期记忆**：
- 向量存储（嵌入 + 相似检索）
- 摘要数据库
- 知识图谱

**Memory 类型**：
- **Working Memory**：当前任务的工作内存
- **Episodic Memory**：过去对话/事件
- **Semantic Memory**：抽象知识

**实现**：
- LangChain 的 `ConversationBufferMemory` / `VectorStoreMemory`
- MemGPT：分层记忆管理

---

## Q8: 工具使用的常见问题？

**答**：
1. **参数错误**：LLM 输出的参数类型/格式不对
   - 解：JSON Schema 严格约束、constrained decoding
2. **幻觉工具**：LLM 调用不存在的工具
   - 解：明确列出可用工具
3. **死循环**：反复调用同一工具
   - 解：限制最大步数、检测重复
4. **工具调用过于保守 / 激进**：
   - 解：调整 prompt 中的工具说明
5. **结果解析**：工具返回大段文本，LLM 难提取
   - 解：让工具返回结构化结果

---

## Q9: Computer Use / GUI Agent？

**答**：
**Anthropic Computer Use（2024.10）**：让 Claude 操作计算机。
- 截屏 → VLM 识别 → 点击坐标 / 输入文字
- 类似浏览器自动化但更通用

**类似工作**：
- OpenAI Operator
- Google Project Mariner
- 各种 web Agent（Browse-RL、WebVoyager）

**挑战**：
- 视觉识别 GUI 元素
- 准确定位坐标
- 容错（页面变化、加载延迟）
- 安全（防被劫持）

---

## Q10: MCP（Model Context Protocol）？

**答**：
**Anthropic 2024 提出**：标准化的 LLM-工具协议。

**核心**：
- 类似 LSP（Language Server Protocol）之于 IDE
- 工具服务器实现标准接口
- LLM 客户端通过协议调用任何 MCP 服务器

**好处**：
- 工具复用（一次实现，多 LLM 可用）
- 解耦
- 生态丰富

**支持**：
- Claude Desktop / Claude Code
- 越来越多框架支持

---

## Q11: Agent 评测？

**答**：

**Benchmark**：
- **AgentBench**：综合 Agent 能力
- **GAIA**：真实世界助手任务（搜索、文档处理）
- **WebArena / WebShop**：网页交互
- **SWE-Bench**：代码 Agent
- **BFCL**（Berkeley Function Calling Leaderboard）：工具调用

**指标**：
- 任务完成率
- 步数（效率）
- 工具调用准确率
- 成本（token）

---

## Q12: Agent 在生产中的实际应用？

**答**：
1. **客服**：意图识别 + 工具调用（查订单、改密码）
2. **编程**：Cursor、Claude Code、Cline 等
3. **数据分析**：自然语言 → SQL / Python
4. **运维**：监控告警 + 自动诊断
5. **办公自动化**：邮件分类、日程安排
6. **科研**：文献综述、实验设计
7. **客户挖掘**：网页爬虫 + 信息抽取
8. **GUI 自动化**：替代 RPA

---

## 🎯 高频追问

1. **Agent 的可靠性怎么提高**？多重检查（自我反思）、约束输出、工具白名单、人工 review 关键步骤。
2. **多 Agent 比单 Agent 强吗**？复杂任务多 Agent 优；简单任务单 Agent 已够。
3. **怎么处理 Agent 的"幻觉"？** 严格 grounding、工具调用前 plan-and-verify、关键决策人工 review。
4. **LangChain 真的好用吗**？社区诟病抽象过度；LangGraph 改善；许多团队用更轻的方案（直接 OpenAI SDK + 自定义）。
5. **Agent 成本怎么控制**？限制步数、上下文裁剪、用便宜模型做简单任务。
