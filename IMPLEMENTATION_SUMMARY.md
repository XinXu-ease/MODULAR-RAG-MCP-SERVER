# 双模态Loader扩展 - 完整实施方案总结

## 概述

本方案在保持现有RAG系统架构完全不变的前提下，将仅支持PDF的Loader扩展为支持**PDF和网站爬取**两种数据源的双模态系统。所有改动遵循**最小化原则**，确保：

- ✅ 后续所有模块（Splitter、Transform、Embed、Upsert、检索、评估）**零改动**
- ✅ 仅Loader层和轻量级的metadata适配
- ✅ 完全向后兼容，现有PDF工作流保持不变
- ✅ 新增功能完全可选，不影响已有部署

---

## 核心改动范围

### A. Loader层（新增，无现有代码改动）

**新增文件**：
- `src/loaders/web_loader.py` - 网站爬取解析器
  - 白名单验证
  - HTML爬取与清理
  - Recipe/Guide识别
  - 参数结构化提取
  - Markdown统一转换

**修改文件**：
- `src/loaders/factory.py` - LoaderFactory支持source_type参数
- `src/loaders/base.py` - Document dataclass（向上游兼容）

**改动影响**：
- Pipeline获得了source_type参数选项
- 默认行为保持为source_type="pdf"（向后兼容）

### B. Metadata架构（扩展，完全兼容）

**通用必填字段**（两种源都有）：
```python
{
    "doc_type": "pdf" | "website",
    "source": str,              # 路径或URL
    "title": str,
    "source_hash": str,         # 用于去重
    "images": List[str]
}
```

**PDF特有字段**（可选）：
```python
{
    "file_size": int,
    "modification_time": str,
    "page_count": int
}
```

**Website特有字段**（可选）：
```python
{
    "website_name": str,
    "page_type": str,           # recipe/guide/manual/other
    "fetched_at": str,
    "recipe_params": Dict       # 可选
}
```

**兼容性分析**：
- Chroma向量库：完全兼容，metadata为任意K-V字典
- BM25索引：完全兼容，仅处理text字段
- 后续Pipeline：通过doc_type字段可识别来源，但无硬依赖

### C. 存储层（无改动，仅扩展能力）

**SQLite ingestion_history表**：
- 新增 `source_type` 字段（区分pdf/website）
- 新增 `url_hash` 字段（Website去重）
- 现有字段保持兼容

**Chroma向量库**：
- metadata新增"doc_type"字段
- 查询时可选按doc_type过滤（无强制）
- 无需修改任何代码

**BM25索引**：
- 新增doc_type_map缓存（可选）
- query()方法新增doc_type_filter参数（可选）
- 现有查询逻辑保持不变

### D. 检索层（新增可选参数）

**HybridRetriever**：
- retrieve()新增doc_type_filter参数（可选）
- 默认行为：不过滤（同时查询两种源）
- 现有逻辑保持不变

**MCP Server**：
- query_knowledge_hub工具新增doc_type参数（可选）
- 默认行为：不过滤
- 向后兼容

### E. 评估层（新增分组维度）

**评估报告**：
- 新增按doc_type分组的细分指标
- 现有全局指标保持不变
- 支持Golden Test Set中包含两种源的样本

**质量评估逻辑**：
- 无改动，评估算法对所有Document通用

### F. Dashboard（新增可选视图）

**六个页面全部支持doc_type区分**：
1. 系统总览 - 新增数据源支持展示
2. 数据浏览器 - 新增doc_type过滤
3. Ingestion管理 - 新增PDF/Web选项卡
4. Query追踪 - Candidate显示doc_type标签
5. Ingestion追踪 - 追踪记录按源类型展示
6. 评估面板 - 报告按doc_type分组

**对现有功能的影响**：
- 完全新增的UI控件，不改动现有逻辑
- 新增的选项卡与过滤器为可选
- 纯PDF部署不需要使用新功能

---

## 实施文档

本方案包含4份详细的实施文档，已存储在项目根目录：

### 1. **LOADER_EXTENSION_SPEC.md** (核心)
完整的Loader扩展设计规范，包含：
- BaseLoader/PDFLoader/WebLoader/LoaderFactory的详细实现代码
- 网站白名单与爬取策略
- Recipe参数结构化提取算法
- 与现有Pipeline的集成方式
- unittest清单

**关键代码片段**：
- `PDFLoader.load()` - 从PDF路径解析到Document对象
- `WebLoader.load()` - 从网站URL爬取到Document对象
- `WebLoader.WHITELIST` - 8个白名单网站的配置
- `WebLoader._extract_recipe_params()` - Recipe参数提取示例

