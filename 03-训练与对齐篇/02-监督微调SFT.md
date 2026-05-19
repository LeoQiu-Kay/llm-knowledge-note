# 监督微调（SFT）与 PEFT

> 把预训练模型变成"能用的助手"的第一步，LoRA 是 PEFT 主力。

---

## Q1: SFT 和 Pretrain 的 loss 区别？

**答**：
**Pretrain CLM**：对所有 token 计算 loss（每个位置预测下一个 token）。

**SFT** 数据格式：
```
<system>You are a helpful assistant.</system>
<user>What is 2+2?</user>
<assistant>2+2 equals 4.</assistant>
```

**Loss 计算**：
- 通常**只对 assistant 部分计算 loss**（mask 掉 system 和 user 部分）
- 这避免模型学习生成用户输入（毫无意义）
- 实现：构造 `loss_mask`，user/system 部分填 0

**变体**：
- "User-loss SFT"：也对 user 部分算 loss，理论上提供更多信号，但效果一般持平或略差
- 现代主流：只对 assistant 部分算 loss

---

## Q2: 指令微调（Instruction Tuning）的目的？

**答**：
**目的**：
1. 让模型从"续写文档"切换到"理解指令并按要求回答"
2. 学习对话格式（system / user / assistant）
3. 灌输安全规则、风格偏好

**数据类型**：
- 通用指令：Alpaca、ShareGPT、OpenAssistant
- 任务专用：代码（Code Alpaca）、数学（MetaMathQA）、推理（OpenHermes）
- 长文本：LongAlpaca
- 多轮对话：Vicuna ShareGPT 多轮
- 工具调用：Glaive function-calling

**数据量**：
- LIMA 论文：1000 条高质量数据可达较好效果
- 现代实践：通常 100K-1M 量级，强调多样性 + 质量
- Llama 3.1：~10M 条 SFT 数据

---

## Q3: 全参数微调 vs PEFT 的对比？

**答**：

| 维度 | 全参微调 | LoRA / PEFT |
|------|---------|------------|
| 显存 | 极大（参数 + 梯度 + 优化器状态） | 1-10% 全参 |
| 训练速度 | 慢 | 快 |
| 效果上限 | 高 | 接近全参（多数任务） |
| 多任务部署 | 每任务一份完整模型 | 共享 base + 多个 adapter |
| 灾难遗忘 | 重 | 轻（base 冻结） |

**典型显存对比**（7B 模型，BF16）：
- 全参 SFT：~80 GB（需要 A100/H100）
- LoRA SFT：~20 GB（消费级 GPU 可跑）
- QLoRA：~6 GB（4090 即可）

---

## Q4: LoRA 的原理？

**答**：
**核心思想**：参数更新 $\Delta W$ 是低秩的，可分解。

**形式**：
$$W' = W + \Delta W = W + BA$$
- $W \in \mathbb{R}^{d \times d}$：冻结的预训练权重
- $A \in \mathbb{R}^{r \times d}$，$B \in \mathbb{R}^{d \times r}$
- $r \ll d$（典型 r=8, 16, 32）

**前向**：
```python
def lora_forward(x, W, A, B, alpha, r):
    return x @ W + (alpha / r) * x @ A.T @ B.T
```

**关键设计**：
- $A$ 用随机高斯初始化，$B$ 用零初始化 → 训练开始时 $\Delta W = 0$，不影响原始模型
- $\alpha / r$ 是缩放因子，让 LoRA 强度与秩解耦

**参数量**：
- 原始 $d \times d$
- LoRA：$d \cdot r + r \cdot d = 2dr$
- $d=4096, r=16$：参数量从 16M 降到 131K（120× 缩减）

---

## Q5: LoRA 加在哪些层？

**答**：
**默认**：加在 Attention 的 $W^Q, W^V$ 上（论文初版）。

**经验**：
- 加在所有 Attention 矩阵（QKVO）效果更好
- 加在 FFN 上效果再好一些（参数更多）
- 极致：加在所有 linear 层（包括 lm_head）

**取舍**：
- LoRA 层越多 → 参数越多，越接近全参，但仍远少于全参
- 工程上 PEFT 库（如 HF peft）默认 QKVO + FFN

---

## Q6: LoRA 的超参 r 和 α 怎么选？

