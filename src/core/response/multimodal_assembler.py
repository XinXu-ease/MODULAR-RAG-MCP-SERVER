"""Multimodal response assembler汇编: Handle text + image content."""

import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.types import RetrievalResult

logger = logging.getLogger(__name__)

# Image MIME types
MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

# Default image base directory
DEFAULT_IMAGE_DIR = "data/images"


class MultimodalAssembler:
    """
    组装多模态响应内容。
    
    将包含图片引用的检索结果转换为 MCP 协议格式的多模态内容，
    包括文本和 base64 编码的图像。
    """

    def __init__(self, image_base_dir: Optional[str] = None):
        """
        初始化多模态组装器。

        Args:
            image_base_dir: 图像文件基础目录（默认：data/images）
        """
        self.image_base_dir = image_base_dir or DEFAULT_IMAGE_DIR
        self._ensure_image_dir_exists()

    def _ensure_image_dir_exists(self) -> None:
        """确保图像目录存在（如果不存在则创建）。"""
        try:
            Path(self.image_base_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create image directory {self.image_base_dir}: {e}")

    def assemble(self, retrieval_results: List[RetrievalResult]) -> List[Dict[str, Any]]:
        """
        组装检索结果为 MCP 多模态内容。

        Args:
            retrieval_results: 检索结果列表

        Returns:
            MCP 协议格式的 content 数组 (base64 编码的图像和文本）
        """
        content = []

        for i, result in enumerate(retrieval_results):
            # 添加文本内容
            text_content = {
                "type": "text",
                "text": result.content,
            }
            content.append(text_content)

            # 处理图像引用
            if result.image_refs:
                for image_id in result.image_refs:
                    image_content = self._load_image_as_content(image_id)
                    if image_content:
                        content.append(image_content)
                    else:
                        logger.warning(f"Could not load image: {image_id}")

        return content

    def _load_image_as_content(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        加载图像并转换为 MCP ImageContent 格式。

        Args:
            image_id: 图像 ID（可以是文件名或路径）

        Returns:
            MCP 格式的 ImageContent，如果加载失败返回 None
        """
        # 构建图像文件路径
        image_path = self._resolve_image_path(image_id)

        if not image_path or not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None

        try:
            # 读取图像文件
            with open(image_path, "rb") as f:
                image_data = f.read()

            # 转换为 base64
            base64_data = base64.b64encode(image_data).decode("utf-8")

            # 获取 MIME 类型
            file_ext = Path(image_path).suffix.lower()
            mime_type = MIME_TYPES.get(file_ext, "application/octet-stream")

            # 构建 MCP ImageContent
            return {
                "type": "image",
                "data": base64_data,
                "mimeType": mime_type,
            }

        except Exception as e:
            logger.error(f"Failed to load image {image_id}: {e}")
            return None

    def _resolve_image_path(self, image_id: str) -> Optional[str]:
        """
        解析图像 ID 为文件路径。

        Args:
            image_id: 图像 ID

        Returns:
            解析后的文件路径，如果无效返回 None
        """
        if not image_id:
            return None

        # 如果 image_id 是相对路径，拼接到 image_base_dir
        if not os.path.isabs(image_id):
            full_path = os.path.join(self.image_base_dir, image_id)
        else:
            full_path = image_id

        # 安全检查：防止路径遍历攻击
        try:
            full_path = os.path.abspath(full_path)
            image_base_abs = os.path.abspath(self.image_base_dir)

            # 确保路径在 image_base_dir 内
            if not full_path.startswith(image_base_abs):
                logger.warning(f"Image path outside base directory: {full_path}")
                return None

            return full_path
        except Exception as e:
            logger.error(f"Invalid image path {image_id}: {e}")
            return None

    def assemble_with_fallback(
        self, retrieval_results: List[RetrievalResult]
    ) -> List[Dict[str, Any]]:
        """
        组装内容，跳过加载失败的图像（不抛异常）。

        Args:
            retrieval_results: 检索结果列表

        Returns:
            MCP 协议格式的 content 数组
        """
        try:
            return self.assemble(retrieval_results)
        except Exception as e:
            logger.error(f"Error assembling multimodal content: {e}")
            # 返回纯文本内容（降级）
            return [
                {"type": "text", "text": result.content} for result in retrieval_results
            ]

    @staticmethod
    def is_mime_type_valid(mime_type: str) -> bool:
        """
        检查 MIME 类型是否有效。

        Args:
            mime_type: MIME 类型字符串

        Returns:
            True 如果是有效的图像 MIME 类型
        """
        return mime_type in MIME_TYPES.values()

    @staticmethod
    def get_supported_extensions() -> List[str]:
        """
        获取支持的文件扩展名列表。

        Returns:
            支持的扩展名列表
        """
        return list(MIME_TYPES.keys())