### 2. **STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md** (数据流)
说明存储、检索、评估模块如何无缝适配两种数据源，包含：
- Chroma metadata扩展
- BM25索引的doc_type过滤
- DocumentManager的更新
- HybridRetriever的doc_type_filter参数
- 回归测试用例
- 兼容性矩阵

**关键改动**：
- `ingestion_history`表新增source_type/url_hash字段
- `BM25Indexer.query()`新增doc_type_filter参数
- `HybridRetriever.retrieve()`新增doc_type_filter参数
- MCP工具新增doc_type参数

### 3. **DASHBOARD_ADAPTATION_GUIDE.md** (UI)
Dashboard六个页面的具体适配方案，包含：
- 每个页面的新增控件与表格列
- Chunk详情和Trace详情的差异化展示
- 代码示例（Streamlit伪代码）
- 实施清单

**关键UI改动**：
- 页面新增doc_type过滤/组选择
- 表格新增doc_type图标标识
- PDF和Web相关字段的条件显示
- 按doc_type细分的统计报告

### 4. **DEV_SPEC.md** (已更新)
原设计文档的修改部分：
- 3.1.1 数据摄取流水线：Loader支持改动说明
- ingestion_history表结构扩展
- MCP工具参数新增

---

## 网站白名单详情

本方案支持8个精品咖啡相关网站的爬取（均为公开可用数据）：

| # | 网站 | 支持页面类型 | 示例URL | 说明 |
|---|------|-----------|---------|------|
| 1 | Breville | recipes, tutorials, manuals | breville.com/recipes | 高端咖啡机 |
| 2 | Baratza | brew-guides, manuals | baratza.com/brew-guides | 专业磨豆机 |
| 3 | Fellow | brew-guides, brew-talks | fellowproducts.com/brew-guides | 设备+新配方 |
| 4 | Stumptown | brew-guides | stumptowncoffee.com/brew-guides | 精品烘焙商 |
| 5 | Blue Bottle | brew-guides | bluebottlecoffee.com/brew-guides | 精品咖啡 |
| 6 | Hario USA | recipes, guides | hariousa.com/recipes | 手冲设备 |
| 7 | AeroPress | recipes, how-to | aeropress.com/recipes | 官方资源 |
| 8 | Chemex | brew-pages | chemexcoffeemaker.com/brew | 官方资源 |

**白名单验证**：WebLoader.validate()自动拒绝非白名单URL，确保数据合规性。

---

## 向后兼容性说明

| 场景 | 现状 | 新方案 |
|-----|------|--------|
| 现有PDF-only部署 | `pipeline.run(source_path="file.pdf")` | ✅ 保持不变 |
| 默认参数调用 | source_type默认为"pdf" | ✅ 保持不变 |
| 现有检索查询 | 不指定doc_type_filter | ✅ 同时检索PDF和Website |
| Dashboard使用 | 所有新增UI为可选 | ✅ 现有部署自动显示 |
| 存储与索引 | Chroma/BM25无改动 | ✅ 自动兼容新metadata |
| 后续Pipeline模块 | Splitter/Transform/Embed无需改动 | ✅ Document对象完全兼容 |

**迁移路径**：
1. 现有部署无需任何改动，继续正常工作
2. 逐步添加Website数据源时，新增WebLoader使用
3. 逐个启用Dashboard的doc_type过滤视图
4. Metadata和存储自动适配，无需迁移脚本

---

## 关键设计决策及理由

### 1. 为什么采用白名单而非开放爬取？
- ✅ **合规性**：明确授权、避免未授权爬取
- ✅ **数据质量**：精心挑选的来源确保内容准确
- ✅ **维护成本**：白名单数量可控，爬取策略可针对优化
- ✅ **用户信任**：透明告知数据源

### 2. 为什么统一为Markdown格式？
- ✅ **兼容性**：后续Pipeline对Markdown有优化支持
- ✅ **质量**：统一格式便于高质量的分块与增强
- ✅ **可观测性**：便于调试和人工验证

### 3. 为什么参数解析采用启发式+LLM？
- ✅ **成本平衡**：启发式规则快速识别，LLM精化
- ✅ **准确性**：组合方案优于单一方案
- ✅ **容错性**：无法解析时可优雅降级

### 4. 为什么metadata采用灵活字典而非强类型？
- ✅ **扩展性**：新增来源无需修改代码
- ✅ **简洁性**：避免复杂的类型系统
- ✅ **兼容性**：与现有存储系统无缝适配

### 5. 为什么检索时doc_type_filter为可选？
- ✅ **默认用户体验**：用户无需关心源类型，自动混合搜索
- ✅ **高级用户**：可选参数支持精细控制
- ✅ **无性能开销**：不启用时无额外计算

