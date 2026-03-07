# PDF + Web 爬取双模态Loader扩展 - 快速导航

## 📋 改动概览

本项目已根据需求完成了设计规范更新，将原本**仅支持PDF**的Loader扩展为**同时支持PDF和网站爬取**的双模态系统。所有改动遵循**保持框架完整、最小化改动**的原则。

### ✅ 完成内容

- ✅ Loader层双模态架构设计
- ✅ 网站白名单与爬取策略定义（8个精品咖啡网站）
- ✅ Recipe参数结构化提取方案
- ✅ 统一Metadata架构设计
- ✅ 存储层（Chroma/BM25/SQLite）适配方案
- ✅ 检索层（HybridRetriever/MCP）适配方案
- ✅ 质量评估模块适配方案
- ✅ Dashboard六页面适配指南
- ✅ 完整的回归测试用例
- ✅ 向后兼容性验证

### 📦 核心架构保持不变

- Pipeline流程：Loader → Splitter → Transform → Embed → Upsert（不变）
- 各层职责边界：清晰分离，Splitter/Transform/Embed/Upsert层**零改动**
- 存储基础设施：Chroma、BM25、SQLite**无代码改动**，仅metadata扩展
- 检索策略：Dense+Sparse混合、RRF融合、Rerank机制**完全兼容**

---

## 🚀 快速开始

### 1️⃣ 了解整体改动方案（5分钟）
📄 **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)**
- 改动范围总览
- 网站白名单详情
- 向后兼容性说明
- 4周开发计划

### 2️⃣ 学习Loader实现细节（30分钟）
📄 **[LOADER_EXTENSION_SPEC.md](./LOADER_EXTENSION_SPEC.md)**
- BaseLoader/PDFLoader/WebLoader完整代码
- 白名单验证机制
- Recipe参数提取算法
- 去重哈希计算
- 单元测试清单

**核心类**：
```python
class BaseLoader(ABC):
    def load(self, source_path=None, source_url=None) -> Document
    def validate(self, source) -> bool

class PDFLoader(BaseLoader):
    # MarkItDown解析 → Markdown转换 → 元数据抽取
    
class WebLoader(BaseLoader):
    # 白名单验证 → HTML爬取 → Recipe识别 → 参数提取
    
class LoaderFactory:
    @staticmethod
    def get_loader(source_type: str) -> BaseLoader
```

### 3️⃣ 了解存储、检索、评估的适配（30分钟）
📄 **[STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md](./STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md)**
- Chroma metadata兼容性
- BM25索引的doc_type支持
- DocumentManager的doc_type识别
- HybridRetriever的过滤参数
- 回归测试用例

**关键改动**：
```python
# 查询时支持按doc_type过滤
results = retriever.retrieve(query, top_k=10, doc_type_filter="pdf")
# 或
results = retriever.retrieve(query, top_k=10, doc_type_filter="website")
# 或（默认）
results = retriever.retrieve(query, top_k=10)  # 混合查询
```

### 4️⃣ 了解Dashboard适配（20分钟）
📄 **[DASHBOARD_ADAPTATION_GUIDE.md](./DASHBOARD_ADAPTATION_GUIDE.md)**
- 六个页面的UI改动
- 新增doc_type过滤控件
- PDF/Web选项卡设计
- Chunk/Trace详情的差异化展示
- Streamlit代码示例

**页面改动概览**：
```
✏️ 系统总览       → 新增"数据源支持"区, 统计按doc_type细分
✏️ 数据浏览器     → 新增doc_type过滤, 表格新增Website列
✏️ Ingestion管理  → 新增PDF上传/Web爬取选项卡
✏️ Query追踪      → Candidate显示doc_type标签
✏️ Ingestion追踪  → 追踪记录按源类型展示
✏️ 评估面板       → 报告按doc_type分组
```

### 5️⃣ 查看DEV_SPEC的更新（15分钟）
📄 **[DEV_SPEC.md](./DEV_SPEC.md)** (已更新以下部分)
- 3.1.1 数据摄取流水线 - Loader支持改动
- ingestion_history表结构扩展
- MCP工具参数新增（query_knowledge_hub的doc_type参数）

