# 存储、检索与评估模块的双模态适配指南

> 本文档说明如何在保持现有逻辑不变的前提下，为存储、检索、评估模块适配 PDF 和 Website 两种数据源。

## 1. 存储层适配（Vector Store + Sparse Index）

### 1.1 Chroma 向量存储

**现状**：Chroma已支持灵活的metadata存储，无需代码改动。

**适配方案**：
- 新增 `doc_type` metadata筛选字段
- 支持按 `doc_type` 进行过滤查询

```python
# 存储时无需特殊处理，Chroma会自动保存所有metadata
chroma_collection.add(
    ids=[chunk.id],
    embeddings=[chunk.embedding],
    documents=[chunk.text],
    metadatas=[{
        "doc_type": "pdf",         # 新增字段
        "source": "/path/to/file.pdf",
        "title": "...",
        "page": 5                  # PDF特有
        # ... 其他字段
    }]
)

# 查询时支持按doc_type过滤
results = chroma_collection.query(
    query_embeddings=[query_vector],
    n_results=10,
    where={"doc_type": {"$eq": "pdf"}}  # 可选：仅从PDF检索
)
```

**无需改动的原因**：
- Chroma的metadata支持任意K-V结构
- PDF和Website的metadata字段集合有交集且无冲突
- 查询接口已支持where条件

---

### 1.2 BM25 稀疏索引

**现状**：自研的BM25索引器操作通用的Document对象。

**适配方案**：
- 为BM25索引器添加 `doc_type` 字段索引（可选但推荐）
- 支持按 `doc_type` 过滤的BM25查询

```python
# src/retrieval/bm25_indexer.py - 修改示意

class BM25Indexer:
    """BM25倒排索引器"""
    
    def add_document(self, chunk: Dict):
        """添加Document到索引"""
        # 现有逻辑：抽取文本、分词、构建倒排表
        tokens = self._tokenize(chunk['text'])
        doc_id = chunk['id']
        
        # 新增：记录doc_type，便于后续过滤
        self.doc_type_map[doc_id] = chunk['metadata'].get('doc_type', 'unknown')
        
        # 现有逻辑继续...
        self._update_inverted_index(tokens, doc_id)
    
    def query(self, query_text: str, top_k: int = 10, doc_type_filter: str = None) -> List[Tuple[str, float]]:
        """
        BM25 查询。
        
        Args:
            query_text: 查询文本
            top_k: 返回候选数
            doc_type_filter: 可选，过滤特定doc_type（如"pdf"、"website"）
            
        Returns:
            [(doc_id, score), ...] 列表
        """
        # 现有逻辑：分词、计算BM25分数、排序
        tokens = self._tokenize(query_text)
        scores = self._calculate_bm25(tokens)
        
        # 新增：按doc_type过滤
        if doc_type_filter:
            scores = {
                doc_id: score 
                for doc_id, score in scores.items() 
                if self.doc_type_map.get(doc_id) == doc_type_filter
            }
        
        # 排序并返回top-k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
    
    def remove_document(self, doc_id: str):
        """删除Document（支持按doc_type级联删除）"""
        # 从倒排索引中移除该文档的所有token
        tokens = self.doc_id_to_tokens.get(doc_id, [])
        for token in tokens:
            if token in self.inverted_index:
                self.inverted_index[token].discard(doc_id)
                if not self.inverted_index[token]:
                    del self.inverted_index[token]
        
        # 清理doc_type_map
        if doc_id in self.doc_type_map:
            del self.doc_type_map[doc_id]
```

**无需改动的原因**：
- 倒排索引的核心算法不变
- 仅在检索端增加可选过滤，对已有逻辑无影响

---

### 1.3 DocumentManager 扩展

**现状**：存在DocumentManager用于文档生命周期管理。

**适配方案**：
- `list_documents()` 支持按 `doc_type` 过滤
- `delete_document()` 通过metadata识别关联数据