---

## 实施步骤建议

### Phase 1：Loader层开发（核心）
1. 实现BaseLoader与PDFLoader（参考LOADER_EXTENSION_SPEC.md）
2. 实现WebLoader（含白名单、爬取、参数提取）
3. 实现LoaderFactory
4. 编写Loader层单元测试

**预期用时**：1-2周

### Phase 2：Pipeline与存储适配
1. 修改Pipeline以支持source_type参数
2. 扩展ingestion_history表
3. 修改DocumentManager
4. 编写集成测试（包括去重验证）

**预期用时**：3-5天

### Phase 3：检索与评估适配
1. 修改BM25索引（新增doc_type_map与过滤）
2. 修改HybridRetriever（新增doc_type_filter）
3. 修改MCP Server工具
4. 扩展评估报告生成

**预期用时**：3-5天

### Phase 4：Dashboard适配
1. 各页面新增doc_type过滤与展示
2. 创建Chunk/Trace详情的差异化组件
3. 添加PDF/Web爬取选项卡
4. 集成并测试

**预期用时**：1周

### Phase 5：文档与测试
1. 编写用户文档（参数说明、白名单列表）
2. 补充端到端集成测试
3. 性能基准测试
4. 部署验证

**预期用时**：3-5天

**总体预期**：3-4周

---

## 开发检查清单

### Loader层
- [ ] BaseLoader/PDFLoader/WebLoader/LoaderFactory实现
- [ ] WebLoader白名单验证逻辑
- [ ] HTML清理与Markdown转换
- [ ] Recipe参数提取算法
- [ ] 去重哈希计算（文件和URL分别）
- [ ] Loader层单元测试（覆盖PDF/Web双路）

### Pipeline与存储
- [ ] ingestion_history表扩展
- [ ] Pipeline.run()支持source_type参数
- [ ] DocumentManager.delete_document()适配source_type识别
- [ ] 集成测试：PDF摄取到检索
- [ ] 集成测试：Website爬取到检索
- [ ] 去重测试（重复PDF和URL）

### 检索与评估
- [ ] BM25Indexer doc_type支持
- [ ] HybridRetriever doc_type_filter参数
- [ ] MCP工具参数扩展
- [ ] 检索测试：混合源查询
- [ ] 检索测试：指定源类型查询
- [ ] 评估报告按doc_type细分

### Dashboard
- [ ] 各页面doc_type过滤控件
- [ ] PDF/Web统一的表格显示
- [ ] Chunk详情差异化组件
- [ ] Trace详情差异化组件
- [ ] PDF上传选项卡
- [ ] Web爬取选项卡（含白名单下拉）
- [ ] Dashboard集成测试

### 文档与部署
- [ ] 用户文档（如何使用新功能）
- [ ] 参数说明（doc_type、source_url等）
- [ ] 白名单网站列表与示例URL
- [ ] 迁移指南（for现有部署）
- [ ] 性能基准测试报告
- [ ] 生产环境验证

---

## 常见问题

**Q: 现有的只用PDF的部署会受影响吗？**
A: 完全不受影响。所有新功能都是可选的，现有pipeline.run()调用保持不变，仍默认处理PDF。

**Q: 能添加新的网站白名单吗？**
A: 可以，修改WebLoader.WHITELIST字典即可。建议添加前进行爬虫测试，确保页面结构稳定。

**Q: Recipe参数提取失败时会怎样？**
A: 参数提取为可选增强，失败时gracefully降级，仍然可以索引和检索Recipe页面的文本内容。

**Q: Dashboard如何显示没有的字段？**
A: 使用metadata.get()方法with默认值，或用doc_type判断是否显示某些列/行。

**Q: 能否混合检索PDF和Website？**
A: 可以，默认行为就是混合检索。也支持通过doc_type_filter指定仅查询某一源。

**Q: Website爬取有频率限制吗？**
A: 建议在WebLoader中添加delays和robots.txt遵守，具体实现可参考LOADER_EXTENSION_SPEC.md。

---

## 相关文档链接

- [LOADER_EXTENSION_SPEC.md](./LOADER_EXTENSION_SPEC.md) - Loader完整实现规范
- [STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md](./STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md) - 存储/检索/评估适配
- [DASHBOARD_ADAPTATION_GUIDE.md](./DASHBOARD_ADAPTATION_GUIDE.md) - Dashboard六页面适配
- [DEV_SPEC.md](./DEV_SPEC.md) - 原项目设计文档（已更新相关部分）

---

**方案完成日期**：2025年3月7日
**总文档数**：4份详细规范 + 本总结
**预期开发周期**：3-4周
**向后兼容性**：100%