**答**：
**r（秩）**：
- 太小：表达力不足
- 太大：失去 PEFT 优势，且容易过拟合
- 典型值：4-64
- 经验：简单任务 r=4-8，复杂任务 r=16-64
- "LoRA 论文"提到 r=1 在多数任务上也够用

**α（缩放）**：
- 通常 α = 2r 或 α = r
- 实际效果 $\Delta W$ 缩放为 $\alpha / r$
- 调大 α 等于调大 LoRA 学习率

**LR**：
- LoRA 的 LR 一般比全参微调大（如 1e-4 to 5e-4）
- 因为只有少量参数训练，可以"激进"一些

---

## Q7: QLoRA 是什么？

**答**：
**核心**：4-bit 量化 base 模型 + LoRA 微调。

**关键创新**：
1. **NF4 数据类型**：Normal Float 4-bit，对正态分布权重最优
2. **Double Quantization**：把量化常数本身也量化，再省 ~0.4 bits/参数
3. **Paged Optimizers**：用 unified memory，避免梯度爆显存

**流程**：
1. 把 base 模型量化到 4-bit（不可训练）
2. 推理时反量化到 BF16 计算（即时反量化）
3. LoRA 部分保持 BF16，可训练
4. 梯度只流到 LoRA

**效果**：
- 65B 模型可在单张 48GB 卡（A6000）上微调
- 效果接近 16-bit LoRA（QLoRA 论文）

---

## Q8: 其他 PEFT 方法？

**答**：

| 方法 | 思路 | 特点 |
|------|------|------|
| **LoRA** | 低秩更新 $W + BA$ | 主流，简单有效 |
| **DoRA** | 分解 W 为方向 + 大小，分别 LoRA | 略优于 LoRA |
| **AdaLoRA** | 训练中自适应分配秩 | 复杂，收益边际 |
| **VeRA** | 共享 A、B，只学缩放向量 | 参数更省 |
| **Prefix Tuning** | 在 K/V 前加可学前缀 | 效果不如 LoRA |
| **Prompt Tuning** | 只学 soft prompt token | 极轻量，但效果有限 |
| **P-Tuning v2** | 每层都加 prompt | 中间路线 |
| **IA³** | 学缩放向量乘到激活 | 参数更少 |

**实际选择**：**LoRA / QLoRA 仍是工业首选**。

---

## Q9: SFT 中的常见坑？

**答**：
1. **过拟合**：SFT 数据有限，几个 epoch 内 loss 暴跌但模型表现下降（"记住"模板）。解法：早停、低 LR、少 epoch（通常 1-3 epoch）。
2. **灾难遗忘**：忘记预训练知识。解法：保持 LR 小、混入预训练数据、PEFT 而非全参。
3. **重复输出**：模型生成重复短语。解法：检查数据质量、加入 repetition penalty、调温度。
4. **格式过拟合**：只会回答固定格式。解法：增加格式多样性。
5. **数据偏见**：数据集偏好（如 GPT-4 生成数据带 OpenAI 风格）传染到模型。解法：多源数据。

---

## Q10: SFT 之后还需要 RL 吗？

**答**：
**SFT 的局限**：
- 只能模仿数据中的"标准答案"
- 无法区分"好回答"和"更好回答"的细微差别
- 不能学习"避免说什么"

**RLHF/DPO 的价值**：
- 利用偏好数据（A 比 B 好）做更细的优化
- 学习避免低质量、有害、不安全的输出
- 让回答更符合人类偏好（helpful、harmless、honest）

**当前最佳实践**：SFT → DPO（或 PPO/GRPO）→ 持续迭代。

---

## 🎯 高频追问

1. **LoRA 训完怎么部署**？两种方式：①保持 base + adapter 分离（运行时合并）；②merge LoRA 到 base 权重，部署单个模型。
2. **多个 LoRA 能合并吗**？可以加权合并（weighted average），常用于多任务，但有效果损失。
3. **LoRA 能用于预训练吗**？理论上可（如 ReLoRA），但实践中预训练几乎都用全参。
4. **r 选得越大越好吗**？不是，r 大到一定程度（如 256）效果不再提升甚至下降。
5. **PEFT 能完全替代全参吗**？多数 SFT 场景可以；但 alignment 阶段（RLHF）和复杂能力提升仍倾向全参。
