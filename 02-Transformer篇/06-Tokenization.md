# Tokenization（分词）

> Tokenizer 是 LLM 的入口，BPE / WordPiece / SentencePiece 必知。

---

## Q1: 为什么不直接用字符或词作为 token？

**答**：
**字符级**：
- 优点：词表小（~ASCII 字符集）
- 缺点：序列太长，计算量大；模型需自己学组词

**词级**：
- 优点：语义直观
- 缺点：词表巨大（百万级）；OOV（Out-Of-Vocabulary）严重；新词无法表示

**Subword 级（BPE/WordPiece/Unigram）**：折中
- 词表中等（30K-150K）
- 高频词作为整词，低频词拆成子词
- 无 OOV，每个字符串都能被拆分表示
- LLM 时代主流

---

## Q2: BPE（Byte Pair Encoding）的算法？

**答**：
**起源**：原本是压缩算法（Sennrich et al. 2016 引入到 NMT）。

**算法**：
1. 初始化：词表 = 所有字符。
2. 在训练语料上统计相邻字符对的频率。
3. 选频率最高的对（如 ("l", "o")），合并成新 token（"lo"）加入词表。
4. 在所有出现该对的地方替换为新 token。
5. 重复直到词表达到目标大小。

**示例**：
```
初始: l o w </w>  l o w </w>  n e w e s t </w>  w i d e s t </w>
合并 (l, o): lo w </w>  lo w </w>  n e w e s t </w>  w i d e s t </w>
合并 (lo, w): low </w>  low </w>  ...
合并 (e, s): low </w>  low </w>  n e w es t </w>  w i d es t </w>
...
```

**特点**：
- 贪心算法
- 拆分时按合并顺序应用规则
- GPT-2、GPT-3 用 Byte-level BPE（基于字节而非字符，能处理任意 Unicode）

---

## Q3: WordPiece 与 BPE 的区别？

**答**：
**核心算法相似**：迭代合并最频繁的对。

**关键差异**：
- BPE 用**频率**作为合并判据
- WordPiece 用**似然增益**作为判据（合并后语言模型概率提升最大的对）
- 公式：选 $\arg\max \frac{P(AB)}{P(A) P(B)}$（点互信息）

**代表**：BERT、DistilBERT 用 WordPiece。

**实际差异不大**：两者效果接近，主要看实现细节。

---

## Q4: SentencePiece 与 BPE 的区别？

**答**：
**SentencePiece** 是 Google 的库，支持多种算法（BPE、Unigram），核心特点：

1. **不依赖空格分词**：把空格视为普通字符（用 `▁` 表示），适合**无空格的语言**（中文、日文）。
2. **可逆**：原始文本 → tokens → 原始文本 不丢失信息。
3. **包含 Unigram LM 算法**：用概率模型选最优 subword 集合。

**Unigram LM 算法**：
1. 初始化大词表
2. 用 EM 算法估计每个 subword 的概率
3. 迭代删掉对似然贡献最小的 subword
4. 直到词表达到目标大小

**代表**：T5、ALBERT、LLaMA、Qwen 都用 SentencePiece。

---

## Q5: Tiktoken 是什么？

**答**：
- OpenAI 的高速 BPE 实现（Rust 编写，Python 绑定）。
- 用于 GPT-3.5/4 系列。
- 速度比 HuggingFace tokenizers 快约 3-6 倍。
- 支持多种编码：`cl100k_base`（GPT-4）、`o200k_base`（GPT-4o）等。

---

## Q6: 中文分词的特殊问题？

**答**：
**核心问题**：中文无空格分隔。

**LLM 时代解法**：
- 用 SentencePiece 等 byte-level 或 char-level subword
- 中文常以单字或双字为基本 token
- 词表中加入大量常用中文字符（如 LLaMA-3 扩展词表为 128K 包含中文）

**OOV 处理**：
- 极生僻字会被拆成 UTF-8 字节（多个 token）
- 字节级 BPE 保证不会有真正的 OOV

**经济性**：
- 中文 token 通常比英文"昂贵"——一段相同长度的文本，中文 token 数往往多。
- 国产模型（Qwen、DeepSeek）扩展中文词表后效率显著提升。

---

## Q7: 词表大小如何影响模型？

**答**：
**词表大**（如 200K）：
- 优点：每个 token 信息密度高，序列短，推理快
- 缺点：embedding 层和 lm_head 参数巨大，训练显存大；rare token 训练不充分

**词表小**（如 32K）：
- 优点：embedding 层小
- 缺点：序列长，推理慢；非英文语种 token 效率低

**经验值**：
- GPT-2: 50K
- LLaMA-1/2: 32K（英语为主，对中文不友好）
- LLaMA-3: 128K（大幅扩展）
- Qwen-2: 152K
- 国产 GLM/Baichuan：~64-128K

---

## Q8: OOV 问题怎么处理？

**答**：
**Subword 级别基本无 OOV**：
- 任何字符都能拆到字符或字节级。
- BPE/WordPiece 训练时，所有训练数据的字符都进入词表初始集合。

**Byte-level BPE**（GPT-2 / LLaMA-3 / Qwen）：
- 最底层是 256 个字节，覆盖任意 Unicode。
- 真正零 OOV。

**遇到训练时未见过的字符**：
- Subword 拆成字节，可能拆得很碎（如一个 emoji 拆成 4-8 字节）
- 模型能处理但语义可能不准

---

## Q9: Tokenizer 训练流程？

**答**：
1. **准备语料**：覆盖目标领域 / 语种（如多语种、代码、数学）。
2. **预处理**：normalization（NFKC）、删除控制字符、统一编码。
3. **选算法**：BPE / WordPiece / Unigram，工业上 SentencePiece BPE 最常见。
4. **设置词表大小**：目标 token 数（如 128K）。
5. **训练**：迭代合并 / 删除子词。
6. **保存**：vocab.json + merges.txt（BPE）或 sp.model（SentencePiece）。
7. **特殊 token**：手动添加 `<pad>`, `<bos>`, `<eos>`, `<|endoftext|>`, 工具调用 token 等。
8. **测试**：在目标语料上看 token 数 / 字符数比，调整。

---

## Q10: Tokenizer 对训练效果的影响？

**答**：
- **token 经济性**：相同文本下 token 越少，训练时 context 利用率越高，推理越快。
- **数字处理**：早期 tokenizer 把"12345"拆成"1234"+"5"等怪异组合，影响数学能力。LLaMA-3、GPT-4 等做了数字 per-digit 编码。
- **代码处理**：缩进、关键字的 token 化方式影响代码能力。
- **多语种平衡**：低资源语种 token 效率低，影响其能力。

---

## 🎯 高频追问

1. **为什么 GPT-2 用 Byte-level BPE 而不是 Unicode-level**？字节级保证 0 OOV，处理任意输入。
2. **特殊 token 的处理**？通过 `add_special_tokens` 加入词表，embedding 和 lm_head 需要扩容。
3. **Tokenizer 能更新吗**？预训练后改 tokenizer 极困难（embedding 不对齐），通常只能"嫁接"+少量训练或重头训。
4. **为什么 LLaMA-2 中文效果差**？词表只 32K 且偏英文，一个汉字常拆成 3-4 个 byte token，效率极低。LLaMA-3 扩展到 128K 后大幅改善。
5. **BPE 的合并顺序重要吗**？非常重要。tokenizer 推理时严格按训练时的合并顺序应用，不可乱序。
