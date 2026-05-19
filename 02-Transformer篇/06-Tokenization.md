# Tokenization（分词）

> Tokenizer 是 LLM 的入口。BPE / WordPiece / SentencePiece 必知。

---

## 1. 为什么不直接用字符或词？

**字符级**：
- 优点：词表小（ASCII 几十个）
- 缺点：序列太长（"hello" → 5 个 token）；模型需自己学组词

**词级**：
- 优点：语义直观
- 缺点：词表巨大（百万级）；OOV（Out-Of-Vocabulary）严重；新词无法表示

**Subword 级（BPE/WordPiece/Unigram）**：折中
- 词表中等（30K-150K）
- 高频词作整词，低频词拆子词
- 几乎无 OOV
- **LLM 时代主流**

---

## 2. BPE（Byte Pair Encoding）

**起源**：原本是压缩算法（Sennrich et al., 2016 引入到 NMT）。

**算法**：
1. 初始化：词表 = 所有字符
2. 在训练语料上统计相邻字符对的**频率**
3. 选频率最高的对（如 `("l", "o")`），合并成新 token（`"lo"`）加入词表
4. 在所有出现该对的位置替换为新 token
5. 重复直到词表达到目标大小

**示例**：

```
初始: l o w </w>  l o w </w>  n e w e s t </w>  w i d e s t </w>
合并 (l, o):    lo w </w>  lo w </w>  n e w e s t </w>  w i d e s t </w>
合并 (lo, w):   low </w>  low </w>  ...
合并 (e, s):    low </w>  low </w>  n e w es t </w>  w i d es t </w>
...
```

**Byte-level BPE**（GPT-2 / LLaMA-3）：
- 最底层是 256 个**字节**，覆盖任意 Unicode
- 真正 0 OOV（任何字符都能拆到字节）

---

## 3. WordPiece 与 BPE 的区别

**核心算法相似**：迭代合并最频繁的对。

**关键差异**：判据不同。

| | 判据 |
|---|---|
| BPE | 频率最高的对 |
| WordPiece | **似然增益**最大的对：$\arg\max \frac{P(AB)}{P(A) P(B)}$（点互信息） |

**符号说明**：
- $A, B$：候选合并的两个 token
- $P(\cdot)$：在训练语料中出现的概率
- $P(AB)$：连续出现 $AB$ 的概率
- $P(A) P(B)$：独立出现的乘积

**代表**：BERT、DistilBERT 用 WordPiece。

**实际差异不大**：两者效果接近，主要看实现细节。

---

## 4. SentencePiece

**Google 的库**，支持多种算法（BPE、Unigram），核心特点：

1. **不依赖空格分词**：空格视为普通字符（用 `▁` 表示），适合中文、日文等无空格语言
2. **可逆**：原文 → tokens → 原文 不丢失信息
3. **支持 Unigram LM 算法**

**Unigram LM 算法**（与 BPE 相反方向）：
1. 初始化**大词表**
2. 用 EM 算法估计每个 subword 的概率
3. 迭代**删掉**对似然贡献最小的 subword
4. 直到词表达到目标大小

**代表**：T5、ALBERT、LLaMA、Qwen 都用 SentencePiece。

---

## 5. Tiktoken（OpenAI 用）

- OpenAI 的高速 BPE 实现（Rust 写、Python 绑定）
- 用于 GPT-3.5/4 系列
- 比 HuggingFace tokenizers 快约 3-6 倍
- 支持多种编码：`cl100k_base`（GPT-4）、`o200k_base`（GPT-4o）

---

## 6. 中文分词的特殊问题

**核心问题**：中文无空格分隔。

**LLM 时代解法**：
- 用 SentencePiece 等 byte-level 或 char-level subword
- 中文常以单字或双字为基本 token
- 词表中加入大量常用中文字符（LLaMA-3 扩到 128K 后中文友好）

**经济性问题**：
- 同一段文本，中文 token 数往往比英文多
- LLaMA-2（词表 32K，偏英文）：一个汉字常拆成 3-4 个 byte token
- LLaMA-3（128K）/ Qwen（152K）：大幅改善

---

## 7. 词表大小如何影响模型？

| 词表大 (200K) | 词表小 (32K) |
|---|---|
| ✅ token 数少（推理快） | ❌ 序列长（推理慢） |
| ❌ embedding 层 + lm_head 参数巨大 | ✅ embedding 层小 |
| ❌ rare token 训练不充分 | ✅ token 训练充分 |

**经验值**：
- GPT-2: 50K
- LLaMA-1/2: 32K（英语为主，对中文不友好）
- LLaMA-3: **128K**（大幅扩展）
- Qwen-2: 152K
- GLM-4: 152K

---

## 8. OOV 问题怎么处理？

**Subword 级基本无 OOV**：
- 任何字符都能拆到字符或字节级
- BPE/WordPiece 训练时，所有字符进入词表初始集合

**Byte-level BPE 真正 0 OOV**：
- 最底层是 256 个字节
- 遇到训练时未见过的字符（如生僻 emoji），拆成多个字节 token
- 模型能处理，但语义可能不准

---

## 9. Tokenizer 训练流程

1. **准备语料**：覆盖目标领域、语种（多语种、代码、数学等）
2. **预处理**：normalization（如 NFKC）、删除控制字符
3. **选算法**：SentencePiece BPE 最常见
4. **设词表大小**：目标 token 数（如 128K）
5. **训练**：迭代合并 / 删除子词
6. **保存**：vocab.json + merges.txt（BPE）或 sp.model（SentencePiece）
7. **特殊 token**：手动添加 `<pad>`, `<bos>`, `<eos>`, `<|endoftext|>` 等
8. **测试**：在目标语料上看 token/字符 比

---

## 10. Tokenizer 对效果的影响

- **token 经济性**：相同文本下 token 越少，context 利用越高，推理越快
- **数字处理**：早期 tokenizer 把 "12345" 乱拆，影响数学。LLaMA-3、GPT-4 改为 per-digit 编码
- **代码处理**：缩进、关键字的 token 化方式影响代码能力
- **多语种平衡**：低资源语种 token 效率低，影响其能力

---

## 11. 最简记忆

```text
BPE         按频率合并相邻对              → GPT-2/3, LLaMA, Qwen
WordPiece   按点互信息合并                → BERT
Unigram LM  从大词表开始，逐步删          → T5, ALBERT（SentencePiece 内）
Byte-level  最底层是字节 → 0 OOV         → GPT-2 起广泛使用

中文 token 效率：LLaMA-2 差 → LLaMA-3 / Qwen 大幅改善（扩词表）

Tokenizer 训完很难改：embedding 不对齐 → 几乎要重训。
```

---

## 🎯 高频追问

1. **为什么 GPT-2 用 Byte-level BPE**？字节级保证 0 OOV，处理任意输入（包括奇怪 Unicode）。

2. **特殊 token 怎么加**？通过 `add_special_tokens` 加入词表，embedding 和 lm_head 需要扩容。

3. **能更新 tokenizer 吗**？非常难。预训练后改 tokenizer 几乎要重训（embedding 不对齐）。通常只能"嫁接"+ 少量训练。

4. **数字怎么处理最好**？per-digit 切分（每个数字一个 token），数学能力更好。LLaMA-3、GPT-4 都改成这样。

5. **BPE 推理时怎么应用**？严格按训练时的合并顺序应用，不可乱序。
