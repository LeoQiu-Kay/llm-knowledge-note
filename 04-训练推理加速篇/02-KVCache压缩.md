# KV Cache 压缩

> 量化、淘汰、共享是三大思路，长上下文场景必考。

---

## Q1: KV Cache 量化的几种粒度？

**答**：
**量化粒度**（精度从高到低）：
- **Per-tensor**：整个 tensor 一个 scale
- **Per-channel**：每个特征通道一个 scale
- **Per-token**：每个 token 一个 scale（KV Cache 中常用）
- **Per-block / Per-group**：分块量化（如每 128 个元素一组）

**典型方案**：
- **INT8 per-token**：精度损失小，2× 显存节省
- **INT4 group quantization**：约 4× 节省，效果略降
- **FP8 (E4M3 / E5M2)**：H100 原生支持

**框架支持**：
- vLLM：FP8 / INT8 KV Cache
- TRT-LLM：INT8 / FP8
- llama.cpp：Q4_0 / Q4_K KV Cache

---

## Q2: KV Cache 量化的关键挑战？

**答**：
**问题**：
1. **outlier**：K 矩阵某些 channel 数值特别大（attention sink 相关），均匀量化会损失这些信息
2. **K 和 V 敏感度不同**：K 更敏感（影响 softmax，误差被放大），V 较鲁棒
3. **每层敏感度不同**：浅层 / 深层量化误差累积差异大

**解决方案**：
- **混合精度**：敏感层用 FP8/FP16，其余 INT4
- **K 用 INT8，V 用 INT4**（敏感度匹配）
- **Outlier 处理**：SmoothQuant 思路，把 outlier 转移到权重

---

## Q3: H2O（Heavy-Hitter Oracle）？

**答**：
**核心观察**：注意力是稀疏的——少数"重要" token 接收大部分注意力。

**算法**：
1. 维护一个固定大小的 KV Cache 窗口（如 256）
2. 每次新 token 后，按累积 attention score 淘汰最不重要的 token
3. 保留高分 token + 最近 token

**效果**：
- 把 KV Cache 缩到原始 20%
- 长上下文任务性能损失小

**类似工作**：
- Scissorhands
- TOVA

---

## Q4: StreamingLLM（Attention Sink）是什么？

**答**：
**核心发现**：
- LLM 的注意力机制需要"看到"序列开头的几个 token（"attention sink"）
- 即使这些 token 语义不重要，模型也"依赖"它们
- 一旦淘汰首部 token，注意力分布崩溃，效果暴跌

**StreamingLLM 方案**：
- 保留前 4 个 token + 最近的滑动窗口
- 实现"流式"无限长度推理（实际是有限 KV Cache）

**为什么有 sink**：
- softmax 必须把权重分配到某处
- 当 query 与所有 token 都不相关时，模型"垃圾桶"地把权重分给开头
- 训练时 BOS 等位置反复出现，模型学到"开头 token 是安全的"

**实际应用**：长对话、流式语音、永远在线的助手。

---

## Q5: SnapKV / PyramidKV？

**答**：
**SnapKV**（清华, 2024）：
- 在 prefill 结束后，用最后几个 token 的 attention 选出"重要" token，丢弃其他
- 静态压缩（不像 H2O 是流式）
- 长文档 QA 场景效果好

**PyramidKV**：
- 不同层用不同 budget：底层 KV 多（细节），高层 KV 少（已抽象）
- 类似金字塔结构

**思路对比**：

| 方法 | 触发时机 | 选择依据 | 适用场景 |
|------|---------|---------|---------|
| H2O | 流式，每步 | 累积 attention | 长生成 |
| StreamingLLM | 流式 | 位置（首部+近期） | 无限流 |
| SnapKV | 一次性，prefill 后 | 最近 query 的 attention | 长上下文 QA |
| PyramidKV | 一次性，分层 | 层级 budget | 长上下文通用 |

---

## Q6: KV Cache 量化 vs 淘汰，怎么选？

**答**：

| 维度 | 量化 | 淘汰 |
|------|------|------|
| 节省方式 | 每个元素更小 | 元素总数变少 |
| 精度损失 | 全局均匀损失 | 局部信息丢失 |
| 适用任务 | 通用 | 长上下文（信息冗余多） |
| 实现复杂度 | 中（量化算子） | 低（直接删元素） |
| 框架支持 | 广泛 | 有限 |

**可组合**：先淘汰冗余 token，再量化剩余 KV。

---

## Q7: 架构层共享（MQA/GQA/MLA）vs 后处理压缩？

**答**：

**架构层（MQA/GQA/MLA）**：
- 训练时就决定 KV 数量
- 训练 / 推理一致
- 模型整体设计，最优

**后处理（量化/淘汰）**：
- 训练完成后施加
- 即插即用
- 效果损失更明显

**实际**：先用 GQA 或 MLA 训练，再用量化进一步压缩，组合效果最佳。

---

## Q8: Prefix Caching 是什么？

**答**：
**目的**：跨请求复用相同前缀的 KV Cache。

**典型场景**：
- 多用户共享同一 system prompt
- RAG 中重复的检索模板
- Few-shot 示例反复使用
- 同一会话的多轮对话

**实现**：
- **vLLM**：自动 Prefix Caching，基于 hash 匹配
- **SGLang**：RadixAttention，用 radix tree 管理共享前缀
- **Anthropic API**：显式标注可缓存段

**效果**：
- TTFT 大幅降低（命中前缀直接跳 prefill）
- 成本降低（按缓存命中折扣计费）

---

## Q9: KV Cache offload（卸载到 CPU/NVMe）？

**答**：
**思路**：把不活跃的 KV Cache 卸载到 CPU 内存或 NVMe 磁盘，需要时再调回。

**典型场景**：
- 服务多并发，单卡显存放不下所有 KV
- 长会话历史，远端历史不常用

**挑战**：
- PCIe 带宽远低于 HBM
- offload/reload 延迟可能比 prefill 还慢
- 适合"低频访问"的 KV

**框架**：
- FlexGen（早期工作）
- 部分场景被 prefix caching 替代

---

## Q10: 多卡 / 分布式下的 KV Cache？

**答**：
**Tensor Parallel（TP）下**：
- KV Cache 按头切分：每张卡只持有自己负责的头的 KV
- attention 计算后通过 AllReduce 合并
- KV Cache 总量不变，但分布到多卡

**Pipeline Parallel（PP）下**：
- 每张卡持有自己负责的层的 KV
- 不同层 KV 在不同卡上

**专家并行（EP，MoE）**：
- 与 KV Cache 无关（KV 不参与专家路由）

---

## 🎯 高频追问

1. **量化对 K 和 V 哪个更敏感**？K 更敏感（影响 softmax）。
2. **StreamingLLM 的 sink 数量怎么选**？通常 4 个就够，加更多边际收益小。
3. **H2O 的窗口大小怎么定**？根据任务和效果折中，64-512 常见。
4. **能不能完全不缓存 V**？理论可重计算，但 attention 需要 V，每步重算成本不低。
5. **长上下文（128K+）的 KV Cache 怎么办**？组合 GQA/MLA + 量化 + 淘汰 + offload，缺一不可。
