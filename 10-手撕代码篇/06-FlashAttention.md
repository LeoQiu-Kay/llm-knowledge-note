# 手撕 FlashAttention（简化版）

> 最难的手撕题。面试一般只要求写出 **online softmax** + **分块** 的核心逻辑，不要求 CUDA。

---

## 1. 题目要求

用"分块 + online softmax"实现 attention，**不实例化完整 $n \times n$ 矩阵**，证明结果与朴素 attention 一致。

---

## 2. 核心思想

朴素 attention 要存完整 $S = QK^T$（$O(n^2)$ 显存）。FlashAttention 把 K/V 分块，**流式**地累加每块的贡献，用 **online softmax** 维护 running max 和 running sum。

**Online softmax 的关键递推**（合并两块的统计量）：

设已处理块的 max = $m$、归一化和 = $\ell$、累积输出 = $O$，新块 max = $m_{\text{new}}$：

$$m' = \max(m, m_{\text{new}})$$
$$\ell' = e^{m - m'} \ell + e^{m_{\text{new}} - m'} \ell_{\text{block}}$$
$$O' = e^{m - m'} O + e^{m_{\text{new}} - m'} O_{\text{block}}$$

---

## 3. 完整实现

```python
import torch
import torch.nn.functional as F
import math


def flash_attention(Q, K, V, block_size=2):
    """
    简化版 FlashAttention（教学用，纯 PyTorch 演示 online softmax）。
    Q, K, V: [B, H, L, d]
    不实例化完整 [L, L] 注意力矩阵。
    """
    B, H, L, d = Q.shape
    scale = 1.0 / math.sqrt(d)

    O = torch.zeros_like(Q)                       # 输出累积
    # 每个 query 位置维护 running max(l_i) 和 running sum(L_i)
    row_max = torch.full((B, H, L, 1), float('-inf'))
    row_sum = torch.zeros(B, H, L, 1)

    # 外层循环：K/V 分块（FlashAttention 的 K/V 在外层）
    for j in range(0, L, block_size):
        Kj = K[:, :, j:j + block_size]            # [B, H, bk, d]
        Vj = V[:, :, j:j + block_size]

        # 当前块的分数 [B, H, L, bk]
        Sij = (Q @ Kj.transpose(-2, -1)) * scale

        # 块内行最大值
        block_max = Sij.max(dim=-1, keepdim=True).values  # [B, H, L, 1]
        new_max = torch.maximum(row_max, block_max)

        # 重新缩放旧的累积量
        exp_old = torch.exp(row_max - new_max)            # 旧贡献的缩放系数
        exp_block = torch.exp(Sij - new_max)              # 当前块 [B,H,L,bk]

        # 更新 running sum
        row_sum = exp_old * row_sum + exp_block.sum(dim=-1, keepdim=True)
        # 更新输出累积
        O = exp_old * O + exp_block @ Vj

        row_max = new_max

    # 最后归一化
    O = O / row_sum
    return O


def naive_attention(Q, K, V):
    """朴素 attention，用来对拍"""
    d = Q.shape[-1]
    S = (Q @ K.transpose(-2, -1)) / math.sqrt(d)
    A = F.softmax(S, dim=-1)
    return A @ V
```

---

## 4. 测试验证

```python
torch.manual_seed(0)
B, H, L, d = 2, 4, 8, 16
Q = torch.randn(B, H, L, d)
K = torch.randn(B, H, L, d)
V = torch.randn(B, H, L, d)

out_flash = flash_attention(Q, K, V, block_size=3)
out_naive = naive_attention(Q, K, V)

err = (out_flash - out_naive).abs().max().item()
print("FlashAttention vs 朴素 最大误差:", err)
assert err < 1e-5, "结果应该数值等价"
print("✓ 通过：online softmax 分块计算与朴素 attention 完全一致")
```

---

## 5. 面试常见追问

**Q: FlashAttention 到底优化了什么？**
A: **IO（显存读写）**，不是 FLOP。朴素 attention 要把 $n \times n$ 矩阵写到 HBM 再读回；FlashAttention 分块后数据留在 SRAM，HBM IO 从 $O(n^2)$ 降到 $O(n)$。计算量不变。

**Q: online softmax 为什么能保证结果正确？**
A: softmax 有"减最大值"的平移不变性。维护 running max 后，每次新块来都重新缩放旧的累积量（乘 $e^{m-m'}$），数学上严格等价于一次性算全局 softmax。

**Q: 这个 PyTorch 版是真的 FlashAttention 吗？**
A: 不是——真正的 FlashAttention 是 CUDA kernel，把分块计算 fuse 在 SRAM 里完成。这里只是用 PyTorch **演示 online softmax 的逻辑**，本身不省显存（PyTorch 会实例化中间量）。

**Q: 反向传播怎么办？**
A: 真正的 FlashAttention 反向时**重计算**注意力矩阵（不存中间结果），用约 30% 额外计算换显存。

**Q: block_size 怎么选？**
A: 受 SRAM 大小限制，让 Q/K/V 块刚好放进 SRAM。真实实现里和 GPU 架构强相关。

> 📚 原理详解：[04-训练推理加速篇/03-高效注意力算法.md](../04-训练推理加速篇/03-高效注意力算法.md)
