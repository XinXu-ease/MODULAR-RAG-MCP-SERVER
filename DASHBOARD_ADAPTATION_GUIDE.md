# Dashboard 双模态数据源适配指南

> 本文档说明如何在 Streamlit Dashboard 中适配 PDF 和 Website 两种数据源的展示和管理功能。

## 1. 总体设计思路

### 1.1 现有 Dashboard 六页面架构

现有 DEV_SPEC 中定义的 Dashboard 包含：
1. **系统总览** - 组件配置概览
2. **数据浏览器** - 已索引文档列表与Chunk详情
3. **Ingestion 管理** - 文件上传与摄取进度
4. **Query 追踪** - 查询历史与检索过程可视化
5. **Ingestion 追踪** - 摄取历史与性能分析
6. **评估面板** - 评估任务与指标展示

### 1.2 双模态适配策略

- **最小化改动**：现有页面结构保持不变
- **灵活显示**：根据 `doc_type` 字段动态显示 PDF 或 Website 特有的信息
- **新增视图**：在每个页面增加 `doc_type` 过滤/分组选项
- **统一metadata展示**：使用统一的metadata结构，按doc_type渲染相关字段

---

## 2. 各页面的具体适配方案

### 2.1 系统总览页

**现状**：展示当前激活的 LLM, Embedding, Splitter, Reranker 等可插拔组件配置。

**适配方案**：
- 新增 **"数据源支持"** 小区域，展示：
  ```
  ✅ PDF Loader (MarkItDown)
  ✅ Web Loader (BeautifulSoup + Recipe Parser)
  
  Web Whitelist Status:
  - Breville ✓
  - Baratza ✓
  - Fellow ✓
  - Stumptown ✓
  - Blue Bottle ✓
  - Hario USA ✓
  - AeroPress ✓
  - Chemex ✓
  ```
- 新增 **"集合统计"** 按 `doc_type` 细分：
  ```
  Total Collections: 2
  Default Collection:
    - PDF Documents: 12 (156 chunks)
    - Website Documents: 8 (94 chunks)
    - Total: 20 documents, 250 chunks
  ```

### 2.2 数据浏览器页

**现状**：展示已索引的文档列表，支持搜索与过滤；点击文档可查看Chunk详情。

**适配方案**：

#### 2.2.1 文档列表视图

**新增过滤控件**：
```python
# src/dashboard/pages/data_browser.py - 伪代码示意
import streamlit as st

col1, col2 = st.columns(2)
with col1:
    doc_type_filter = st.selectbox(
        "Filter by source type:",
        options=["All", "PDF", "Website"],
        index=0
    )
with col2:
    search_text = st.text_input("Search documents...")

# 应用过滤
if doc_type_filter != "All":
    doc_type_map = {"PDF": "pdf", "Website": "website"}
    filtered_docs = [
        d for d in all_documents 
        if d['doc_type'] == doc_type_map[doc_type_filter]
    ]
else:
    filtered_docs = all_documents

# 构建表格
table_data = []
for doc in filtered_docs:
    row = {
        "Source": doc['source'][:60] + "..." if len(doc['source']) > 60 else doc['source'],
        "Type": "📄 PDF" if doc['doc_type'] == 'pdf' else "🌐 Web",
        "Title": doc['title'],
        "Chunks": doc['chunk_count'],
        "Loaded": doc['loaded_at']
    }
    if doc['doc_type'] == 'website':
        row["Website"] = doc['metadata'].get('website_name', 'Unknown')
    
    table_data.append(row)

st.dataframe(table_data, use_container_width=True)
```

**表格列定义**：
| 列名 | 说明 | 公共 | PDF特有 | Web特有 |
|-----|------|------|---------|--------|
| Source | 文件路径或URL | ✓ | | |
| Type | 数据源图标 | ✓ | | |
| Title | 文档标题 | ✓ | | |
| Chunks | Chunk数量 | ✓ | | |
| Loaded | 加载时间 | ✓ | | |
| File Size | 文件大小（字节） | | ✓ | |
| Website | 网站名 | | | ✓ |
| Page Type | Recipe/Guide/Manual | | | ✓ |

