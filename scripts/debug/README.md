# Debug & Testing Tools

此文件夹包含开发和调试过程中的工具脚本，用于验证系统功能和排查问题。

## 📋 文件说明

### Demo Scripts（使用演示）
这些脚本展示了如何使用 RAG 系统的核心功能：

- **demo_ingestion.py** - 展示如何运行数据摄取管道
  ```bash
  python scripts/debug/demo_ingestion.py
  ```

- **demo_query.py** - 展示如何执行混合查询（Dense + Sparse + Rerank）
  ```bash
  python scripts/debug/demo_query.py
  ```

- **demo_query_dense.py** - 展示纯稠密检索
  ```bash
  python scripts/debug/demo_query_dense.py
  ```

### Inspection Tools（检查工具）
用于查看和验证存储数据的结构和内容：

- **inspect_chunks.py** - 检查向量库中存储的 chunks
  - 显示实际存储的文本内容、ID、距离评分
  - 用于验证数据摄取是否正确

- **inspect_metadata.py** - 检查 chunks 的元数据结构
  - 显示所有 metadata 字段
  - 验证元数据是否完整
  - 测试带过滤条件的查询

### Testing Tools（测试工具）
用于验证系统的分割和处理能力：

- **test_official_markdown_splitter.py** - 验证 Markdown 分割器
  - 测试 LangChain 的官方 MarkdownHeaderTextSplitter
  - 验证按层级分割效果

- **test_semantic_splitter.py** - 验证语义分割器
  - 测试自定义语义边界分割器
  - 检查句子边界是否正确

- **debug_langchain.py** - LangChain 版本和模块检查
  - 验证 LangChain 安装状态
  - 检查文本分割器模块

## 🚀 使用场景

### 验证数据摄取
```bash
# 1. 首先运行演示摄取
python scripts/debug/demo_ingestion.py

# 2. 检查摄取结果
python scripts/debug/inspect_chunks.py
python scripts/debug/inspect_metadata.py
```

### 测试查询功能
```bash
# 运行完整的混合查询演示
python scripts/debug/demo_query.py

# 或测试纯稠密检索
python scripts/debug/demo_query_dense.py
```

### 调试分割器问题
```bash
# 测试 Markdown 分割
python scripts/debug/test_official_markdown_splitter.py

# 测试语义分割
python scripts/debug/test_semantic_splitter.py
```

## ⚠️ 注意事项

- 这些脚本仅用于**开发和调试**，不应在生产环境中使用
- 某些脚本可能会依赖已存在的数据（如 `inspect_*.py`）
- 在运行前请确保配置文件 `config/settings.yaml` 已正确设置

## 📝 添加新工具

如果需要添加新的调试工具：
1. 创建脚本文件：`scripts/debug/debug_xxx.py`
2. 更新此 README 的相应部分
3. 确保脚本包含清晰的注释和使用说明

## 🔧 环境要求

- Python 3.10+
- 项目依赖已安装（`pip install -r requirements.txt`）
- 相关配置文件已初始化
