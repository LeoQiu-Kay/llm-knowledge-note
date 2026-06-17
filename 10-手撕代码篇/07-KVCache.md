# 手撕 KV Cache

> 高频题。重点：自回归生成时**只算新 token 的 Q/K/V**，历史 K/V 缓存复用。

---

## 1. 题目要求

实现带 KV Cache 的增量解码：
- prefill 阶段：处理完整 prompt
- decode 阶段：每次只输入 1 个新 token，复用缓存的历史 K/V

---

## 2. 核心思想

**没有 KV Cache**：每生成一个 token，要对 `[prompt + 已生成]` 全部重算 attention → $O(t^2)$。

**有 KV Cache**：
- 历史 token 的 K/V **不会变**（输入不变、权重不变）
- 缓存它们，每步只算**新 token** 的 Q/K/V，新 K/V 追加到缓存
- 每步复杂度降到 $O(t)$

---

## 3. 完整实现

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class AttentionWithKVCache(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)

    def forward(self, x, kv_cache=None):
        """
        x: [B, L_new, D]
           - prefill: L_new = prompt 长度
           - decode:  L_new = 1（只输入新 token）
        kv_cache: dict {'k': [B,H,L_past,d], 'v': [...]} 或 None
        返回 out, new_kv_cache
        """
        B, L_new, D = x.shape

        # 只对新输入算 Q/K/V
        q = self.W_q(x).view(B, L_new, self.n_heads, self.d_k).transpose(1, 2)
        k = self.W_k(x).view(B, L_new, self.n_heads, self.d_k).transpose(1, 2)
        v = self.W_v(x).view(B, L_new, self.n_heads, self.d_k).transpose(1, 2)
        # q,k,v: [B, H, L_new, d_k]

        # 拼接历史 K/V
        if kv_cache is not None:
            k = torch.cat([kv_cache['k'], k], dim=2)   # [B,H,L_past+L_new,d_k]
            v = torch.cat([kv_cache['v'], v], dim=2)

        new_cache = {'k': k, 'v': v}

        # attention：新 Q 对全部（历史+新）K/V
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.d_k)
        # [B, H, L_new, L_total]

        # decode 阶段 L_new=1，新 token 能看到全部历史，无需 causal mask
        # prefill 阶段需要 causal mask
        if L_new > 1:
            L_total = k.shape[2]
            causal = torch.tril(torch.ones(L_new, L_total, device=x.device),
                                diagonal=L_total - L_new)
            scores = scores.masked_fill(causal == 0, float('-inf'))

        attn = F.softmax(scores, dim=-1)
        out = attn @ v                                  # [B,H,L_new,d_k]
        out = out.transpose(1, 2).contiguous().view(B, L_new, D)
        return self.W_o(out), new_cache


@torch.no_grad()
def generate(model, prompt_emb, n_steps, embed_next):
    """
    演示自回归生成流程。
    prompt_emb: [B, L_prompt, D]
    embed_next: 函数，把上一步输出映射成下一个 token embedding [B, 1, D]
    """
    # 1. Prefill：一次性处理完整 prompt，建立 KV Cache
    out, cache = model(prompt_emb)
    last = out[:, -1:]                                  # [B, 1, D]

    outputs = [last]
    # 2. Decode：每次只输入 1 个新 token
    for _ in range(n_steps):
        next_in = embed_next(last)                      # [B, 1, D]
        out, cache = model(next_in, kv_cache=cache)     # 复用缓存！
        last = out
        outputs.append(last)
    return torch.cat(outputs, dim=1)
```

---

## 4. 测试验证

```python
torch.manual_seed(0)
B, L, D, H = 1, 4, 64, 8
model = AttentionWithKVCache(D, H).eval()
x = torch.randn(B, L, D)

# 关键正确性验证：带 cache 的增量计算 == 不带 cache 的整段计算
with torch.no_grad():
    # 方式 A：一次性处理全部（prefill）
    full_out, _ = model(x)

    # 方式 B：先 prefill 前 2 个，再逐个 decode 后 2 个
    out1, cache = model(x[:, :2])           # prefill 前 2 个
    out2, cache = model(x[:, 2:3], cache)   # decode 第 3 个
    out3, cache = model(x[:, 3:4], cache)   # decode 第 4 个
    incremental = torch.cat([out1, out2, out3], dim=1)

err = (full_out - incremental).abs().max().item()
print("整段 vs 增量(KV Cache) 最大误差:", err)
assert err < 1e-5, "KV Cache 增量解码应与整段计算一致"
print("✓ 通过")

# 显存增长演示
print("\nKV Cache 大小随生成增长：")
_, cache = model(x[:, :2])
print("  prefill 后:", cache['k'].shape)      # [1,8,2,8]
_, cache = model(x[:, 2:3], cache)
print("  decode 1 步:", cache['k'].shape)     # [1,8,3,8]
```

---

## 5. 面试常见追问

**Q: KV Cache 为什么能省计算？**
A: 历史 token 的 K/V 在生成中不变。缓存后每步只算新 token 的 Q/K/V，复杂度从每步 $O(t^2)$ 降到 $O(t)$。

**Q: 为什么只缓存 K/V 不缓存 Q？**
A: Q 只在"当前步"用一次（算当前 token 对历史的注意力）。下一步的 Q 是新 token 的，旧 Q 没用了。K/V 则要被未来所有 token 反复查询，所以缓存。

**Q: KV Cache 显存怎么算？**
A: $2 \times L \times s \times h \times d_h \times \text{bytes}$（2 是 K+V）。长序列时这是显存大头。

**Q: decode 阶段为什么不需要 causal mask？**
A: decode 时 L_new=1，这个新 token 本来就该看到所有历史，没有"看到未来"的问题。prefill 阶段才需要 causal mask。

**Q: 怎么降低 KV Cache？**
A: 架构层 MQA/GQA/MLA（减 KV 头数）、量化（INT8/INT4）、淘汰（H2O/StreamingLLM）、PagedAttention（减碎片）。

> 📚 原理详解：[04-训练推理加速篇/01-KVCache.md](../04-训练推理加速篇/01-KVCache.md)