---

## 📚 文档导航表

| 文档 | 面向 | 内容 | 阅读时间 |
|------|------|------|---------|
| **IMPLEMENTATION_SUMMARY.md** | 所有人 | 全局改动概览、项目计划、验收清单 | 5-10分钟 |
| **LOADER_EXTENSION_SPEC.md** | 开发者 | Loader完整实现、白名单、参数提取 | 30-45分钟 |
| **STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md** | 开发者 | 存储/检索/评估的改动与集成 | 30-45分钟 |
| **DASHBOARD_ADAPTATION_GUIDE.md** | 前端开发者 | Dashboard六页面的UI改动 | 20-30分钟 |
| **DEV_SPEC.md** | 参考用 | 原项目设计文档，已更新相关部分 | 按需查阅 |

---

## 🎯 关键特性

### 1. 网站白名单机制（数据合规）
```python
WHITELIST = {
    "breville.com": {"name": "Breville", "paths": ["/recipes", ...], ...},
    "baratza.com": {"name": "Baratza", "paths": ["/brew-guides", ...], ...},
    # ... 共8个网站
}

# 自动拒绝非白名单URL
if not web_loader.validate(url):
    raise ValueError("URL not in whitelist")
```

### 2. 双模态Metadata（灵活扩展）
```python
# PDF文档
metadata = {
    "doc_type": "pdf",
    "source": "/path/to/file.pdf",
    "file_size": 2048000,
    "modification_time": "2025-03-07T10:30:00",
    "page_count": 15,
    ...
}

# Website文档
metadata = {
    "doc_type": "website",
    "source": "https://aeropress.com/recipes",
    "website_name": "AeroPress",
    "page_type": "recipe",
    "fetched_at": "2025-03-07T10:30:00Z",
    "recipe_params": {
        "servings": 2,
        "brew_time_minutes": 4,
        "water_temperature_celsius": 200
    },
    ...
}
```

### 3. 统一Document对象（零改动下游）
```python
@dataclass
class Document:
    id: str                    # 全局唯一
    source: str               # 路径或URL
    text: str                 # 规范化Markdown
    metadata: Dict[str, Any]  # 灵活字典

# 后续Pipeline （Splitter/Transform/Embed）无需改动
# 完全兼容document对象，通过doc_type字段感知来源
```

### 4. 可选的检索过滤（无强制）
```python
# 默认：混合检索
results = retriever.retrieve("How to brew?")  # 同时检索PDF和Website

# 可选：指定源类型
results = retriever.retrieve("How to brew?", doc_type_filter="pdf")      # 仅PDF
results = retriever.retrieve("How to brew?", doc_type_filter="website")  # 仅Website

# MCP工具也支持
curl -X POST http://localhost:8000/query_knowledge_hub \
  -d '{"query": "...", "doc_type": "website"}'
```

### 5. Recipe参数自动提取（增强质量）
```python
# 启发式规则 + 可选LLM辅助
recipe_params = {
    "servings": 2,
    "prep_time_minutes": 5,
    "brew_time_minutes": 4,
    "water_temperature_celsius": 200,
    "coffee_grams": 30,
    "water_grams": 500
}

# 提取失败时gracefully降级，仍然可以索引页面文本
```

---

## 🔄 向后兼容性

### 现有部署继续工作（零改动）
```python
# 现有代码无需改动
pipeline.run(source_path="document.pdf")  # ✅ 工作如常
loader = PDFLoader()                       # ✅ 工作如常
```

### 逐步采用新功能（完全可选）
```python
# 新增功能支持
pipeline.run(source_type="website", source_url="https://aeropress.com/recipes")

# 新增检索过滤
retriever.retrieve(query, doc_type_filter="website")

# Dashboard新增可选UI（仅显示，不影响查询）
```

### 数据存储完全兼容（自动适配）
```
Chroma    → metadata新增doc_type字段 ✅ 无需迁移
BM25      → 新增可选doc_type过滤    ✅ 无需迁移
SQLite    → ingestion_history扩展  ✅ 自动扩展表结构
```

