# 监督微调 SFT 与 PEFT

> 把预训练模型变成"能用的助手"的第一步。LoRA 是 PEFT 主力。

---

## 1. SFT 和 Pretrain 的 loss 区别

**Pretrain CLM**：对所有 token 算 loss（每个位置预测下一个 token）。

**SFT 数据格式**：
```
<system>You are a helpful assistant.</system>
<user>What is 2+2?</user>
<assistant>2+2 equals 4.</assistant>
```

**Loss 计算**：

$$\mathcal{L}_{\text{SFT}} = -\sum_{t \in A} \log P(x_t \mid x_{<t}; \theta)$$

**符号说明**：
- $A$：assistant 部分的 token 位置集合
- 其他符号同 CLM

通常**只对 assistant 部分算 loss**（mask 掉 system/user）。原因：避免模型学习生成用户输入（毫无意义）。

实现上：构造 `loss_mask`，user/system 部分填 0。

---

## 2. 指令微调的目的

让模型从"续写文档"切换到"理解指令并按要求回答"：

1. 学习对话格式（system / user / assistant）
2. 学习工具调用、JSON 输出等格式
3. 灌输安全规则、风格偏好

**数据类型**：
- 通用：Alpaca、ShareGPT、OpenAssistant
- 专项：Code Alpaca、MetaMathQA、OpenHermes
- 多轮、工具调用、长文本……

**数据量**：
- LIMA 论文：1000 条高质量即可
- 现代实践：100K-1M，强调多样性 + 质量
- Llama-3.1：~10M 条 SFT 数据

---

## 3. 全参微调 vs PEFT

| 维度 | 全参微调 | LoRA / PEFT |
|---|---|---|
| 显存 | 极大（参数 + 梯度 + 优化器状态） | 1-10% 全参 |
| 训练速度 | 慢 | 快 |
| 效果上限 | 高 | 接近全参（多数任务） |
| 多任务部署 | 每任务一份完整模型 | 共享 base + 多个 adapter |
| 灾难遗忘 | 重 | 轻（base 冻结） |

**7B 模型显存对比**（BF16 + Adam）：
- 全参 SFT：~140 GB（需 A100/H100 多卡）
- LoRA SFT：~20 GB（消费级 GPU 可跑）
- QLoRA SFT：~6 GB（4090 即可）

---

## 4. LoRA 原理

### 4.1 核心假设

参数更新 $\Delta W$ 是**低秩**的，可分解：

$$W' = W + \Delta W = W + B A$$

**符号说明**：
- $W \in \mathbb{R}^{d \times d}$：冻结的预训练权重
- $\Delta W$：微调带来的更新
- $A \in \mathbb{R}^{r \times d}$：下投影
- $B \in \mathbb{R}^{d \times r}$：上投影
- $r$：LoRA 的秩（典型 4-64）

只训练 $A, B$（小），冻结 $W$（大）。

### 4.2 前向

$$y = W x + \frac{\alpha}{r} B A x$$

**符号说明**：
- $x$：输入
- $y$：输出
- $\alpha$：缩放系数（典型 $\alpha = 2r$）
- $\frac{\alpha}{r}$：缩放因子，控制 LoRA 强度

### 4.3 关键设计

- **A 用随机高斯初始化**，**B 用零初始化**
- 训练开始时 $BA = 0$，不破坏 base 模型
- 渐进式学习增量

### 4.4 参数量

| | 参数量 |
|---|---|
| 原始 $W$ | $d^2$（如 $d = 4096 \to 16.7M$） |
| LoRA $(A, B)$ | $2 d r$（如 $r = 16 \to 131K$） |

**缩减 ~128 倍**。

---

## 5. LoRA 加在哪些层？

**默认**：加在 Attention 的 $W^Q, W^V$（论文初版）。

**经验**：
- 加在所有 Attention 矩阵（QKVO）效果更好
- 加在 FFN 上效果再好一些（FFN 参数更多）
- 极致：加在所有 linear 层

工程上 HF peft 库默认 QKVO + FFN。

---

## 6. LoRA 超参选择

### 6.1 $r$（秩）

- 简单任务（指令）：$r = 4 \sim 8$
- 复杂任务（领域知识）：$r = 16 \sim 64$
- 经验：$r = 8$ 是甜点，往上边际递减