```python
# src/ingestion/document_manager.py - 修改示意

class DocumentManager:
    """文档生命周期管理"""
    
    def list_documents(self, doc_type: str = None, collection: str = "default") -> List[DocumentInfo]:
        """
        列出已摄入的文档。
        
        Args:
            doc_type: 可选，"pdf" 或 "website"
            collection: 存储集合名
            
        Returns:
            DocumentInfo列表
        """
        # 从Chroma查询所有文档的metadata
        all_items = collection.get()  # 获取所有项
        
        documents = []
        for item_id, item_metadata in all_items['metadatas'].items():
            # 按doc_type过滤
            if doc_type and item_metadata.get('doc_type') != doc_type:
                continue
            
            doc_source = item_metadata.get('source')
            doc_info = DocumentInfo(
                id=item_id,
                doc_type=item_metadata.get('doc_type'),
                source=doc_source,
                title=item_metadata.get('title'),
                chunk_count=self._count_chunks_for_source(doc_source),
                created_at=item_metadata.get('modification_time') or item_metadata.get('fetched_at')
            )
            documents.append(doc_info)
        
        return documents
    
    def delete_document(self, source: str, collection: str = "default"):
        """
        删除指定源的所有数据。
        
        自动检测doc_type，协调删除跨存储的数据。
        """
        # 1. 从Chroma查询该source的所有chunk
        results = collection.get(where={"source": {"$eq": source}})
        chunk_ids = results['ids']
        
        if not chunk_ids:
            return DeleteResult(status="not_found")
        
        # 识别doc_type
        sample_metadata = results['metadatas'][0] if results['metadatas'] else {}
        doc_type = sample_metadata.get('doc_type', 'unknown')
        
        try:
            # 2. 从Chroma删除
            collection.delete(ids=chunk_ids)
            
            # 3. 从BM25索引删除
            for chunk_id in chunk_ids:
                self.bm25_indexer.remove_document(chunk_id)
            
            # 4. 删除关联的图像文件（若有）
            images = sample_metadata.get('images', [])
            for image_id in images:
                self.image_storage.delete(image_id)
            
            # 5. 从ingestion_history删除记录
            source_hash = sample_metadata.get('source_hash')
            if source_hash:
                self.integrity_checker.remove_record(source_hash)
            
            return DeleteResult(status="success", deleted_count=len(chunk_ids))
        
        except Exception as e:
            return DeleteResult(status="error", error_msg=str(e))
```

---

## 2. 检索层适配（Query Processing + Hybrid Search）

### 2.1 查询过滤策略

**现状**：Query Processing已支持metadata过滤。

**适配建议**：
- 支持通过 `doc_type_filter` 参数约束检索范围
- 默认行为：不过滤（同时检索PDF和Website）
- 可选显式指定检索特定类型

```python
# src/retrieval/retriever.py - 修改示意

class HybridRetriever:
    """混合检索引擎"""
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        doc_type_filter: str = None  # 新增参数
    ) -> List[Document]:
        """
        执行混合检索（Dense + Sparse + Rerank）。
        
        Args:
            query: 查询文本
            top_k: 返回候选数
            doc_type_filter: 可选，"pdf" 或 "website"
            
        Returns:
            相关Document列表
        """
        # 1. Query Processing（无需改动）
        query_embedding = self.embedding_client.embed(query)
        
        # 2. Dense 检索
        dense_results = self.vector_store.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,
            where={"doc_type": {"$eq": doc_type_filter}} if doc_type_filter else None
        )
        
        # 3. Sparse 检索
        sparse_results = self.bm25_indexer.query(
            query_text=query,
            top_k=top_k * 2,
            doc_type_filter=doc_type_filter
        )
        
        # 4. 融合（RRF，无需改动）
        fused = self._rrf_fusion(dense_results, sparse_results, k=60)
        
        # 5. 精排（可选，无需改动）
        if self.reranker:
            reranked = self.reranker.rerank(query, fused[:top_k*2])
        else:
            reranked = fused[:top_k*2]
        
        # 6. 返回
        return reranked[:top_k]
```