---

## 📋 开发统括清单

### Phase 1: Loader核心实现
- [ ] 实现BaseLoader/PDFLoader/WebLoader
- [ ] 白名单验证与爬取流程
- [ ] Recipe参数提取算法
- [ ] Loader层单元测试

### Phase 2: Pipeline与存储集成
- [ ] Pipeline支持source_type参数
- [ ] 扩展ingestion_history表
- [ ] DocumentManager适配
- [ ] 集成测试（PDF→检索，Web→检索）

### Phase 3: 检索与评估适配
- [ ] BM25索引doc_type支持
- [ ] HybridRetriever新增参数
- [ ] MCP工具参数扩展
- [ ] 评估报告按doc_type分组

### Phase 4: Dashboard开发
- [ ] 六页面新增doc_type控件
- [ ] PDF/Web选项卡
- [ ] Chunk/Trace详情组件
- [ ] Dashboard集成测试

### Phase 5: 文档与部署
- [ ] 用户文档
- [ ] 白名单列表与示例
- [ ] 性能基准
- [ ] 生产验证

---

## 💡 核心设计原则

| 原则 | 实现 | 好处 |
|------|------|------|
| **最小化改动** | Loader新增，后续层无改动 | 风险小，易维护 |
| **框架完整** | Pipeline流程不变 | 升级现有系统零成本 |
| **灵活扩展** | Metadata字典化 | 易添加新数据源 |
| **合规运营** | 白名单机制 | 数据来源明确可控 |
| **用户体验** | 默认混合查询+可选过滤 | 简单易用，高级可选 |
| **向后兼容** | 所有新功能可选 | 现有部署继续工作 |

---

## 🎓 学习路径建议

### 初级（想快速了解）
1. 读 [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) 的概述部分（5分钟）
2. 查看"网站白名单详情"表（3分钟）
3. Done！你已了解整个方案

### 中级（想参与设计讨论）
1. 读 [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) 完整（15分钟）
2. 读 [LOADER_EXTENSION_SPEC.md](./LOADER_EXTENSION_SPEC.md) 的"核心设计原则"和"Loader架构设计"（20分钟）
3. 查看"关键设计决策"部分（10分钟）
4. 提出反馈与优化建议

### 高级（想实现代码）
1. 按顺序精读四份文档（2-3小时）
2. 根据 [LOADER_EXTENSION_SPEC.md](./LOADER_EXTENSION_SPEC.md) 实现Loader层
3. 根据 [STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md](./STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md) 适配存储/检索
4. 根据 [DASHBOARD_ADAPTATION_GUIDE.md](./DASHBOARD_ADAPTATION_GUIDE.md) 开发UI
5. 按开发统括清单执行与验收

---

## ❓ 常见问题

**Q: 我是不是必须使用Web爬取功能？**
A: 不是。Web爬取完全可选，现有PDF-only部署继续工作。

**Q: 能添加新的网站到白名单吗？**
A: 可以，修改WebLoader.WHITELIST字典，建议先测试爬取的稳定性。

**Q: 我如何确保数据隐私？**
A: 白名单限制爬取来源；所有数据本地存储；DataStore（Chroma/BM25）无需网络。

**Q: Splitter/Transform/Embed层真的完全不需要改吗？**
A: 是的。Document对象格式不变，metadata为通用字典，这些层直接兼容。

**Q: 怎么样测试新的PDF+Web混合查询？**
A: 阅读 [STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md](./STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md) 中的"TestDualLoaderIntegration"章节。

---

## 📞 反馈与改进

这是一份设计方案，在实现前可能需要根据实际情况微调。欢迎提出：
- 设计问题或疑惑
- 实现难度评估
- 优化建议
- 测试用例想法

---

**方案编制时间**：2025年3月7日
**总文档数**：5份（含本导航文档）
**预期开发周期**：3-4周
**向后兼容性**：100%

🎉 **祝开发愉快！**