#### 2.2.2 Chunk 详情视图

点击文档后展示其Chunk列表，支持展开查看Chunk详情。

**PDF Chunk详情展示**：
```
Chunk ID: pdf_001_chunk_05
Source: /path/to/document.pdf
Page: 5
Title: ### Section Title
Length: 342 tokens
Text Preview:
---
This is the chunk content...
---
Images: 0
Metadata:
- doc_type: pdf
- file_size: 2048000
- modification_time: "2025-03-07T10:30:00"
```

**Website Chunk详情展示**：
```
Chunk ID: web_001_chunk_03
Source: https://aeropress.com/recipes
Page Type: recipe
Title: Classic AeroPress Recipe
Length: 256 tokens
Text Preview:
---
This is the chunk content...
---
Recipe Params:
- Servings: 2
- Prep Time: 5 minutes
- Brew Time: 4 minutes
- Water Temperature: 200°C
- Coffee: 30g
- Water: 500g

Metadata:
- doc_type: website
- website_name: AeroPress
- fetched_at: "2025-03-07T10:30:00Z"
```

---

### 2.3 Ingestion 管理页

**现状**：用户可通过界面选择本地文件，触发摄取流程，实时展示进度。

**适配方案**：

#### 2.3.1 新增选项卡 (Tabs)

```python
# src/dashboard/pages/ingestion_management.py - 伪代码示意
import streamlit as st

tab1, tab2 = st.tabs(["📄 PDF Upload", "🌐 Web Crawler"])

with tab1:
    st.subheader("Upload PDF Documents")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file and st.button("Start Ingestion"):
        pipeline.run(source_type="pdf", source_path=uploaded_file)

with tab2:
    st.subheader("Fetch from Whitelisted Websites")
    
    website = st.selectbox(
        "Select Website:",
        options=[
            ("Breville", "breville.com"),
            ("Baratza", "baratza.com"),
            ("Fellow", "fellowproducts.com"),
            ("Stumptown", "stumptowncoffee.com"),
            ("Blue Bottle", "bluebottlecoffee.com"),
            ("Hario USA", "hariousa.com"),
            ("AeroPress", "aeropress.com"),
            ("Chemex", "chemexcoffeemaker.com")
        ]
    )
    
    # 显示该网站支持的页面类型
    page_types = WHITELIST_CONFIG.get(website)[1]['page_types']
    st.info(f"✅ Supported page types: {', '.join(page_types)}")
    
    url = st.text_input("Enter full URL:")
    
    if url and st.button("Start Crawling"):
        pipeline.run(source_type="website", source_url=url)
```

#### 2.3.2 进度条与日志

两种数据源的进度条应显示相同的阶段流程：即使是 Web 爬取也会经历 Load → Split → Transform → Embed → Upsert 的相同阶段。

```python
# 统一的进度显示
stages = ["Load", "Split", "Transform", "Embed", "Upsert"]
progress_bar = st.progress(0)
progress_text = st.empty()

for i, stage in enumerate(stages):
    progress_text.write(f"Current stage: {stage}")
    progress_bar.progress((i + 1) / len(stages))
    # 等待该阶段完成...
    time.sleep(1)  # 占位

# 最终日志与统计
st.success("Ingestion completed!")
st.dataframe({
    "Stage": stages,
    "Duration (ms)": [100, 200, 150, 300, 250],
    "Status": ["✓", "✓", "✓", "✓", "✓"]
})
```

---

### 2.4 Query 追踪页

**现状**：展示查询历史，选择查询可视化其检索过程（Dense/Sparse候选对比、Rerank效果）。

**适配方案**：

#### 2.4.1 查询历史表格

