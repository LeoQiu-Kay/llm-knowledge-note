# KV Cache 压缩

> 量化、淘汰、共享是三大思路，长上下文必考。

---

## 1. KV Cache 量化

### 1.1 量化粒度（从粗到细）

| 粒度 | 含义 |
|---|---|
| **Per-tensor** | 整个 tensor 一个 scale |
| **Per-channel** | 每个特征通道一个 scale |
| **Per-token** | 每个 token 一个 scale（KV Cache 常用） |
| **Per-block** | 分块量化（如每 128 元素一组） |

### 1.2 典型量化方案

**对称量化公式**：

$$x_{\text{quant}} = \text{round}\left(\frac{x}{s}\right), \quad x_{\text{dequant}} = x_{\text{quant}} \cdot s$$

**符号说明**：
- $x$：原始值
- $s$：scale（缩放因子）
- $x_{\text{quant}}$：量化后的整数值
- $\text{round}$：取整

**非对称量化**：增加 zero-point $z$：

$$x_{\text{quant}} = \text{round}\left(\frac{x}{s}\right) + z$$

**LLM 常用**：
- **INT8 per-token**：精度损失小，2× 显存节省
- **INT4 group quantization**：约 4× 节省
- **FP8** (E4M3 / E5M2)：H100 原生支持

---

## 2. KV Cache 量化的关键挑战

1. **outlier**：K 矩阵某些 channel 数值特别大 → 均匀量化损失大
2. **K 和 V 敏感度不同**：K 更敏感（影响 softmax，误差被放大），V 较鲁棒
3. **每层敏感度不同**：浅层 / 深层量化误差累积差异大

**解决方案**：
- **混合精度**：敏感层用 FP8/FP16，其余 INT4
- **K 用 INT8，V 用 INT4**（敏感度匹配）
- **Outlier 处理**：SmoothQuant 思路把 outlier 转移到权重

---

## 3. H2O：基于注意力分数的淘汰

**核心观察**：注意力是稀疏的——少数"重要" token 接收大部分注意力。

**算法**：
1. 维护固定大小的 KV Cache 窗口（如 256）
2. 每次新 token 后，按**累积 attention score** 淘汰最不重要的 token
3. 保留高分 token + 最近 token

**效果**：把 KV Cache 缩到原始 20%，长上下文性能损失小。

---

## 4. StreamingLLM（Attention Sink）

**核心发现**：LLM 的注意力需要"看到"序列开头的几个 token（**attention sink**）。

```text
即使开头 token 语义不重要，模型也"依赖"它们。
一旦淘汰首部 token，注意力分布崩溃，效果暴跌。
```

**StreamingLLM 方案**：保留**前 4 个 token + 滑动窗口**。

**为什么有 sink**：
- Softmax 必须把权重分配到某处
- 当 query 与所有 token 都不相关时，模型"垃圾桶"地把权重分给开头
- 训练时 BOS 等位置反复出现，模型学到"开头 token 是安全的"

**实际应用**：长对话、流式语音、永远在线的助手。

---

## 5. SnapKV / PyramidKV

**SnapKV**（清华 2024）：
- prefill 结束后用最后几个 token 的 attention 选出"重要" token
- 静态压缩（不像 H2O 是流式）
- 长文档 QA 场景效果好

**PyramidKV**：
- 不同层用不同 budget：底层多（细节），高层少（已抽象）
- 类似金字塔

**思路对比**：

| 方法 | 触发 | 选择依据 | 适用 |
|---|---|---|---|
| H2O | 流式、每步 | 累积 attention | 长生成 |
| StreamingLLM | 流式 | 位置（首部 + 近期） | 无限流 |
| SnapKV | 一次、prefill 后 | 最近 query 的 attention | 长上下文 QA |
| PyramidKV | 一次、分层 | 层级 budget | 长上下文通用 |

---

## 6. 量化 vs 淘汰，怎么选？

| 维度 | 量化 | 淘汰 |
|---|---|---|
| 节省方式 | 每个元素更小 | 元素总数变少 |
| 精度损失 | 全局均匀 | 局部信息丢失 |
| 适用任务 | 通用 | 长上下文（冗余多） |
| 实现复杂度 | 中 | 低 |
| 框架支持 | 广泛 | 有限 |

```text
可组合：先淘汰冗余 token，再量化剩余 KV。
```

---

## 7. 架构层共享 vs 后处理压缩

**架构层（MQA / GQA / MLA）**：
- 训练时就决定 KV 数量
- 训练 / 推理一致
- 整体设计、最优

**后处理（量化 / 淘汰）**：
- 训练完成后施加
- 即插即用
- 效果损失更明显

**实际**：先用 GQA 或 MLA 训练，再用量化进一步压缩，组合最佳。

---

## 8. Prefix Caching：跨请求复用

**目的**：跨请求复用相同前缀的 KV Cache。

**典型场景**：
- 多用户共享同一 system prompt
- RAG 中重复检索模板
- Few-shot 示例反复使用
- 多轮对话历史

**实现**：
- **vLLM**：Automatic Prefix Caching，基于 hash 匹配
- **SGLang**：RadixAttention（radix tree，更细粒度）
- **Anthropic API**：显式标注 cacheable section

**效果**：
- TTFT 大幅降低（命中前缀直接跳过 prefill）
- 成本降低（按缓存命中折扣计费）

---

## 9. KV Cache offload

**思路**：把不活跃的 KV Cache 卸载到 CPU 内存或 NVMe SSD，需要时再调回。

**典型场景**：
- 服务多并发，单卡显存放不下所有 KV
- 长会话历史，远端历史不常用

**挑战**：
- PCIe 带宽远低于 HBM
- offload/reload 延迟可能比 prefill 还慢
- 适合"低频访问"的 KV

**框架**：FlexGen（早期工作）；部分场景被 Prefix Caching 替代。

---

## 10. 最简记忆

```text
三大压缩思路：

量化：
  INT8/INT4/FP8，per-token 最常用
  K 比 V 敏感、注意 outlier

淘汰：
  H2O    流式按 attention 分数
  StreamingLLM 保首部 + 滑窗
  SnapKV  prefill 后选关键 token
  PyramidKV 不同层不同 budget

共享：
  架构层 MQA / GQA / MLA
  跨请求 Prefix Caching / RadixAttention

组合使用：架构 + 量化 + 淘汰 + 复用。
```

---

## 🎯 高频追问

1. **K 和 V 哪个对量化更敏感**？K 更敏感（影响 softmax 进而被指数放大）。

2. **StreamingLLM 的 sink 数量怎么选**？通常 4 个就够，加更多边际收益小。

3. **H2O 的窗口大小怎么定**？根据任务和效果折中，64-512 常见。

4. **能完全不缓存 V 吗**？理论可重算，但 attention 需要 V，每步重算成本不低。

5. **长上下文（128K+）怎么办**？组合 GQA/MLA + 量化 + 淘汰 + offload，缺一不可。
