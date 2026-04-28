# PDF 摄取完整指南

## 📁 目录结构

```
MODULAR-RAG-MCP-SERVER/
├── data/
│   ├── pdfs/              ← 放置 PDF 文件的地方
│   ├── db/                ← 自动生成的数据库
│   │   ├── bm25/          ← BM25 索引
│   │   └── ingestion_history.db
│   ├── images/            ← 提取的图片
│   └── logs/              ← 日志文件
├── scripts/
│   └── ingest.py          ← 摄取脚本
└── src/
    └── ingestion/         ← 摄取逻辑
```

---

## 🚀 三种摄取方式

### **方式 1：单个 PDF 文件**

```bash
python scripts/ingest.py --path data/pdfs/example.pdf --collection my_docs
```

**参数说明：**
- `--path`：PDF 文件的完整路径（相对或绝对都可以）
- `--collection`：数据集合名（用于分类和查询过滤）
- `--force`（可选）：跳过去重检查，强制重新摄取

**输出示例：**
```
OK  data/pdfs/example.pdf chunks=15 skipped=0
```

---

### **方式 2：整个目录的所有 PDF**

```bash
python scripts/ingest.py --path data/pdfs/ --collection my_docs
```

**行为：**
- 自动递归搜索目录下所有 `.pdf` 文件
- 逐个摄取（失败不中断）
- 输出：
```
OK  data/pdfs/doc1.pdf chunks=8 skipped=0
OK  data/pdfs/subfolder/doc2.pdf chunks=12 skipped=0
ERR data/pdfs/broken.pdf error=Failed to parse PDF
```

---

### **方式 3：重新摄取（跳过去重）**

```bash
python scripts/ingest.py --path data/pdfs/example.pdf --collection my_docs --force
```

**说明：**
- 即使 PDF 已经摄取过，也会重新处理
- 有用场景：更新嵌入模型、修改分块策略等

---

## 📊 摄取流程详解

### 完整的摄取管道：

```
PDF 文件 (data/pdfs/example.pdf)
    ↓
[1] PDFLoader
    - 使用 markitdown 把 PDF 转成 Markdown
    - 提取元数据（文件大小、修改时间、页数）
    ✓ 输出：Document(text, metadata)

    ↓
[2] DocumentChunker  
    - 智能分块（保留上下文和语义）
    - 默认：max_chunk_size=512, overlap=50
    ✓ 输出：List[Chunk]

    ↓
[3] ChunkRefiner / MetadataEnricher / ImageCaptioner
    - 可选的高级处理（需要 LLM）
    - 当前演示跳过
    ✓ 输出：Enriched Chunks

    ↓
[4] BatchProcessor
    - 并行生成嵌入向量
    ├─ DenseEncoder → 384维稠密向量（Sentence-Transformers）
    └─ SparseEncoder → BM25 权重

    ↓
[5] Storage
    ├─ BM25Indexer → 构建 BM25 倒排索引（保存到 data/db/bm25/）
    └─ VectorUpserter → 存储向量到 Chroma（data/db/chroma/）

    ↓
[6] IngestionHistory  
    - 记录到 SQLite：data/db/ingestion_history.db
    - 用于去重和增量摄取

✅ 完成：数据已索引可查询
```

---

## 📝 配置文件（可选）

编辑 `config/settings.yaml` 来自定义行为：

```yaml
ingestion:
  batch_size: 16                    # 并行处理的块数
  bm25_index_dir: data/db/bm25      # BM25 索引位置
  image_root: data/images           # 提取图片存储位置
  history_db: data/db/ingestion_history.db  # 摄取历史数据库

chunking:
  max_chunk_size: 512               # 单个块的最大字符数
  overlap: 50                       # 块之间的重叠

embedding:
  provider: sentence-transformers   # 嵌入模型提供商
  model: all-MiniLM-L6-v2          # 嵌入模型名称
```

---

## 🔍 查看摄取结果

### 查询已摄取的数据：

```python
from src.core.query_engine.hybrid_search import HybridSearch
from src.core.query_engine.query_processor import QueryProcessor
from src.core.settings import get_settings

settings = get_settings()
engine = HybridSearch(
    settings=settings,
    query_processor=QueryProcessor(),
)

# 查询
results = engine.search(
    "your search query", 
    top_k=5, 
    filters={"collection": "my_docs"}  # 只在这个集合中搜索
)

# 显示结果
for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.content[:200]}...")
    print(f"Metadata: {result.metadata}")
    print()
```

---

## 🛠️ 常见问题

### Q: PDF 格式要求？
**A:** 支持标准 PDF 格式（需要可提取文本的 PDF，扫描图片类不支持）

### Q: 如何修改分块大小？
**A:** 编辑 `config/settings.yaml` 或在代码中修改 `DocumentChunker` 参数

### Q: 如何跳过某些 PDF？
**A:** 在命令中使用正确的 `--path`，或者手动修改文件名

### Q: 如何清空已摄取的数据？
**A:** 
```bash
rm -r data/db/chroma  # 删除向量数据库
rm -r data/db/bm25    # 删除 BM25 索引
rm data/db/ingestion_history.db  # 删除摄取历史
```

### Q: 摄取失败了怎么办？
**A:** 查看错误信息，常见原因：
- PDF 文件损坏：用其他 PDF 工具验证
- 内存不足：降低 `batch_size`
- 权限问题：检查文件/目录权限

---

## ✅ 快速开始

```bash
# 1. 将 PDF 文件放到 data/pdfs/ 目录

# 2. 运行摄取
python scripts/ingest.py --path data/pdfs/ --collection my_docs

# 3. 检查结果
# ✓ 看到 "OK  data/pdfs/xxx.pdf chunks=N skipped=0" 表示成功

# 4. 进行查询
python -c "
from src.core.query_engine.hybrid_search import HybridSearch
from src.core.query_engine.query_processor import QueryProcessor
from src.core.settings import get_settings

engine = HybridSearch(get_settings(), QueryProcessor())
results = engine.search('search term', top_k=3, filters={'collection': 'my_docs'})
for r in results:
    print(f'{r.chunk_id}: {r.content[:100]}')
"
```

---

## 📞 需要帮助？

- 查看完整流程：`python demo_ingestion.py`
- 运行测试：`pytest tests/integration/test_ingestion_pipeline.py -v`
- 查看配置：`cat config/settings.yaml`
