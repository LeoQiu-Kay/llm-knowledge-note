# KV Cache 压缩 · 面试题

> 对应原理文档：[02-KVCache压缩.md](../02-KVCache压缩.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: KV Cache 压缩有哪三大思路？怎么组合？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

| 思路 | 节省方式 | 代表方法 |
|---|---|---|
| **量化** | 每个元素更小 | INT8 / INT4 / FP8 per-token |
| **淘汰（eviction）** | 元素总数变少 | H2O、StreamingLLM、SnapKV、PyramidKV |
| **共享** | 多份合一份 | 架构层 MQA/GQA/MLA、跨请求 Prefix Caching |

**组合范式**：架构层（GQA/MLA 训练时定）+ 量化（如 INT8 KV）+ 淘汰（如 H2O / SnapKV）+ 复用（Prefix Caching）。四类正交叠加。

---

## Q2: KV Cache 量化的粒度有哪些？为什么常用 per-token？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

| 粒度 | 含义 | 显存开销（scale） | 误差 |
|---|---|---|---|
| Per-tensor | 整个 tensor 一个 scale | 极小 | 大 |
| Per-channel | 每个特征通道一个 scale | 小 | 中 |
| **Per-token** | 每个 token 一个 scale | 中 | 小（KV 常用） |
| Per-block | 每 K 个元素一组（如 128） | 较大 | 最小 |

**KV 用 per-token 的理由**：
- KV Cache 是按 token 增长的，per-token scale 自然贴合数据布局
- 不同 token 的激活幅度差异大（如 sink token 大，普通 token 小），每 token 单独 scale 显著降低误差
- 量化/反量化时元数据局部化，不影响其他 token

**追问：per-channel 为什么不适合 KV？** KV Cache 跨多个 token 共享 channel-wise scale 时，scale 是动态的（每多一个 token 都可能改），更新困难。

---

## Q3: K 和 V 哪个对量化更敏感？为什么？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**K 更敏感**。

**理由**：K 参与 $\text{softmax}(QK^T/\sqrt{d_h})$，量化误差被 softmax **指数放大**——一个 logit 误差 $\Delta$ 经过 $e^\Delta$ 后变化巨大；V 只参与 $P \cdot V$ 的线性加权，误差线性传播。

**工程对策**：
- **K 用 INT8，V 用 INT4**（敏感度匹配）
- 或浅层用 FP8/FP16，深层用 INT4（误差累积差异）

**追问：另一个 K 的痛点？** Outlier——K 矩阵某些 channel 数值特别大，均匀量化时 step size 被它们拉爆，小值损失严重。SmoothQuant 的思路就是把 outlier 转移到权重。

---

## Q4: H2O 是什么？淘汰依据是什么？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**H2O**（Heavy-Hitter Oracle）：基于**累积 attention 分数**的动态淘汰。

**核心观察**：注意力是稀疏的——少数"重要" token 接收大部分注意力。

**算法**：
1. 维护固定大小的 KV Cache 窗口（如 256）
2. 每生成新 token 后，累计每个历史 token 收到的 attention 分数
3. 当窗口超限时，淘汰累计分数最低的 token
4. 同时保留最近 N 个 token（"recency"）

**效果**：KV Cache 缩到 20%，长上下文性能损失小。

**追问：H2O 的窗口怎么定？** 任务相关，常见 64-512。生成越长、上下文越复杂，窗口要更大。

---

## Q5: StreamingLLM 的 attention sink 是什么？为什么不能淘汰首部 token？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**关键现象**：LLM 的 attention 严重依赖序列**开头几个 token**（即使语义不重要）。一旦淘汰首部，attention 分布崩溃，生成质量暴跌。

**为什么会有 sink**：
- Softmax 必须把权重总和分配到某处
- 当 query 与所有 token 都不相关时，模型"垃圾桶式"把权重倾倒给开头
- 训练时 BOS 等位置反复出现，模型学到"开头 token 是安全的"

**StreamingLLM 方案**：保留**前 4 个 token（sink）+ 最近 N 个 token（滑动窗口）**，中间全淘汰。可支持无限流（流式语音、永久在线助手）。

**追问：sink 数量怎么选？** 通常 4 个就够，更多边际收益小。

---

## Q6: 对比 H2O / StreamingLLM / SnapKV / PyramidKV 四种淘汰策略
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

| 方法 | 触发时机 | 选择依据 | 适用场景 |
|---|---|---|---|
| **H2O** | 流式、每步 | 累积 attention | 长生成 |
| **StreamingLLM** | 流式 | 位置（首部 sink + 最近 N） | 无限流、长对话 |
| **SnapKV** | 一次、prefill 后 | 最近 query 的 attention | 长上下文 QA |
| **PyramidKV** | 一次、按层分 | 层级 budget（底层多、高层少） | 长上下文通用 |

**SnapKV 直觉**：prefill 结束时，用最后几个 token 的 attention 模式选出"将被未来高频访问"的 token，做一次性裁剪。
**PyramidKV 直觉**：浅层处理细节、深层处理抽象，所以浅层多留 token、深层少留。

---

## Q7: 量化 vs 淘汰，怎么选？能不能组合？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

| 维度 | 量化 | 淘汰 |
|---|---|---|
| 节省方式 | 每个元素更小（INT4 是 FP16 的 1/4） | 元素总数变少 |
| 精度损失 | 全局均匀 | 局部信息丢失（被淘汰的 token） |
| 适用任务 | 通用 | 长上下文（冗余 token 多） |
| 实现复杂度 | 中（量化 kernel、scale 管理） | 低（标记 + 跳读） |
| 框架支持 | 广泛 | 有限 |

**组合**：完全可以——先淘汰冗余 token 再量化剩余 KV，节省效果叠加。

---

## Q8: 架构层共享（GQA/MLA）和后处理压缩（量化/淘汰）的区别？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

| | 架构层共享 | 后处理压缩 |
|---|---|---|
| 决定时机 | **训练前** | **训练后** |
| 训练/推理一致性 | 一致 | 不一致（需校准） |
| 效果损失 | 小（联合训练） | 较明显 |
| 灵活性 | 改架构需重训 | 即插即用 |
| 代表 | MQA / GQA / MLA | INT8/INT4 KV、H2O |

**实践**：先用 GQA / MLA 训练，再叠加量化和淘汰——架构层是"地基"，后处理是"装修"。

**MLA**：Multi-head Latent Attention，把 K/V 压到 $d_c$ 维潜空间（DeepSeek 典型 $d_c=512$），比 GQA 进一步减小。

---

## Q9: KV Cache offload 是什么？什么场景下值得？
> 难度 ⭐⭐ ｜ 高频 🔥

**思路**：把不活跃的 KV Cache 卸载到 CPU 内存或 NVMe SSD，需要时再调回 GPU。

**典型场景**：
- 单卡显存放不下所有并发的 KV
- 长会话历史中"很久没用"的部分

**挑战**：
- PCIe 带宽（~32 GB/s）远低于 HBM（~3 TB/s）
- offload/reload 的延迟可能比 prefill 还慢
- 只适合"低频访问"的 KV

**实践**：FlexGen 是早期代表；现在很多场景被 Prefix Caching 替代（缓存可被多请求复用，比 offload 性价比高）。

---

## Q10: 长上下文（128K+）下 KV Cache 怎么管？
> 难度 ⭐⭐⭐⭐ ｜ 高频 🔥🔥

单条策略不够，必须组合拳：

1. **架构层**：GQA / MLA 把 $h$ 或 $d_c$ 压小（必选）
2. **量化**：INT8 或 INT4 KV，2-4× 节省
3. **淘汰**：H2O / SnapKV，长上下文中 token 冗余大，淘汰收益明显
4. **PagedAttention**：管理碎片
5. **Prefix Caching**：跨请求复用前缀
6. **Offload**：极端长度或低 QPS 场景

**算账**：LLaMA-3-70B 128K：原始 ~42 GB → GQA 已计入 → INT4 量化 ~10 GB → H2O 淘汰 50% → ~5 GB，可行。

---

## 🎯 自测清单

- [ ] 能说清量化 / 淘汰 / 共享三大思路的区别
- [ ] 能解释 K 比 V 对量化更敏感的原因（softmax 指数放大）
- [ ] 能讲清 attention sink 现象 + StreamingLLM 方案
- [ ] 能对比 H2O / StreamingLLM / SnapKV / PyramidKV
- [ ] 能说出长上下文组合压缩的完整链路