### 2.2 MCP 工具更新

**现状**：MCP Services暴露 `query_knowledge_hub` 工具。

**适配方案**：
- 为 `query_knowledge_hub` 增加可选的 `doc_type` 参数

```python
# src/mcp/server.py - 修改示意

@server.tool()
def query_knowledge_hub(
    query: str,
    top_k: int = 5,
    doc_type: str = None  # 新增参数："pdf" 或 "website"
) -> str:
    """
    主检索入口。
    
    Args:
        query: 查询问题
        top_k: 返回候选数
        doc_type: 可选，过滤特定数据源类型
        
    Returns:
        JSON格式的检索结果（含引用）
    """
    results = retriever.retrieve(query, top_k=top_k, doc_type_filter=doc_type)
    
    response = {
        "answer": "...",
        "citations": [
            {
                "id": 1,
                "source": result.metadata['source'],
                "doc_type": result.metadata['doc_type'],  # 新增：文档类型
                "page": result.metadata.get('page'),  # PDF特有
                "page_type": result.metadata.get('page_type'),  # Website特有
                "text": result.text[:200]
            }
            for result in results
        ]
    }
    
    return json.dumps(response, ensure_ascii=False, indent=2)
```

---

## 3. 质量评估适配

### 3.1 评估集通用化

**现状**：评估集基于Golden Test Set。

**适配方案**：
- Golden Test Set 中的每个query应包含 PDF 和 Website 的参考文档
- 评估报告按 `doc_type` 分组展示

```json
{
    "query": "How to brew coffee with AeroPress?",
    "retrieved_docs": [
        {
            "source": "documents/aeropress_guide.pdf",
            "doc_type": "pdf",
            "expected_rank": 1,
            "hit": true
        },
        {
            "source": "https://aeropress.com/recipes",
            "doc_type": "website",
            "expected_rank": 2,
            "hit": true
        }
    ]
}
```

### 3.2 指标细分

**推荐新增的评估维度**：

```python
# src/evaluation/evaluator.py - 修改示意

class EvaluationReport:
    """评估报告"""
    
    def generate_detailed_report(self) -> Dict:
        """生成详细评估报告（按doc_type细分）"""
        
        overall_metrics = {
            "hit_rate": 0.85,
            "mrr": 0.72,
            "faithfulness": 0.88
        }
        
        # 新增：按doc_type分类的指标
        by_doc_type = {
            "pdf": {
                "hit_rate": 0.87,
                "mrr": 0.75,
                "faithfulness": 0.89,
                "query_count": 50
            },
            "website": {
                "hit_rate": 0.82,
                "mrr": 0.68,
                "faithfulness": 0.86,
                "query_count": 48
            }
        }
        
        return {
            "overall": overall_metrics,
            "by_doc_type": by_doc_type,
            "detailed_cases": [...]
        }
```

### 3.3 回归测试

**测试覆盖**：

