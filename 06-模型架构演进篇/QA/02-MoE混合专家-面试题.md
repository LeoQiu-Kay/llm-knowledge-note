# MoE 混合专家 · 面试题

> 对应原理文档：[02-MoE混合专家.md](../02-MoE混合专家.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: MoE 的核心思想是什么？为什么是"免费午餐"？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**MoE**（Mixture of Experts，混合专家）：把传统 FFN 替换为 $N$ 个"专家"（每个是一个小 FFN）+ 一个**路由器**（router），每个 token 只激活 $K$ 个专家（典型 $K=2$ 或 $K=8$）。

**"免费午餐"的含义**：
- 总参数：$N$ 倍 FFN → 容量大、能力强
- 激活参数：只算 $K$ 个 → FLOP 只增加 $K/N$
- 同等推理 FLOP 下，模型容量大几倍 → **能力按总参，速度按激活**

公式上：

$$\text{output} = \sum_{i \in \text{TopK}} g_i(x) \cdot E_i(x)$$

**符号**：$E_i$ 第 $i$ 个专家，$g_i(x)$ 路由权重（gate 输出）。

**代价**：
1. 显存大（要装所有专家）
2. 路由开销
3. 负载均衡难（训练不稳）
4. EP（专家并行）有 All-to-All 通信瓶颈

**追问：MoE 为什么没"早就"成为标准？** ① 训练稳定性差（路由难调）；② 显存压力大；③ 通信开销在小规模看不出收益。直到 Switch Transformer（2021）+ Mixtral（2023）+ DeepSeek-V3（2024）才把工程问题逐步解决。

---

## Q2: MoE 的路由器是怎么工作的？写出 Top-K 路由的伪代码
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**路由器**：一个**小线性层**（hidden_size → $N$），输出每个专家的 logits。

```python
def moe_forward(x, experts, router, K):
    # 1. 算路由分数
    logits = router(x)               # [N]
    gates = softmax(logits)          # 所有专家的概率
    
    # 2. 选 Top-K
    topk_vals, topk_idx = gates.topk(K)
    topk_vals = topk_vals / topk_vals.sum()  # 归一化（重要）
    
    # 3. 加权聚合
    out = sum(topk_vals[i] * experts[topk_idx[i]](x) for i in range(K))
    return out
```

**为什么 Top-K 后要归一化**：softmax 后 Top-K 之和 < 1，归一化让它和为 1，保持输出 scale 稳定。

**典型 $K$**：
- $K = 1$：Switch Transformer，极致稀疏
- $K = 2$：Mixtral，最经典
- $K = 8$（256 中选 8）：DeepSeek-V3，细粒度

**追问：路由器为什么能学到"分工"？** 训练中反向传播只会回流到激活的专家 → 该专家被强化在"它擅长的 token"上；同时路由器也接收梯度，学会"哪种 token 该送哪个专家"。这是一个自组织过程。

---

## Q3: MoE 的负载均衡问题是什么？两大解法的核心差异？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**问题**：没有约束，路由器倾向少数"热门"专家——大部分专家几乎没被用，参数浪费，训练后期"赢者通吃"。

**解法 1：辅助损失（Aux Loss，Switch Transformer）**

$$\mathcal{L}_{\text{aux}} = N \cdot \sum_{i=1}^N f_i \cdot P_i$$

**符号**：
- $N$ 专家总数
- $f_i$ 分到专家 $i$ 的 token 比例（fraction，离散）
- $P_i$ 路由器给专家 $i$ 的平均概率（连续，可导）
- $f_i$ 不可导，但 $P_i$ 可导；让 $f_i \cdot P_i$ 都接近 $1/N$ 即均衡

最终 loss = 主任务 loss + $\alpha \cdot \mathcal{L}_{\text{aux}}$，$\alpha$ 典型 0.01-0.1。

**解法 2：Aux-loss-free（DeepSeek-V3）**

不加 loss，而是给每个专家维护一个**动态 bias** $b_i$：

$$\text{routing\_score}_i = \text{logits}_i + b_i$$

- 若专家 $i$ 在最近 batch 被分配过多 → $b_i$ 减小
- 若被分配过少 → $b_i$ 增大
- 推理时 $b_i$ 不参与最终权重，只影响 Top-K 选择

**两者核心差异**：

| 维度 | Aux Loss | Aux-loss-free（Bias） |
|---|---|---|
| 形式 | 加 loss 项 | 调路由分数 |
| 对主任务影响 | 干扰（loss 拉扯主目标） | 不干扰 |
| 调参 | $\alpha$ 难调 | bias 更新率 |
| 代表 | Switch / Mixtral | DeepSeek-V3 |

**追问：为什么 DeepSeek-V3 要去掉 Aux Loss？** Aux Loss 会拉扯主任务 loss 方向，让模型在"对均衡"和"对预测"之间妥协；规模大了之后这个妥协代价高。Bias 调整只影响"分配"不影响"梯度方向"，主任务不受干扰。

---

## Q4: Expert Capacity 和 Token Drop 是什么？怎么算？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**问题**：即使均衡了，某 batch 里某专家也可能被过度分配 → 该专家显存爆炸。

**Expert Capacity**：限制每个专家在一个 batch 内能处理的 token 数：

$$\text{capacity} = \text{capacity\_factor} \cdot \frac{T \cdot K}{N}$$

**符号**：
- $T$ batch 内总 token 数
- $K$ Top-K
- $N$ 专家数
- $\text{capacity\_factor}$ 典型 1.0-1.5（>1 留余量）

直觉：均衡情况下每专家平均分到 $TK/N$ 个 token，capacity 在此基础上放宽 1.x 倍。

**Token Drop**：超过容量的 token 被**丢弃**——不经任何专家，直接用残差通过。等于"这个 token 没经过 FFN"。

**No-Drop 训练**：DeepSeek-V3 用无 token-drop 训练，靠 bias 均衡保证不溢出。

**追问：capacity_factor 太大太小会怎样？** 太小 → 大量 token drop，效果差；太大 → 显存占用接近无限制，失去 capacity 意义。1.25 是常用折中。

---

## Q5: DeepSeek-MoE 的"细粒度专家 + 共享专家"是什么？为什么有用？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**两大创新**：

### 1. 细粒度专家

- 把传统"8 大专家"切成"64 小专家"（每个小 1/8）
- 总参数和激活参数不变（$K$ 也按比例扩大）
- **组合更灵活**：256 选 8 = $C_{256}^8 \approx 4 \times 10^{14}$ 种组合 vs 8 选 2 = 28 种
- 路由更精细，专家可学到更细致的分工

### 2. 共享专家（Shared Expert）

- 部分专家**始终激活**（不参与路由，每个 token 都过）
- 部分通过路由选择（**路由专家**）
- 共享专家学"通用模式"，路由专家学"专项模式"

**DeepSeek-V3 配置**：
- 256 个路由专家 + 1 个共享专家
- 每 token 激活 8 个路由 + 1 个共享 = 9 个专家
- 总参 671B / 激活 37B / 激活比 5.5%

**为什么共享专家有用**：
- 避免每个路由专家都重复学"常识"（如基础语法、常用模式）
- 让路由专家专注差异化能力
- 等价于"硬编码"了一个"必学"的通用专家

**追问：细粒度专家会增加路由开销吗？** 是的——256 选 8 比 8 选 2 路由计算大。但路由开销相对 FFN 计算很小，且 256 个专家的"组合自由度"带来的能力提升远大于路由代价。

---

## Q6: MoE 的专家并行（EP）是怎么做的？All-to-All 为什么是瓶颈？
> 难度 ⭐⭐⭐⭐ ｜ 高频 🔥🔥🔥

**专家并行（EP，Expert Parallelism）**：把 $N$ 个专家分到 $P$ 张卡上，每卡持有 $N/P$ 个专家。

**Forward 流程**：

1. 每张卡的 token 在本卡算路由（路由器是复制的）
2. **All-to-All #1**：把每个 token 发到对应专家的卡（按路由结果）
3. 各卡上的专家计算
4. **All-to-All #2**：把结果发回到原 token 所在的卡
5. 原卡上加权聚合

**为什么 All-to-All 是瓶颈**：
- **小 tensor 多**：每张卡要发若干小块到 P-1 张其他卡 → 通信开销大
- **同步**：必须等最慢那张卡 → 木桶效应
- **每层 2 次**：训练时 forward + backward = 4 次 All-to-All / 层
- 大模型 MoE 训练中通信可占 **30%+** 时间

**优化方案**：
- **DeepEP**（DeepSeek 开源）：定制的 All-to-All，低延迟高吞吐
- **Flux**（NVIDIA）：通信/计算重叠
- **专家放置策略**：把热门专家分散，冷门集中

**追问：EP 和 TP（张量并行）能同时用吗？** 可以。典型组合 TP 处理 Attention/Embedding、EP 处理 MoE FFN，每个 token 在两套并行间切换。DeepSeek-V3 训练用 EP + PP + DP（不用 TP，避开它的低效）。

---

## Q7: 主流 MoE 模型的总参/激活/专家配比是什么样？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

| 模型 | 总参 | 激活 | 专家 | TopK | 激活比 |
|---|---|---|---|---|---|
| Switch Transformer | — | — | 多 | 1 | 极稀疏 |
| **Mixtral 8×7B** | 47B | 13B | 8 | 2 | 28% |
| Mixtral 8×22B | 141B | 39B | 8 | 2 | 28% |
| DeepSeek-V2 | 236B | 21B | 160 + 2 共享 | 6 | 9% |
| **DeepSeek-V3** | **671B** | **37B** | **256 + 1 共享** | **8** | **5.5%** |
| Qwen-3-MoE | 235B | 22B | 128 | 8 | 9% |

**演进趋势**：
1. 专家数从 8 → 256（更细粒度）
2. TopK 从 2 → 8（更细粒度但 K/N 比保持低）
3. 激活比从 28% → 5%（更稀疏，更"免费午餐"）
4. 共享专家成为标配（DeepSeek 引领）

**追问：激活比是不是越小越好？** 不是。激活比太小 → 单个 token 看到的专家太少，能力不足；过大 → 失去 MoE 的稀疏优势。5-10% 是当前主流甜区。

---

## Q8: MoE 训练有哪些独有的稳定性问题？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

| 问题 | 现象 | 对策 |
|---|---|---|
| **路由不稳** | 训练初期 router 随机，专家学不到特长 | warmup、初始化技巧 |
| **专家坍缩** | 某些专家被冷落，参数浪费 | Aux Loss / Bias 调整 |
| **路由极端** | logits 爆炸，softmax 接近 one-hot | **Router z-loss**（惩罚大 logits） |
| **通信瓶颈** | All-to-All 占 30%+ | DeepEP / Flux 重叠 |
| **显存压力** | 所有专家都要持有 | EP + ZeRO + offload |
| **精度敏感** | 路由分数小数差异敏感 | FP32 路由（其余 BF16/FP8） |

**Router z-loss**（避免极端 logits）：

$$\mathcal{L}_z = \frac{1}{B}\sum_b \left(\log \sum_i e^{z_{b,i}}\right)^2$$

惩罚 logits 的 logsumexp 太大，让数值稳定。

**追问：为什么 MoE 训练对随机种子敏感？** 路由是离散选择（Top-K），初期路由模式被早期数据塑造；不同种子可能让"哪个专家学什么"完全不同，但最终效果差异通常不大（专家"等价类"自由度）。

---

## Q9: MoE 推理为什么"显存吃紧但速度快"？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

**速度快**：
- 每 token 只激活 $K$ 个专家
- FLOP = 激活参数对应的计算量（远小于总参数）
- DeepSeek-V3 推理 FLOP 接近 37B Dense 模型，但能力远超

**显存吃紧**：
- 必须把**所有专家**装进显存（不知道下一个 token 路由到哪）
- DeepSeek-V3 671B 全 BF16 ≈ 1.3 TB → 至少 16-32 张 80GB GPU
- 单机推理对绝大多数用户不可行

**部署优化**：
- **Expert Caching**：热门专家放 HBM，冷门 offload 到 CPU/SSD
- **EP 推理**：多卡分担专家
- **vLLM / SGLang** 都支持 MoE 推理
- **Speculative + MoE**：投机解码进一步加速

**追问：MoE 推理 batch 大时是不是更划算？** 是的——batch 大时不同 token 路由到不同专家的概率更均匀，每个专家都"忙起来"；batch 小时大量专家闲置，路由开销占比反而高。**MoE 适合云端大流量场景**。

---

## Q10: 能把 Dense 模型"转"成 MoE 吗？Upcycling 是什么？
> 难度 ⭐⭐⭐ ｜ 高频 🔥

**Upcycling**：从一个训好的 Dense 模型构造 MoE 初始化。

**做法**：
1. 取 Dense 的 FFN，**复制 $N$ 份**作为 MoE 的 $N$ 个专家
2. 路由器随机初始化
3. 其余参数（Attention 等）直接复用
4. 继续训练（让专家分化）

**优势**：
- 不从零训，省 50%+ 算力
- 初始效果接近原 Dense
- 后续 finetune 让专家分化

**典型应用**：
- Mixtral 8×7B 据传从 Mistral 7B upcycle
- 国内多数 MoE 开源都用类似流程

**坑**：
- 初始所有专家相同，路由器随机选无差异 → 需较长时间分化
- 加 Aux Loss 强制均衡，否则可能塌缩回 Dense

**追问：Upcycling 后专家最终会"分化"到不同领域吗？** 部分会（如某专家偏数学/代码），但很多分化是"风格"或"语法"层面，不一定可解释。研究分析显示专家分工是"软"的，且不同层差异大。

---

## 🎯 自测清单

- [ ] 能默写 MoE 的 Top-K 路由公式 + 解释每项
- [ ] 能讲清 Aux Loss vs Aux-loss-free 两种均衡的差异
- [ ] 能算 Expert Capacity 公式并解释 capacity_factor 作用
- [ ] 能说清 DeepSeek-MoE 的"细粒度 + 共享专家"为什么有效
- [ ] 能讲 All-to-All 为什么是 EP 瓶颈，DeepEP 在优化什么
