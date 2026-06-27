# DeepSeek-R1 论文解读 · 面试题

> 对应原理文档：[07-DeepSeek-R1论文解读.md](../07-DeepSeek-R1论文解读.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: DeepSeek-R1 论文的核心宣言是什么？为什么重要？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**核心宣言**：推理能力可以通过**纯 RL** 激发，**不需要任何人工标注的推理轨迹**。

**论文价值**：
1. **R1-Zero 是关键证据**：base 模型直接做 GRPO + 规则奖励 RL → 自发涌现长 CoT、self-correction
2. **完全开源**：MIT License，权重可下载、可商用、可蒸馏
3. **实用流水线**：四阶段训练解决可读性 + 通用能力
4. **首次大规模验证 GRPO**：去 critic 的 PPO 变种
5. **诚实公开"失败章节"**：PRM、MCTS 都试过、都失败了——业界罕见
6. **结果**：AIME'24 79.8% / MATH-500 97.3%，**接近 o1-1217**

```text
o1 之前业界主流路线：SFT 长 CoT 数据 → 蒸馏
R1 的颠覆：跳过人标推理过程，让模型自己学会推理
```

---

## Q2: R1-Zero 和 R1 的本质区别是什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

| 维度 | R1-Zero | R1 |
|---|---|---|
| **SFT 数据** | **零**（直接在 base 上 RL） | 有 cold-start SFT |
| **训练阶段** | 1 阶段（纯 RL） | 4 阶段流水线 |
| **可读性** | 差（CoT 混乱、中英混用） | 好（语言一致性奖励） |
| **通用能力** | 弱（只优化推理） | 强（涵盖写作、QA、安全） |
| **意义** | 证明"纯 RL 可触发推理涌现" | 实际可部署的产品 |

**简记**：R1-Zero 是科学发现，R1 是工程落地。

---

## Q3: GRPO（Group Relative Policy Optimization）相比 PPO 改了什么？写出公式
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**最核心改动**：**去掉 critic**，用**组内归一化**做 advantage。

**算法步骤**：

1. 对同一 prompt $q$，从 old policy 采样 $G$ 个回答 $\{o_1, \dots, o_G\}$
2. 用规则或 RM 算每个奖励 $r_i$
3. **组内归一化**作为 advantage：

$$A_i = \frac{r_i - \text{mean}(r_1, \dots, r_G)}{\text{std}(r_1, \dots, r_G)}$$

4. PPO 风格 CLIP + KL 罚目标：

$$\mathcal{L}_{\text{GRPO}}(\theta) = \mathbb{E}\Big[\frac{1}{G}\sum_{i=1}^G \min(\rho_i A_i, \, \text{clip}(\rho_i, 1-\epsilon, 1+\epsilon) A_i) - \beta D_{KL}(\pi_\theta \| \pi_{\text{ref}})\Big]$$

其中 $\rho_i = \pi_\theta(o_i \mid q) / \pi_{\text{old}}(o_i \mid q)$。

**好处**：
- **省一半显存**（去掉 critic，对 671B 模型至关重要）
- 组内 baseline 替代 value function，方差被组归一化吸收
- 训练更稳定、更简单

```text
PPO 4 模型 → GRPO 3 模型（actor / RM / ref）
```

---

## Q4: R1-Zero 用的"规则奖励"是什么？为什么不用 RM？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

只有两类奖励，**无需任何 reward model**：

1. **Accuracy Reward**（答案对错）：
   - 数学：正则提取最终数字，对比标准答案
   - 代码：用编译器 + 测试用例执行
   - 对 → +1，错 → 0

2. **Format Reward**（格式合规）：
   - 推理过程必须放在 `<think>...</think>` 里
   - 答案放在 `<answer>...</answer>` 里
   - 用 → +1，没用 → 0

**为什么用规则而不用 RM**：

```text
规则不可 hack：答案对不对、格式合不合规，都是确定的
RM 容易被 hack：模型学会"骗高分"而非真本事
```

规则奖励对数学/代码够用，但对通用任务（聊天、写作）不行 → 所以 Stage 4 才引入 model-based reward。

---

## Q5: R1-Zero 的"涌现"现象具体表现？什么是 Aha moment？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

随训练步数增加，R1-Zero 自发地表现出以下行为：

1. **思考长度自动增长**：从几百 token 涨到几千 token
2. **Self-reflection（自我反思）**：自发说出"等等，让我重新检查一下"
3. **Verification（验证）**：算完一遍后主动再验证一次
4. **Strategy adaptation（动态调整策略）**：发现思路不对就换方法

**"Aha moment"**（论文原话）：训练某一步突然出现 self-correction，模型在 CoT 中说出类似：

> "Wait, I made a mistake, let me reconsider."

**意义**：**纯 RL（无 SFT 引导）能触发推理涌现**的标志性证据。

**追问：涌现是评估伪影吗？** R1 的涌现不是 benchmark 跃升的伪影——而是直接观察到模型 CoT 长度持续增长、特定 self-correction 短语出现频率上升，是行为级证据，比单一 benchmark 数字更可信。

---

## Q6: R1 的四阶段训练流水线是什么？每一阶段解决什么问题？
> 难度 ⭐⭐⭐⭐ ｜ 高频 🔥🔥🔥

```
[V3-Base]
   ↓ Stage 1: Cold Start
   数千条长 CoT 数据 → SFT
   ↓
   ↓ Stage 2: Reasoning RL
   GRPO + 规则奖励 + 语言一致性奖励
   ↓
   ↓ Stage 3: Rejection Sampling + SFT
   600K 推理数据 + 200K 通用数据
   → 在 V3-Base 上重新 SFT
   ↓
   ↓ Stage 4: All-Scenarios RL
   再做 RL，加 helpfulness / harmlessness 奖励
   ↓
[DeepSeek-R1]
```

**每阶段的作用**：

| 阶段 | 输入 | 解决问题 |
|---|---|---|
| **1. Cold Start SFT** | 数千条精修 CoT | 让模型先学会"长 CoT + 格式规范"，避免 R1-Zero 的早期不稳 |
| **2. Reasoning RL** | GRPO + 规则 + 语言一致性 | 让模型"会推理 + 单语种" |
| **3. Rejection SFT** | 600K 推理 + 200K 通用 | 让模型"会推理 + 会通用任务" |
| **4. All-Scenarios RL** | RM + 规则 | 让模型"会推理 + 通用 + 安全" |

**关键细节**：Stage 3 **从 V3-Base 重新 SFT**（不接 Stage 2 checkpoint），相当于"用 R1 的推理能力蒸馏自己"。

---

## Q7: R1 在 benchmark 上的表现如何？和 o1-1217 比谁强？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

| Benchmark | R1 | o1-1217 |
|---|---|---|
| **AIME'24** (Pass@1) | **79.8%** | 79.2% |
| **MATH-500** | **97.3%** | 96.4% |
| **Codeforces** (Elo) | **2029**（>96.3% 人类）| 2061 |
| **GPQA Diamond** | 71.5% | 75.7% |
| **MMLU** | 90.8% | 91.8% |

```text
推理任务 R1 ≈ o1-1217，AIME / MATH 略胜
GPQA / MMLU（知识）略低
```

**核心价值**：**完全开源 + MIT License + 蒸馏版可用 + 论文公开方法**，学术影响远超 o1。

---

## Q8: R1-Distill 系列是怎么做的？为什么"蒸馏 > 直接 RL"？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**做法**：用 R1 生成的 **800K** 数据对小模型做 SFT（**不做 RL**），得到 Distill-Qwen / Distill-Llama 系列：1.5B → 70B。

**关键蒸馏结果**：
- **R1-Distill-Qwen-32B**：AIME'24 **72.6%**，超过 o1-mini
- **R1-Distill-Qwen-7B**：AIME'24 55.5%，超过 GPT-4o（数学任务）

**论文对照实验**（同 Qwen2.5-32B）：

| 方法 | AIME'24 | MATH-500 |
|---|---|---|
| 直接 RL | 47.0% | 91.6% |
| **R1 数据 SFT（蒸馏）** | **72.6%** | **94.3%** |

**为什么蒸馏胜过直接 RL**：
- 小模型**探索能力弱**，自己采样的 rollout 质量不够
- 蒸馏让小模型直接学到 R1 已经验证过的"好路径"
- 大模型先做 frontier、再蒸馏到小模型，是**更经济的路径**

```text
论文结论：未来 frontier 模型先发展，再蒸馏到小模型。
```

---

## Q9: R1 论文为什么说 PRM 和 MCTS 都失败了？
> 难度 ⭐⭐⭐⭐ ｜ 高频 🔥🔥🔥

R1 论文 Section 4.2 罕见公开"踩过的坑"。

### PRM（Process Reward Model）失败

**预期**：对推理过程每一步打分，比 ORM 更密集。

**实际问题**：
1. **难定义"一步"**：自然语言推理没有明确步骤边界
2. **标注难扩展**：自动标不准、人标不 scale
3. **Reward Hacking**：模型学会刷过程分而非真推理

**论文原话**：

> "Building a PRM that is smarter than the model it is grading is a paradox."

### MCTS（Monte Carlo Tree Search）失败

**预期**：仿 AlphaGo，用搜索增强 LLM 推理。

**实际问题**：
1. **搜索空间指数爆炸**：token 词表 >> 围棋 361 个位置
2. **value model 不可靠**：很难评估"半句话"的价值
3. **路径过滤弱**：限制扩展节点后又陷入局部最优

**作者最终的选择**：

> "把搜索内化到模型权重里。"

通过 RL 训练，模型在 forward pass 中自动完成"搜索 + 验证 + 回溯"，**不需要外部搜索树**。

```text
最朴素的方案（GRPO + 规则奖励）赢了。
复杂的方案（PRM、MCTS）败了。
```

---

## Q10: R1 工程细节：用了哪些 V3 的基础设施？
> 难度 ⭐⭐ ｜ 高频 🔥

| 项 | 值 |
|---|---|
| Base 模型 | DeepSeek-V3-Base（671B MoE，激活 37B） |
| 训练精度 | **FP8**（V3 训练同款，省 ~50% 显存） |
| KV Cache 架构 | **MLA**（低秩潜空间压缩） |
| 上下文长度 | 32K → 128K（YaRN 扩展） |
| 开源协议 | MIT License（可商用、可蒸馏） |
| 模型大小 | 671B（R1 / R1-Zero）；1.5B/7B/8B/14B/32B/70B（Distill 版） |

**追问：R1 启发了哪些后续工作？** Qwen-QwQ、智谱 GLM-Zero、Moonshot K1.5、Kimi、Doubao 等推理模型基本沿用 **"GRPO + 规则奖励"** 框架。

---

## Q11: R1 论文带来的关键启示有哪些？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

1. **scaling laws 已被重定义**：推理时计算（RL + 长 CoT）开辟了和"训练时参数"叠加的新轴
2. **规则奖励 > RM**（在可验证领域）：不可 hack、更稳定
3. **GRPO > PPO**：去 critic 让大模型 RL 可承担
4. **蒸馏 > 直接 RL**（小模型）：未来路径是"先 frontier，再蒸馏"
5. **最朴素方案赢**：PRM、MCTS 都败给了 GRPO + 规则奖励
6. **完全开源的科学传统**：失败章节、复现细节都公开

---

## 🎯 自测清单

- [ ] 能用一句话讲 R1-Zero 的核心宣言（纯 RL + 规则奖励 → 推理涌现）
- [ ] 能默写 GRPO 的 advantage 公式 + 解释为何去 critic
- [ ] 能讲 R1-Zero 的 Accuracy + Format 两类规则奖励
- [ ] 能说出 R1-Zero 的 4 大涌现现象（含 Aha moment）
- [ ] 能按顺序讲全 R1 的四阶段流水线 + 每阶段动机
- [ ] 能讲为什么"蒸馏 > 小模型直接 RL"
- [ ] 能讲为什么 PRM 和 MCTS 在 R1 论文里失败