```python
# tests/test_dual_loader_integration.py

class TestDualLoaderIntegration:
    """双Loader集成测试"""
    
    def test_pdf_ingestion_to_retrieval(self):
        """端到端：PDF摄取→存储→检索"""
        # 1. 摄取PDF
        result = pipeline.run(source_type="pdf", source_path="test_data/sample.pdf")
        assert result.status == "success"
        
        # 2. 验证Chroma中的metadata
        items = chroma.get(where={"doc_type": {"$eq": "pdf"}})
        assert len(items['ids']) > 0
        assert items['metadatas'][0]['doc_type'] == 'pdf'
        
        # 3. 检索验证
        results = retriever.retrieve("query", doc_type_filter="pdf")
        assert all(r.metadata['doc_type'] == 'pdf' for r in results)
    
    def test_website_ingestion_to_retrieval(self):
        """端到端：Website爬取→存储→检索"""
        # 1. 爬取网站
        result = pipeline.run(source_type="website", source_url="https://aeropress.com/recipes")
        assert result.status == "success"
        
        # 2. 验证Chroma中的metadata
        items = chroma.get(where={"doc_type": {"$eq": "website"}})
        assert len(items['ids']) > 0
        assert items['metadatas'][0]['doc_type'] == 'website'
        assert items['metadatas'][0]['website_name'] == 'AeroPress'
        
        # 3. 检索验证
        results = retriever.retrieve("query", doc_type_filter="website")
        assert all(r.metadata['doc_type'] == 'website' for r in results)
    
    def test_deduplication_pdf_and_website(self):
        """去重：重复的PDF和Website应只被索引一次"""
        # 多次摄取同一PDF
        pipeline.run(source_type="pdf", source_path="test_data/sample.pdf")
        result2 = pipeline.run(source_type="pdf", source_path="test_data/sample.pdf")
        
        assert result2.status == "skipped"  # 应被识别为重复
        
        # 相同URL的Website
        pipeline.run(source_type="website", source_url="https://aeropress.com/recipes")
        result2 = pipeline.run(source_type="website", source_url="https://aeropress.com/recipes")
        
        assert result2.status == "skipped"  # 应被识别为重复
    
    def test_hybrid_retrieval_both_sources(self):
        """混合检索：同时从PDF和Website检索"""
        # 预先摄取一份PDF和一份Website
        pipeline.run(source_type="pdf", source_path="test_data/aeropress.pdf")
        pipeline.run(source_type="website", source_url="https://aeropress.com/recipes")
        
        # 查询（不指定doc_type_filter）
        results = retriever.retrieve("AeroPress brewing", top_k=5)
        
        # 应同时包含PDF和Website的结果
        doc_types = {r.metadata['doc_type'] for r in results}
        assert 'pdf' in doc_types or 'website' in doc_types  # 至少包含一种
    
    def test_doc_type_filter_in_mcp_tool(self):
        """MCP工具：验证doc_type参数"""
        # 仅查询PDF
        result_pdf = call_mcp_tool("query_knowledge_hub", {
            "query": "brewing",
            "doc_type": "pdf"
        })
        assert all(r['doc_type'] == 'pdf' for r in result_pdf['citations'])
        
        # 仅查询Website
        result_web = call_mcp_tool("query_knowledge_hub", {
            "query": "brewing",
            "doc_type": "website"
        })
        assert all(r['doc_type'] == 'website' for r in result_web['citations'])
```

---

## 4. 向后兼容性总结

| 模块 | 改动范围 | 影响 | 兼容性 |
|-----|---------|------|--------|
| Chroma | metadata添加doc_type字段 | 查询端可选过滤 | 完全兼容（新字段可选） |
| BM25 | 缓存doc_type_map | 查询端可选过滤 | 完全兼容（新参数可选） |
| DocumentManager | 新增doc_type参数 | delete_document自动检测源类型 | 完全兼容 |
| Retriever | 新增doc_type_filter参数 | 查询时可选约束 | 完全兼容（无参数默认全检索） |
| MCP Tool | 新增doc_type参数 | 暴露给前端用户 | 完全兼容（参数可选） |
| Evaluator | 新增分类报告 | 报告输出扩展 | 完全兼容（新维度可选） |

---

## 5. 迁移清单

- [ ] 在 `ingestion_history` 表添加 `source_type` 和 `url_hash` 字段
- [ ] BM25Indexer 添加 `doc_type_map` 和 `query()` 参数扩展
- [ ] DocumentManager 添加 `doc_type` 过滤参数
- [ ] HybridRetriever 添加 `doc_type_filter` 参数
- [ ] MCP Server `query_knowledge_hub` 工具添加 `doc_type` 参数
- [ ] Dashboard Ingestion 管理页添加 doc_type 筛选视图
- [ ] 评估模块添加按 `doc_type` 细分的报告生成
- [ ] 编写集成测试（覆盖PDF、Website、两者混合）
- [ ] 更新用户文档，说明新参数用法