新增 `doc_type_filter` 列，显示本次查询是否启用了 doc_type 过滤：

| Query | Timestamp | Top Result | Doc Type Filter | Latency |
|-------|-----------|-----------|-----------------|---------|
| How to brew? | 2025-03-07 10:30 | aeropress.pdf | None (All) | 245ms |
| Recipe parameters | 2025-03-07 10:31 | aeropress.com | website | 198ms |

#### 2.4.2 查询详情页

点击查询后展示Dense/Sparse候选对比时，为每个候选添加 `doc_type` 标签：

```
Dense Route (Top-5):
1. 📄 aeropress_guide.pdf - Score: 0.92
2. 🌐 aeropress.com/recipes - Score: 0.88
3. 📄 brew_basics.pdf - Score: 0.85
...

Sparse Route (Top-5):
1. 🌐 aeropress.com/recipes - Score: 45.2
2. 📄 aeropress_guide.pdf - Score: 38.5
...

RRF Fusion Result (Top-5):
1. 📄 aeropress_guide.pdf
2. 🌐 aeropress.com/recipes
...
```

---

### 2.5 Ingestion 追踪页

**现状**：展示摄取历史，可查看各阶段耗时与处理详情。

**适配方案**：

#### 2.5.1 追踪记录表格

新增 `Source Type` 列：

| Source | Type | Status | Chunks | Total Time | Date |
|--------|------|--------|--------|-----------|------|
| sample.pdf | 📄 PDF | ✓ | 42 | 1.23s | 2025-03-07 10:30 |
| aeropress.com/recipes | 🌐 Web | ✓ | 5 | 2.15s | 2025-03-07 10:31 |

#### 2.5.2 追踪详情视图

PDF 和 Website 的详情展示在结构上一致，但显示的具体值不同：

**PDF Ingestion Trace 详情**：
```
Trace ID: ing_20250307_001
Source Type: 📄 PDF
Source: /data/documents/aeropress_guide.pdf
Collection: default
Status: Success
Timeline:
  Load (MarkItDown)       → 245ms | 42 chunks, 0 images
  Split (Recursive)       → 189ms | chunk_size: 512, overlap: 100
  Transform (Captioning)  → 0ms   | 0 images to process
  Embed (text-embedding-3) → 834ms | Dense: 384d, Sparse: BM25
  Upsert (Chroma)         → 156ms | Upsert: 42 chunks, BM25 update: 42 docs
Total Latency: 1.424s
Total Chunks: 42
Total Images: 0
Metadata:
- file_size: 2048000 bytes
- page_count: 15
- title: "AeroPress Brewing Guide"
```

**Website Ingestion Trace 详情**：
```
Trace ID: ing_20250307_002
Source Type: 🌐 Web
Source: https://aeropress.com/recipes
Collection: default
Status: Success
Timeline:
  Load (BeautifulSoup)    → 1125ms | Recipe detected, 1 page, 3 images
  Split (Recursive)       → 89ms  | chunk_size: 512, overlap: 100
  Transform (Captioning)  → 342ms | 3 images captioned
  Embed (text-embedding-3) → 156ms | Dense: 384d, Sparse: BM25
  Upsert (Chroma)         → 98ms  | Upsert: 5 chunks, BM25 update: 5 docs
Total Latency: 1.810s
Total Chunks: 5
Total Images: 3
Metadata:
- website_name: AeroPress
- page_type: recipe
- fetched_at: 2025-03-07T10:31:00Z
- recipe_params: {servings: 2, brew_time_minutes: 4, water_temperature_celsius: 200, ...}
```

---

### 2.6 评估面板

**现状**：运行评估任务，展示Hit Rate、Faithfulness等指标。

**适配方案**：

#### 2.6.1 评估报告按 doc_type 分组

在评估统计中新增 `doc_type` 维度：