### 6.2 $\alpha$（缩放）

- 通常 $\alpha = 2r$ 或 $\alpha = r$
- 实际 $\Delta W$ 强度由 $\alpha / r$ 决定
- 调大 $\alpha$ 等价于调大 LoRA 学习率

### 6.3 学习率

LoRA 的 LR 一般比全参微调大（如 $1e^{-4} \sim 5e^{-4}$），因为只有少量参数训练，可以"激进"。

---

## 7. QLoRA：4-bit 量化 + LoRA

**核心**：把 base 模型量化到 4-bit（不可训练），LoRA 部分保持 BF16 可训练。

**三个关键创新**：

1. **NF4 数据类型**：Normal Float 4-bit，对正态分布权重最优
2. **Double Quantization**：把量化常数也量化，再省 ~0.4 bits/参数
3. **Paged Optimizers**：用 unified memory，避免梯度爆显存

**流程**：
1. Base 模型量化到 4-bit（冻结）
2. 推理时反量化到 BF16 计算（即时反量化）
3. LoRA 保持 BF16，可训练
4. 梯度只流到 LoRA

**效果**：
- 65B 模型可在单张 48GB 卡（A6000）上微调
- 效果接近 16-bit LoRA（QLoRA 论文）

---

## 8. 其他 PEFT 方法

| 方法 | 思路 | 特点 |
|---|---|---|
| **LoRA** | 低秩更新 $W + BA$ | 主流，简单有效 |
| **DoRA** | 分解 W 为方向 + 大小，分别 LoRA | 略优于 LoRA |
| **AdaLoRA** | 训练中自适应分配秩 | 复杂、收益边际 |
| **Prefix Tuning** | 在 K/V 前加可学前缀 | 效果不如 LoRA |
| **Prompt Tuning** | 只学 soft prompt token | 极轻量、效果有限 |
| **IA³** | 学缩放向量乘到激活 | 参数更少 |

```text
工业首选：LoRA / QLoRA，其他做研究探索。
```

---

## 9. SFT 常见坑

1. **过拟合**：SFT 数据少，几个 epoch 内 loss 暴跌但模型表现下降。**解**：早停、低 LR、少 epoch（1-3）
2. **灾难遗忘**：忘记预训练知识。**解**：小 LR、混入预训练数据、用 PEFT
3. **重复输出**：模型生成重复短语。**解**：检查数据质量、加 repetition penalty
4. **格式过拟合**：只会回答固定格式。**解**：增加格式多样性
5. **数据偏见**：GPT-4 生成的数据带 OpenAI 风格。**解**：多源数据

---

## 10. SFT 之后还需要 RL 吗？

**SFT 的局限**：
- 只能模仿"标准答案"
- 无法区分"好答案"和"更好答案"
- 不能学习"避免说什么"

**RLHF/DPO 的价值**：
- 利用偏好数据（A 比 B 好）
- 学习避免低质量、有害输出
- 让回答更符合人类偏好

**当前最佳实践**：SFT → DPO（或 PPO/GRPO）→ 持续迭代。

---

## 11. 最简记忆

```text
SFT：只对 assistant 部分算 loss（user/system mask 掉）

LoRA：W' = W + B·A
  A: r × d（高斯初始化）
  B: d × r（零初始化）
  α/r：缩放因子

QLoRA = 4-bit 量化 base + BF16 LoRA → 单卡微调 65B

r 选择：简单任务 4-8，复杂 16-32
LR：LoRA 比全参大几倍

PEFT 之王：LoRA / QLoRA。
```

---

## 🎯 高频追问

1. **LoRA 训完怎么部署**？两种：① 保持 base + adapter 分离（运行时合并）；② 把 LoRA 合并到 base 权重，部署单个模型。

2. **多个 LoRA 能合并吗**？可加权合并（weighted average），用于多任务，但有效果损失。

3. **LoRA 能用于预训练吗**？理论可（如 ReLoRA），但实践中预训练几乎都用全参。

4. **$r$ 越大越好吗**？不是，$r$ 大到一定程度（如 256）效果不再提升甚至下降。

5. **PEFT 能完全替代全参吗**？多数 SFT 场景可以；alignment（RLHF）和复杂能力提升仍倾向全参。
