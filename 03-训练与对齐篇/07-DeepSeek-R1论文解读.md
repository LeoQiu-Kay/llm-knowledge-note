# DeepSeek-R1 论文解读

> **论文**：DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning
> **arXiv**：[2501.12948](https://arxiv.org/abs/2501.12948)（2025 年 1 月）
> **本地 PDF**：[`./paper/DeepSeek-R1-2501.12948.pdf`](./paper/DeepSeek-R1-2501.12948.pdf)
> **核心宣言**：推理能力可以通过**纯 RL** 激发，**不需要任何人工标注的推理轨迹**。

---

## 0. 论文价值速览

| 维度 | 创新点 |
|---|---|
| **方法论** | 证明 base 模型可以**纯靠 RL** 学到长 CoT、自我反思——R1-Zero 触发"涌现"现象 |
| **实用流水线** | 四阶段训练（Cold Start → Reasoning RL → Rejection Sampling SFT → All-Scenarios RL）解决 R1-Zero 的可读性问题 |
| **算法** | 在 DeepSeekMath 提出的 **GRPO** 上完成大规模 RL 验证 |
| **蒸馏** | 用 R1 生成的数据 SFT 小模型（1.5B-70B），小模型推理能力**远超直接 RL** |
| **诚实** | 论文专门写了"失败的尝试"章节（PRM、MCTS）—— 极罕见 |
| **结果** | AIME'24 79.8% / MATH-500 97.3% / Codeforces 2029 Elo（≈o1-1217 水平） |

---

## 1. 背景：为什么需要 R1

**OpenAI o1 之后的核心问题**：
- o1 闭源、训练方法保密
- 业界主流路线是 **SFT 长 CoT 数据 + 蒸馏**，但需要大量人标推理过程
- 是否能跳过"人标推理过程"，让模型自己学到推理？

**DeepSeek 的答案**：可以，纯 RL + 规则奖励就够，**R1-Zero 是关键证据**。

---

## 2. R1-Zero：纯 RL 训练，无 SFT

### 2.1 训练设置

| 项 | 设置 |
|---|---|
| **Base 模型** | DeepSeek-V3-Base（671B MoE） |
| **RL 算法** | GRPO（DeepSeekMath 提出） |
| **奖励** | **规则奖励**（无 RM） |
| **SFT 数据** | **零**（直接在 base 上 RL） |
| **Prompt 模板** | 强制 `<think>...</think><answer>...</answer>` 格式 |

### 2.2 GRPO 算法核心

PPO 需要 4 个模型（actor / critic / RM / ref），GRPO **去掉 critic**，用**组内归一化**做 advantage。

**采样**：对同一 prompt $q$，从 old policy 采样 $G$ 个回答 $\{o_1, \dots, o_G\}$。

**Advantage**（组内归一化）：

$$A_i = \frac{r_i - \text{mean}(r_1, \dots, r_G)}{\text{std}(r_1, \dots, r_G)}$$

**符号说明**：
- $G$：组大小（典型 16-64）
- $r_i$：第 $i$ 个回答的奖励（规则给出）
- $A_i$：第 $i$ 个回答的优势（组内归一化后的标量）
- $\text{mean}, \text{std}$：组内均值、标准差

**目标函数**（PPO 风格 clip + KL 罚）：

$$\mathcal{L}_{\text{GRPO}}(\theta) = \mathbb{E}\left[\frac{1}{G}\sum_{i=1}^G \min\big(\rho_i \, A_i, \; \text{clip}(\rho_i, 1-\epsilon, 1+\epsilon) A_i\big) - \beta \, D_{KL}(\pi_\theta \, \| \, \pi_{\text{ref}})\right]$$

**符号说明**：
- $\rho_i = \pi_\theta(o_i \mid q) / \pi_{\text{old}}(o_i \mid q)$：重要性采样比
- $\epsilon$：clip 阈值（典型 0.2）
- $\beta$：KL 惩罚系数
- $\pi_{\text{ref}}$：参考模型（冻结，防偏离）
- $\pi_{\text{old}}$：上一轮的策略

```text
省了 critic（少一个 70B 大模型），显存大幅下降。
组内 baseline 替代 value function，方差被组归一化吸收。
```

### 2.3 规则奖励（Rule-based Reward）

只有两类奖励，**无需 reward model**：

1. **Accuracy Reward**（答案对错）：
   - 数学：从答案中正则提取最终数字，对比标准答案
   - 代码：用编译器 + 测试用例执行
   - 对 → +1，错 → 0

2. **Format Reward**（格式合规）：
   - 模型必须把推理过程放在 `<think>...</think>` 里
   - 答案放在 `<answer>...</answer>` 里
   - 用 → +1，没用 → 0

```text
为什么用规则而不用 RM？
  规则不可 hack：答案对不对，是确定的。
  RM 容易被 hack：模型学到"骗高分"而非真本事。
```

### 2.4 涌现现象（关键发现）

随训练步数增加，R1-Zero 自发地表现出以下行为：

1. **思考长度自动增长**：从几百 token 涨到几千 token
2. **Self-reflection（自我反思）**：自发说出"等等，让我重新检查一下"
3. **Verification（验证）**：算完一遍后主动再验证一次
4. **Strategy adaptation（动态调整策略）**：发现思路不对就换方法

**"Aha moment"**（论文原话）：训练某一步突然出现 self-correction，模型在 CoT 中说出类似 "Wait, I made a mistake, let me reconsider"。这是**纯 RL 触发推理涌现**的标志性证据。

### 2.5 R1-Zero 的问题

虽然能力强，但：
- **可读性差**：CoT 混乱、跳跃
- **中英文混用**：模型自由切换语言

→ 引出 R1 的四阶段流水线来修正。

---

## 3. R1：四阶段训练流水线

```
[V3-Base]
   ↓ Stage 1: Cold Start
   数千条长 CoT 数据 → SFT
   ↓
[V3-Base + cold-start SFT]
   ↓ Stage 2: Reasoning RL
   GRPO + 规则奖励 + 语言一致性奖励
   ↓
[Reasoning model]
   ↓ Stage 3: Rejection Sampling + SFT
   用上一步采样 600K 高质量推理数据
   + 200K 通用数据（写作/QA/自我认知）
   → 在 V3-Base 上重新 SFT
   ↓
[Mixed model]
   ↓ Stage 4: All-Scenarios RL
   再做一次 RL，覆盖所有场景 + 加入 helpfulness/harmlessness 奖励
   ↓
[DeepSeek-R1 (final)]
```

### 3.1 Stage 1: Cold Start（冷启动 SFT）

**目的**：避免直接 RL 时的早期不稳，给模型一个"好的起点"。

**数据**：手工/半自动收集的**数千条**带长 CoT 的样本。
- 来自 R1-Zero 输出的精修版（人工 + few-shot）
- 强制可读、单语种

**作用**：让模型先学会"长 CoT + 格式规范"的基础。

### 3.2 Stage 2: Reasoning-Oriented RL

跟 R1-Zero 一样用 GRPO + 规则奖励，但**多了一个语言一致性奖励**：

$$r_{\text{lang}} = \frac{\text{目标语言词数}}{\text{CoT 总词数}}$$

**符号**：CoT 中目标语言（如英文）占比越高，奖励越大。

**代价**：论文承认这会让评测分**略微下降**，但人类喜好显著上升。

### 3.3 Stage 3: Rejection Sampling + SFT

**Rejection Sampling**（拒绝采样）：
- 用 Stage 2 的 checkpoint 对大量 prompt 采样多次
- **只保留答案正确的**
- 收集约 **600K 推理数据**

加上 V3 的通用 SFT 数据（**200K**：写作、事实 QA、self-cognition、翻译等）。

**关键**：从 **V3-Base 重新 SFT**（而不是接着 Stage 2 的 checkpoint 训）—— 这等于"用 R1 的推理能力去蒸馏自己"。

### 3.4 Stage 4: All-Scenarios RL

最后一轮 RL，**目标三合一**：
- **推理任务**：继续用规则奖励
- **通用任务**：用 RM（model-based reward）评估 helpfulness、harmlessness
- **混合**：覆盖各类 prompt

```text
四阶段总结：
  1. Cold Start  让模型"会写长 CoT"
  2. Reasoning RL 让模型"会推理"
  3. Rejection SFT 让模型"会推理 + 会通用任务"
  4. Final RL     让模型"会推理 + 通用 + 安全"
```

---

## 4. 性能（vs o1-1217）

### 4.1 R1 主模型

| Benchmark | R1 | o1-1217 |
|---|---|---|
| **AIME'24** (Pass@1) | **79.8%** | 79.2% |
| **MATH-500** | **97.3%** | 96.4% |
| **Codeforces** (Elo) | **2029**（>96.3% 人类参赛者）| 2061 |
| **GPQA Diamond** | 71.5% | 75.7% |
| **MMLU** | 90.8% | 91.8% |

```text
推理任务上 R1 ≈ o1-1217，部分指标领先。
完全开源（MIT License），权重可下载。
```

### 4.2 蒸馏小模型（用 R1 生成的 800K 数据做 SFT）

| 模型 | Base | AIME'24 | MATH-500 | GPQA-D | LiveCodeBench | Codeforces |
|---|---|---|---|---|---|---|
| R1-Distill-Qwen-1.5B | Qwen2.5-1.5B | 28.9% | 83.9% | 33.8% | 16.9% | 954 |
| R1-Distill-Qwen-7B | Qwen2.5-7B | 55.5% | 92.8% | 49.1% | 37.6% | 1189 |
| R1-Distill-Llama-8B | Llama-3.1-8B | 50.4% | 89.1% | 49.0% | 39.6% | 1205 |
| R1-Distill-Qwen-14B | Qwen2.5-14B | 69.7% | 93.9% | 59.1% | 53.1% | 1481 |
| **R1-Distill-Qwen-32B** | Qwen2.5-32B | **72.6%** | **94.3%** | **62.1%** | **57.2%** | **1691** |
| R1-Distill-Llama-70B | Llama-3.3-70B | 70.0% | 94.5% | 65.2% | 57.5% | 1633 |

**关键结论**：
- **R1-Distill-Qwen-32B 超越 o1-mini**
- **R1-Distill-Qwen-7B 超越 GPT-4o**
- 论文实验对比："对小模型做 R1 数据 SFT" > "对小模型直接 RL"（详见下节）

---

## 5. R1 vs OPD vs RLHF vs SFT：训练范式定位

| 范式 | 数据来源 | 奖励信号 | 是否需要 RM | 代表 |
|---|---|---|---|---|
| **SFT** | 人/教师写的固定数据 | 每 token NLL | 否 | LLaMA-Instruct |
| **RLHF (PPO)** | 学生 rollout | RM 给 episode 奖励 + KL 罚 | 是（学的 RM） | ChatGPT |
| **R1 风格 RL (GRPO)** | 学生 rollout | **规则奖励**（accuracy + format） | 否 | DeepSeek-R1 |
| **OPD**（前一篇） | 学生 rollout | per-token reverse KL（教师即 RM） | 否（用教师） | Thinking Machines |

```text
R1 的独到之处：
  规则奖励替代 RM → 不可 hack
  GRPO 替代 PPO   → 省 critic
  四阶段流水线    → 解决可读性 + 通用能力
```

---

## 6. 蒸馏 vs 直接 RL（小模型场景）

论文做了对照实验：在 **Qwen2.5-32B** 上分别：
1. **直接 RL**（同 R1-Zero 配方）
2. **R1 数据 SFT**（用 R1 生成的 800K 数据）

| 方法 | AIME'24 | MATH-500 |
|---|---|---|
| Qwen2.5-32B + 直接 RL | 47.0% | 91.6% |
| **Qwen2.5-32B + R1 数据 SFT（蒸馏）** | **72.6%** | **94.3%** |

**论文结论**：
- 大模型推理能力可以**蒸馏到**小模型
- 小模型直接 RL 探索能力弱，效果远不如蒸馏
- **未来 frontier 模型先发展，再蒸馏到小模型** 是更经济的路径

---

## 7. 失败的尝试（极有价值的章节）

论文 Section 4.2 罕见地公开"踩过的坑"。

### 7.1 PRM（Process Reward Model）— 失败

**预期**：对推理过程的每一步打分，比 ORM 信号更密集。

**实际遇到的三大问题**：

1. **难定义"一步"**：自然语言推理没有明确的步骤边界
2. **标注难扩展**：自动标不准、人工标不 scale
3. **Reward Hacking**：模型学会刷分而非真推理

**论文原话**：
> "Building a PRM that is smarter than the model it is grading is a paradox."

PRM 反而**增加复杂度而不带来稳定收益**。

### 7.2 MCTS（Monte Carlo Tree Search）— 失败

**预期**：仿 AlphaGo，用搜索增强 LLM 推理。

**实际遇到的问题**：
1. **搜索空间指数级爆炸**：token 词表远大于围棋的 361 个位置
2. **value model 不可靠**：很难评估"半句话"的价值
3. **路径过滤弱**：限制扩展节点后又容易陷入局部最优

**论文结论**：MCTS 对 LLM 推理"投入产出比极低"。

### 7.3 作者最终的选择

**"把搜索内化到模型权重里"**——通过 RL 训练，模型学会在 forward pass 中自动完成"搜索 + 验证 + 回溯"，不需要外部搜索树。

```text
最朴素的方案（GRPO + 规则奖励）赢了。
复杂的方案（PRM、MCTS）败了。
```

---

## 8. 工程细节

| 项 | 值 |
|---|---|
| Base 模型 | DeepSeek-V3-Base（671B MoE，激活 37B） |
| 训练精度 | FP8（V3 训练同款，省 ~50% 显存） |
| KV Cache 架构 | MLA（低秩潜空间压缩） |
| 上下文长度 | 32K → 128K（YaRN 扩展） |
| 开源协议 | MIT License（可商用、可蒸馏） |
| 模型大小 | 671B（R1 / R1-Zero）；1.5B/7B/8B/14B/32B/70B（蒸馏版） |

---

## 9. 一句话总结

```text
R1-Zero：证明纯 RL + 规则奖励可以让 base 模型"自学"推理
R1：    四阶段流水线把 R1-Zero 修成"既能推理又能聊天"
蒸馏：  用 R1 生成的数据 SFT 小模型 → 远胜直接 RL
GRPO：  去 critic + 组内 baseline + 规则奖励 → 比 PPO 简单稳定

关键启示：
  scaling laws 已被推理时计算 + RL 重新定义。
  最朴素的方案常常赢过看起来"更聪明"的方案（PRM/MCTS）。
```

---

## 🎯 高频追问

1. **R1-Zero 和 R1 的本质区别**？R1-Zero 只有 stage 2（纯 RL，无 SFT 引导）；R1 加了三阶段流水线（cold start SFT、rejection sampling SFT、all-scenarios RL），解决了可读性和通用能力问题。

2. **为什么 GRPO 比 PPO 好用**？省了 critic（少一个大模型显存）+ 组内 baseline 替代 value function（方差小、更稳）。RL 训练 671B 模型时这个差异巨大。

3. **规则奖励真的够吗**？数学/代码够（答案对错可验证）。但通用任务（聊天、写作）就不行——所以 Stage 4 引入 model-based reward。

4. **为什么蒸馏 > 小模型直接 RL**？小模型探索能力弱，自己采样的轨迹质量不够；蒸馏直接学到 R1 已验证的"好路径"。

5. **R1 和 OpenAI o1 的差距**？推理任务上 R1 ≈ o1-1217。在 GPQA Diamond 上略低。但 R1 完全开源 + 蒸馏版可用 + 论文公开方法 = 学术影响远超 o1。

6. **R1 启发了哪些工作**？后续 Qwen-QwQ、智谱 GLM-Zero、Moonshot K1.5、Kimi、Doubao 等推理模型基本沿用 "GRPO + 规则奖励" 框架。

7. **R1-Distill-Qwen-7B 真的超过 GPT-4o？** 在数学/代码 benchmark 上是；通用对话上 GPT-4o 仍领先。

---

## 来源

- [arXiv: DeepSeek-R1 论文原文](https://arxiv.org/abs/2501.12948) | [PDF 直链](https://arxiv.org/pdf/2501.12948)
- [HuggingFace: DeepSeek-R1 模型卡](https://huggingface.co/deepseek-ai/DeepSeek-R1)
- [GitHub: deepseek-ai/DeepSeek-R1](https://github.com/deepseek-ai/deepseek-r1)
- [Aman's AI Journal - DeepSeek-R1 详解](https://aman.ai/primers/ai/deepseek-R1/)
- [Phil Schmid - How DeepSeek-R1 was trained](https://www.philschmid.de/deepseek-r1)
- [Yugen.ai - Math Behind GRPO](https://medium.com/yugen-ai-technology-blog/understanding-the-math-behind-grpo-deepseek-r1-zero-9fb15e103a0a)
- 本地 PDF：[`./paper/DeepSeek-R1-2501.12948.pdf`](./paper/DeepSeek-R1-2501.12948.pdf)
