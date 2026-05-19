# MoE（混合专家）

> Mixtral、DeepSeek-V3、Qwen-3 都用 MoE。路由 / 负载均衡是核心问题。

---

## 1. MoE 的核心思想

**朴素 FFN**：每个 token 经过同一个大 FFN。

**MoE FFN**：用多个"专家"（每个是一个小 FFN），通过**路由器**选择 $K$ 个专家处理 token。

**典型结构**：
- $N$ 个专家（如 8 / 64 / 256）
- 每个 token 激活 $K$ 个（如 2 / 8）
- **总参数大，激活参数小**

**优势**：
- 同等激活参数下，**总参数大几倍 → 能力更强**
- 推理时只计算激活的专家 → FLOP 与小模型相当
- "免费午餐"：更多参数，相同计算

**代价**：
- 显存巨大（要装下所有专家）
- 路由开销
- 训练难度高（负载均衡）

---

## 2. Sparse Gating + Top-K 路由

**路由器（Router）**：一个小线性层，输入 token hidden state，输出 $N$ 个专家的分数。

**伪代码**：
```python
def moe_forward(x, experts, router, K):
    # 算路由分数
    logits = router(x)               # [N]
    gates = softmax(logits)
    
    # 选 Top-K
    topk_vals, topk_idx = gates.topk(K)
    topk_vals = topk_vals / topk_vals.sum()   # 归一化
    
    # 加权求和激活专家的输出
    out = sum(topk_vals[i] * experts[topk_idx[i]](x) for i in range(K))
    return out
```

**符号说明**：
- $x$：当前 token 的 hidden state
- $\text{router}$：路由器（线性层）
- $\text{gates}$：所有专家的概率分布
- $K$：每 token 激活的专家数
- $\text{topk\_vals}, \text{topk\_idx}$：Top-K 的概率值和专家索引

**典型 $K$ 值**：
- $K = 1$（Switch Transformer）：极致稀疏
- $K = 2$（Mixtral）：典型
- $K = 8$（DeepSeek-V3 在 256 专家中选 8）：细粒度

---

## 3. 负载均衡问题

**问题**：
- 没有约束的话，路由器倾向少数"热门"专家
- 大部分专家几乎没被用 → 浪费参数
- 训练后期可能"赢者通吃"

### 3.1 辅助损失（Aux Loss）

经典做法（Switch Transformer）：

$$\mathcal{L}_{\text{aux}} = N \cdot \sum_{i=1}^N f_i \cdot P_i$$

**符号说明**：
- $N$：专家总数
- $f_i$：分配到专家 $i$ 的 token 比例（fraction）
- $P_i$：路由器给专家 $i$ 的平均概率
- 直觉：鼓励 $f_i$ 和 $P_i$ 都接近均匀

### 3.2 DeepSeek 的 Aux-loss-free

**DeepSeek-V3**：不用 aux loss，而是动态调整每个专家的 bias。
- 优势：aux loss 会干扰主任务
- 实现：根据负载情况调整每个专家的路由偏置

---

## 4. Token Drop / Expert Capacity

**问题**：即使均衡，某 batch 内某专家可能被过度分配 → 显存爆。

**Expert Capacity**：限制每个专家在一个 batch 内能处理的 token 数：

$$\text{capacity} = \text{capacity\_factor} \cdot \frac{\text{tokens per batch}}{N} \cdot K$$

**符号**：
- $\text{capacity\_factor}$：典型 1.0-1.5

**Token Drop**：超过容量的 token 被丢弃（不经任何专家，直接用残差）。

**No-Drop 训练**：DeepSeek-V3 用无 token-drop 训练，靠负载均衡保证。

---

## 5. DeepSeek-MoE 的设计

**两大创新**：

### 5.1 细粒度专家

- 把传统 FFN 切成更多更小的专家（如 8 大专家 → 64 小专家）
- 组合更灵活、路由更精细
- 总参数和激活参数控制不变

### 5.2 共享专家 + 路由专家

- 部分专家"始终激活"（**共享专家**，捕获共同模式）
- 部分通过路由选择（**路由专家**，捕获专项模式）

**DeepSeek-V3 配置**：
- 256 个路由专家 + 1 个共享专家
- 每 token 激活 8 个路由 + 1 个共享
- 总 671B 参数，激活 37B

