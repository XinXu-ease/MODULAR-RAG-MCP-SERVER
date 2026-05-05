"""Ragas 评估器实现，基于 Ragas 框架进行 RAG 质量评估。"""

from typing import Any, Dict, List, Optional


class RagasEvaluator:
    """基于 Ragas 框架的评估器。
    
    支持的指标：
    - faithfulness：生成答案与检索上下文的一致性
    - answer_relevancy：生成答案与查询的相关性
    - context_precision：检索上下文与查询的相关性
    """

    def __init__(self, llm: Optional[Any] = None):
        """初始化 Ragas 评估器。
        
        Args:
            llm: 用于评估的 LLM 实例。如果为 None，使用默认 LLM。
        
        Raises:
            ImportError: 如果 ragas 未安装
        """
        self.llm = llm
        self._metrics_loaded = False
        self.faithfulness = None
        self.answer_relevancy = None
        self.context_precision = None
        self._load_metrics()

    def _load_metrics(self) -> None:
        """延迟加载 Ragas 指标对象。"""
        if self._metrics_loaded:
            return
            
        try:
            from ragas.metrics import (
                answer_relevancy,
                context_precision,
                faithfulness,
            )

            self.answer_relevancy = answer_relevancy
            self.context_precision = context_precision
            self.faithfulness = faithfulness
            self._metrics_loaded = True
            
        except ImportError as e:
            raise ImportError(
                "ragas 库未安装。请运行: pip install ragas"
            ) from e

    def evaluate(
        self,
        query: str,
        retrieved_chunks: List[Any],
        generated_answer: str,
        ground_truth: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """执行评估并返回指标字典。
        
        Args:
            query: 用户查询
            retrieved_chunks: 检索到的文档块列表
            generated_answer: 生成的答案
            ground_truth: 真实答案（可选）
        
        Returns:
            包含评估指标的字典，例如：
            {
                "faithfulness": 0.85,
                "answer_relevancy": 0.92,
                "context_precision": 0.78
            }
        """
        try:
            # 将 chunks 转换为文本形式
            context = self._extract_context(retrieved_chunks)
            
            # 创建 Ragas 评估输入
            sample = {
                "question": query,
                "answer": generated_answer,
                "contexts": [context],
                "ground_truth": ground_truth,
            }
            
            metrics = {}
            
            # 计算 Faithfulness
            try:
                if self.llm:
                    faithfulness_score = self.faithfulness.score_single(sample, llm=self.llm)
                else:
                    faithfulness_score = self.faithfulness.score_single(sample)
                metrics["faithfulness"] = faithfulness_score
            except Exception as e:
                # 如果单个指标失败，记录但继续
                metrics["faithfulness"] = None
                
            # 计算 Answer Relevancy
            try:
                if self.llm:
                    relevancy_score = self.answer_relevancy.score_single(sample, llm=self.llm)
                else:
                    relevancy_score = self.answer_relevancy.score_single(sample)
                metrics["answer_relevancy"] = relevancy_score
            except Exception as e:
                metrics["answer_relevancy"] = None
                
            # 计算 Context Precision
            try:
                if self.llm:
                    precision_score = self.context_precision.score_single(sample, llm=self.llm)
                else:
                    precision_score = self.context_precision.score_single(sample)
                metrics["context_precision"] = precision_score
            except Exception as e:
                metrics["context_precision"] = None
            
            return metrics
            
        except Exception as e:
            raise RuntimeError(f"Ragas 评估过程中出错: {str(e)}") from e

    def _extract_context(self, retrieved_chunks: List[Any]) -> str:
        """从检索块列表中提取上下文文本。
        
        Args:
            retrieved_chunks: 检索块列表，每个块可能是：
                - 字符串
                - 包含 'content' 字段的字典
                - 包含 'text' 字段的字典
                - 其他对象（尝试 str() 转换）
        
        Returns:
            合并后的上下文文本
        """
        contexts = []
        for chunk in retrieved_chunks:
            if isinstance(chunk, str):
                contexts.append(chunk)
            elif isinstance(chunk, dict):
                # 尝试多个可能的键名
                if "content" in chunk:
                    contexts.append(str(chunk["content"]))
                elif "text" in chunk:
                    contexts.append(str(chunk["text"]))
                elif "chunk" in chunk:
                    contexts.append(str(chunk["chunk"]))
                else:
                    # 作为后备，转换整个字典
                    contexts.append(str(chunk))
            else:
                # 尝试字符串转换
                contexts.append(str(chunk))
        
        return "\n".join(contexts)