```
Overall Metrics:
- Hit Rate: 85%
- MRR: 0.72
- Faithfulness: 0.88

Metrics by Source Type:
┌─ PDF Documents ─┐
│ Hit Rate: 87%   │
│ MRR: 0.75       │
│ Faithfulness: 0.89 │
│ Sample Size: 50 │
└─────────────────┘

┌─ Website Documents ─┐
│ Hit Rate: 82%   │
│ MRR: 0.68       │
│ Faithfulness: 0.86 │
│ Sample Size: 48 │
└─────────────────┘
```

#### 2.6.2 评估任务配置

在创建新评估任务时，支持按 `doc_type` 限制要评估的文档范围：

```python
import streamlit as st

st.subheader("Create Evaluation Task")

col1, col2 = st.columns(2)
with col1:
    task_name = st.text_input("Task Name:", "evaluation_2025_03")

with col2:
    doc_type = st.multiselect(
        "Document Types to Evaluate:",
        options=["PDF", "Website"],
        default=["PDF", "Website"]  # 默认全部
    )

if st.button("Start Evaluation"):
    evaluator.run_evaluation(task_name, doc_types=doc_type)
```

---

## 3. 实施清单

### 页面改动清单

- [ ] **系统总览**
  - [ ] 新增"数据源支持"展示区
  - [ ] 集合统计按 doc_type 细分

- [ ] **数据浏览器**
  - [ ] 添加 doc_type 过滤控件
  - [ ] 表格新增 Website 特有列（Website、Page Type）
  - [ ] Chunk 详情视图区分 PDF 和 Web 展示

- [ ] **Ingestion 管理**
  - [ ] 新增选项卡：PDF Upload / Web Crawler
  - [ ] Web Crawler 页面添加白名单下拉选择
  - [ ] 统一的进度展示（两种源相同阶段）

- [ ] **Query 追踪**
  - [ ] 历史表新增 Doc Type Filter 列
  - [ ] Dense/Sparse 候选添加 doc_type 标签

- [ ] **Ingestion 追踪**
  - [ ] 历史表新增 Source Type 列
  - [ ] 详情视图区分 PDF 和 Web 展示

- [ ] **评估面板**
  - [ ] 报告按 doc_type 分组统计
  - [ ] 评估任务支持 doc_type 选择

### 代码结构调整

```
src/dashboard/
├── pages/
│   ├── overview.py              # 改动：数据源支持区
│   ├── data_browser.py          # 改动：doc_type过滤、表格列、详情差异化
│   ├── ingestion_management.py  # 改动：PDF/Web选项卡
│   ├── query_traces.py          # 改动：doc_type标签
│   ├── ingestion_traces.py      # 改动：源类型识别、差异化详情
│   └── evaluation.py            # 改动：按doc_type分组报告
├── components/
│   ├── chunk_details.py         # 新增：统一的Chunk详情组件，支持doc_type差异化
│   ├── trace_details.py         # 新增：统一的Trace详情组件，支持doc_type差异化
│   └── metadata_display.py      # 新增：通用Metadata展示，按doc_type渲染
└── utils/
    └── doc_utils.py             # 新增：doc_type相关的显示逻辑（图标、颜色等）
```

---

## 4. 向后兼容性

- 现有纯 PDF 的部署将自动显示仅PDF数据的Dashboard视图
- 新增的选项卡、过滤器、细分指标对现有功能无影响
- 所有改动都是**扩展性**的，无需修改现有查询逻辑

---

## 5. 用户体验建议

- **PDF 文档**：用📄 图标标识，显示文件名、页码、文件大小
- **网站文档**：用🌐 图标标识，显示URL、网站名、页面类型
- **颜色编码**：可选在过滤和表格中为两种源使用不同背景色（如蓝色/绿色）
- **快速筛选**：在多个表格的右上角提供"仅显示PDF"/"仅显示Website"快捷按钮
- **白名单标记**：在网站选择器中标记白名单网站为"✓"，其他为"⚠️ Not Whitelisted"

