"""RagasEvaluator 单元测试。"""

import pytest
from unittest.mock import Mock


class TestRagasEvaluator:
    """测试 RagasEvaluator 类。"""

    def test_evaluate_returns_metrics(self):
        """测试 evaluate() 返回包含 faithfulness/answer_relevancy 的指标。"""
        from src.observability.evaluation.ragas_evaluator import RagasEvaluator
        
        mock_faithfulness = Mock()
        mock_faithfulness.score_single.return_value = 0.85
        
        mock_answer_relevancy = Mock()
        mock_answer_relevancy.score_single.return_value = 0.92
        
        mock_context_precision = Mock()
        mock_context_precision.score_single.return_value = 0.78

        evaluator = RagasEvaluator.__new__(RagasEvaluator)
        evaluator.llm = None
        evaluator._metrics_loaded = True
        evaluator.faithfulness = mock_faithfulness
        evaluator.answer_relevancy = mock_answer_relevancy
        evaluator.context_precision = mock_context_precision

        # 准备输入
        query = "What is Python?"
        chunks = [
            "Python is a high-level programming language.",
            "It was created by Guido van Rossum in 1991.",
        ]
        answer = "Python is a programming language."

        # 执行评估
        metrics = evaluator.evaluate(query, chunks, answer)

        # 验证结果包含必要字段
        assert "faithfulness" in metrics
        assert "answer_relevancy" in metrics
        assert "context_precision" in metrics
        
        # 验证指标值
        assert metrics["faithfulness"] == 0.85
        assert metrics["answer_relevancy"] == 0.92
        assert metrics["context_precision"] == 0.78

    def test_evaluate_with_dict_chunks(self):
        """测试 evaluate() 处理字典类型的 chunks。"""
        from src.observability.evaluation.ragas_evaluator import RagasEvaluator
        
        mock_faithfulness = Mock()
        mock_faithfulness.score_single.return_value = 0.80
        
        mock_answer_relevancy = Mock()
        mock_answer_relevancy.score_single.return_value = 0.90
        
        mock_context_precision = Mock()
        mock_context_precision.score_single.return_value = 0.75

        evaluator = RagasEvaluator.__new__(RagasEvaluator)
        evaluator.llm = None
        evaluator._metrics_loaded = True
        evaluator.faithfulness = mock_faithfulness
        evaluator.answer_relevancy = mock_answer_relevancy
        evaluator.context_precision = mock_context_precision

        # 测试字典类型 chunks（包含 content 字段）
        chunks = [
            {"content": "Python is a programming language.", "doc_id": "001"},
            {"content": "It's used for web development.", "doc_id": "002"},
        ]
        
        metrics = evaluator.evaluate(
            "What is Python?",
            chunks,
            "Python is used for programming.",
        )

        assert metrics["faithfulness"] == 0.80
        assert metrics["answer_relevancy"] == 0.90

    def test_evaluate_with_ground_truth(self):
        """测试 evaluate() 处理包含 ground_truth 的场景。"""
        from src.observability.evaluation.ragas_evaluator import RagasEvaluator
        
        mock_faithfulness = Mock()
        mock_faithfulness.score_single.return_value = 0.88
        
        mock_answer_relevancy = Mock()
        mock_answer_relevancy.score_single.return_value = 0.95
        
        mock_context_precision = Mock()
        mock_context_precision.score_single.return_value = 0.82

        evaluator = RagasEvaluator.__new__(RagasEvaluator)
        evaluator.llm = None
        evaluator._metrics_loaded = True
        evaluator.faithfulness = mock_faithfulness
        evaluator.answer_relevancy = mock_answer_relevancy
        evaluator.context_precision = mock_context_precision
            
        chunks = ["Python is a programming language."]
        ground_truth = "Python is a high-level programming language."

        metrics = evaluator.evaluate(
            "What is Python?",
            chunks,
            "Python is a programming language.",
            ground_truth=ground_truth,
        )

        # 验证 mock 被调用时包含 ground_truth
        call_args = mock_faithfulness.score_single.call_args
        assert "ground_truth" in call_args[0][0]
        assert call_args[0][0]["ground_truth"] == ground_truth

    def test_evaluate_with_partial_failures(self):
        """测试当某个指标计算失败时的降级行为。"""
        from src.observability.evaluation.ragas_evaluator import RagasEvaluator
        
        mock_faithfulness = Mock()
        mock_faithfulness.score_single.side_effect = Exception("LLM call failed")
        
        mock_answer_relevancy = Mock()
        mock_answer_relevancy.score_single.return_value = 0.92
        
        mock_context_precision = Mock()
        mock_context_precision.score_single.return_value = 0.78

        evaluator = RagasEvaluator.__new__(RagasEvaluator)
        evaluator.llm = None
        evaluator._metrics_loaded = True
        evaluator.faithfulness = mock_faithfulness
        evaluator.answer_relevancy = mock_answer_relevancy
        evaluator.context_precision = mock_context_precision
            
        chunks = ["Python is a programming language."]
        metrics = evaluator.evaluate(
            "What is Python?",
            chunks,
            "Python is a programming language.",
        )

        # 验证返回结果包含所有字段，失败的设为 None
        assert metrics["faithfulness"] is None
        assert metrics["answer_relevancy"] == 0.92
        assert metrics["context_precision"] == 0.78

    def test_extract_context_with_mixed_types(self):
        """测试 _extract_context() 处理混合类型的 chunks。"""
        from src.observability.evaluation.ragas_evaluator import RagasEvaluator
        
        evaluator = RagasEvaluator.__new__(RagasEvaluator)

        # 混合类型的 chunks：字符串、dict、object
        chunks = [
            "Direct string chunk",
            {"content": "Dict with content key"},
            {"text": "Dict with text key"},
            {"chunk": "Dict with chunk key"},
        ]

        context = evaluator._extract_context(chunks)

        # 验证所有 chunks 都被包含在上下文中
        assert "Direct string chunk" in context
        assert "Dict with content key" in context
        assert "Dict with text key" in context
        assert "Dict with chunk key" in context
        
    def test_extract_context_with_strings(self):
        """测试 _extract_context() 处理纯字符串列表。"""
        from src.observability.evaluation.ragas_evaluator import RagasEvaluator
        
        evaluator = RagasEvaluator.__new__(RagasEvaluator)
        
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        context = evaluator._extract_context(chunks)
        
        # 验证所有 chunks 用换行符连接
        assert context == "Chunk 1\nChunk 2\nChunk 3"
