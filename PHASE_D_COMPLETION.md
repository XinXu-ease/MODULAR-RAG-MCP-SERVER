# 阶段 D 完成总结 - Retrieval MVP

**完成时间**: 2026-03-21  
**阶段状态**: 已完成 MVP 主链路

---

## 本次完成内容

- `DenseRetriever`：接入 embedding + vector store，完成向量召回。
- `SparseRetriever`：接入 BM25 倒排索引，并补齐按 `chunk_id` 回查正文/元数据。
- `HybridSearch`：实现 Dense + Sparse 融合，采用 RRF 排序，并支持可选 rerank。
- `scripts/query.py`：新增查询脚本入口，支持 `--query --top-k --no-rerank --verbose`。
- `tests/unit/core/test_query_engine.py`：补充 Retrieval 层单元测试。

---

## 关键改动

- 向量存储抽象新增 `get_by_ids()`，用于 Sparse 检索后的结果回填。
- `src/core/query_engine/` 从空目录补齐为可运行检索模块。
- 查询结果统一输出为 `QueryResult` / `RetrievalResult`，与现有核心类型契约对齐。
- 检索链路内已预留 Trace 记录，便于后续 Phase F 继续打点增强。

---

## 当前结论

项目现在已经具备本地检索 MVP：

1. 先执行 `scripts/ingest.py` 完成本地索引构建。
2. 再执行 `scripts/query.py` 可直接做 Hybrid Retrieval。
3. Dense/Sparse/Fusion/Rerank 的阶段结果已经在代码层完成解耦，后续可继续挂 MCP tools、Trace 持久化与 Dashboard。

---

## 验收说明

- 已补齐 Retrieval 相关测试文件。
- 当前终端中的 Python 命令执行被代理层静默拦截，我无法在此会话里拿到实际 `pytest` 输出，因此这次未完成自动化验证回执。