---

## 6. 典型 MoE 对比

| 模型 | 总参 | 激活 | 专家数 | TopK |
|---|---|---|---|---|
| Switch Transformer | -- | -- | 多 | 1 |
| GShard | -- | -- | 多 | 2 |
| Mixtral 8×7B | 47B | 13B | 8 | 2 |
| Mixtral 8×22B | 141B | 39B | 8 | 2 |
| DeepSeek-V2 | 236B | 21B | 160 + 2 共享 | 6 |
| **DeepSeek-V3** | **671B** | **37B** | **256 + 1 共享** | **8** |
| Qwen-3-MoE | 235B | 22B | 128 | 8 |

---

## 7. 训练挑战

1. **路由不稳**：训练初期 router 随机，专家学不到特长
2. **专家坍缩**：某些专家被冷落，参数浪费
3. **通信开销**：EP 的 All-to-All 是分布式瓶颈
4. **显存压力**：所有专家都要持有
5. **混合精度**：路由分数对精度敏感

**对策**：
- Aux loss 或 bias 调整
- Capacity factor 控制
- 专家并行 + All-to-All 优化（DeepEP）
- Router z-loss（避免极端 logits）

---

## 8. 专家并行（EP）

**分布**：把 $N$ 个专家分到 $P$ 张卡上。每卡持有 $N/P$ 个专家。

**Forward**：
1. 每张卡的 token 计算路由
2. **All-to-All**：把每个 token 发到对应专家的卡
3. 专家计算
4. **All-to-All**：返回结果到原卡
5. 加权聚合

**通信瓶颈**：
- 每层 2 次 All-to-All
- 涉及大量小 tensor
- 大模型 MoE 训练中可能占 30%+

**优化**：DeepEP（DeepSeek 开源）、Flux（NVIDIA）通信 / 计算重叠。

---

## 9. MoE 推理特点

**优点**：
- 计算 FLOP = 激活参数（远小于总参数）
- 速度接近小模型，效果接近大模型

**挑战**：
- **显存吃紧**：必须装下所有专家
- **路由开销**：每 token 算路由
- **batch 不均匀**：不同 token 路由不同专家
- **EP 通信**：多卡推理时 All-to-All

**部署优化**：
- Speculative + MoE 组合加速
- Expert Caching：热门专家放显存，冷门 offload
- vLLM、SGLang 都支持 MoE

---

## 10. MoE vs Dense（稠密）对比

| 维度 | Dense | MoE |
|---|---|---|
| 总参数 | 中 | 大（数倍） |
| 激活参数 | = 总参 | 1/10 - 1/20 |
| 训练效率（同 FLOP） | 标准 | 更好（更多参数） |
| 推理 FLOP | 大 | 小（按激活参数） |
| 推理显存 | 小 | 大（按总参数） |
| 训练稳定性 | 好 | 难（路由问题） |
| 适用 | 边缘 / 小服务 | 云端 / 大流量 |

**经验**：
- 同 FLOP 训练下，MoE 比 Dense 强约 30-50%
- 同总参数下，Dense 比 MoE 强（但训练 FLOP 大得多）

---

## 11. 最简记忆

```text
MoE = 多个小专家 + 路由器，每 token 只激活 K 个
  总参数大（能力强）+ 激活参数小（推理省 FLOP）

负载均衡：
  Aux loss（Switch）  或  Bias 调整（DeepSeek-V3）

DeepSeek-MoE：
  细粒度专家 + 共享专家 + 路由专家

通信：All-to-All（两次/层），大模型瓶颈 → DeepEP/Flux 优化

部署：显存吃紧，但速度接近小模型。
```

---

## 🎯 高频追问

1. **MoE 的"专家"真学到了不同领域吗**？部分是（如某专家偏数学）；很多是"风格"或"语法"特化，不一定可解释。

2. **能把 Dense 转 MoE 吗**？可以（Upcycling）：把 FFN 复制 N 份作为初始 N 个专家。

3. **MoE 的路由器是什么模型**？一个小的线性层 → softmax。

4. **共享专家为什么有用**？避免每个专家重复学常识，让路由专家专注差异化能力。

5. **MoE 的辅助损失系数怎么调**？通常 0.01-0.1，太大损害主任务。
