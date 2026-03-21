import hashlib
import re
from datetime import datetime, timezone
from html import unescape #把 HTML 实体（如 &amp;）转成正常字符。
from typing import Any, Optional
from urllib.parse import urlparse #拆解 URL（scheme/domain/path）

try:
    import requests
except ImportError:  # pragma: no cover - dependency availability varies
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - dependency availability varies
    BeautifulSoup = None

from src.core.types import Document

from .base import BaseLoader


class WebLoader(BaseLoader):
    """Load whitelisted web pages into normalized documents."""

    WHITELIST = {
        "breville.com": {
            "name": "Breville",
            "paths": ["/recipes", "/tutorials", "/manuals"],
        },
        "baratza.com": {
            "name": "Baratza",
            "paths": ["/brew-guides", "/manuals"],
        },
        "fellowproducts.com": {
            "name": "Fellow",
            "paths": ["/brew-guides", "/brew-talks"],
        },
        "stumptowncoffee.com": {
            "name": "Stumptown",
            "paths": ["/brew-guides"],
        },
        "bluebottlecoffee.com": {
            "name": "Blue Bottle",
            "paths": ["/brew-guides"],
        },
        "hariousa.com": {
            "name": "Hario USA",
            "paths": ["/recipes", "/guides"],
        },
        "aeropress.com": {
            "name": "AeroPress",
            "paths": ["/recipes", "/how-to"],
        },
        "chemexcoffeemaker.com": {
            "name": "Chemex",
            "paths": ["/brew"],
        },
    }

    def __init__(self, timeout: int = 10, session: Optional[Any] = None):
        self.timeout = timeout
        self.session = session or self._build_session() #如果没有传入 session，就创建一个新的 requests.Session() 实例。
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            }
        ) #设置一个常见的 User-Agent，模拟浏览器访问，避免被服务器拒绝。

    def load(self, source: str) -> Document:
        if not self.validate(source):
            raise ValueError(f"URL is not in the allowed whitelist: {source}")

        response = self.session.get(source, timeout=self.timeout)
        response.raise_for_status()

        html = response.text
        text = self._html_to_markdown(html)
        title = self._extract_title(html) or source
        metadata = {
            "doc_type": "website",
            "source": source,
            "source_hash": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "title": title,
            "website_name": self._website_name(source),
            "page_type": self._page_type(source),
            "images": self._extract_images(html),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        return Document(
            id=f"web_{hashlib.md5(source.encode('utf-8')).hexdigest()}",
            text=text,
            metadata=metadata,
        )

    def validate(self, source: str) -> bool:
        parsed = urlparse(source)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False

        domain = parsed.netloc.lower().removeprefix("www.") #统一域名格式，去掉 www.
        domain_config = self.WHITELIST.get(domain)
        if domain_config is None:
            return False

        path = parsed.path or "/"
        return any(path.startswith(prefix) for prefix in domain_config["paths"])

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        if BeautifulSoup is None:
            return WebLoader._html_to_markdown_without_bs4(html)

        soup = BeautifulSoup(html, "html.parser") #解析 HTML

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose() #删除这些噪声标签及其内容

        parts: list[str] = []
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        if title:
            parts.append(f"# {title}") #把标题作为一级标题添加到 parts 列表

        body = soup.body or soup #如果没有 body 标签，就从整个文档开始提取文本
        for node in body.find_all(["h1", "h2", "h3", "p", "li"]): #只提取这些标签的文本
            text = node.get_text(" ", strip=True) #把标签内的文本提取出来
            if not text:
                continue
            if node.name == "h1":
                parts.append(f"# {text}")
            elif node.name == "h2":
                parts.append(f"## {text}")
            elif node.name == "h3":
                parts.append(f"### {text}")
            elif node.name == "li":
                parts.append(f"- {text}")
            else:
                parts.append(text) #把提取的文本根据标签类型添加到 parts 列表，标题加上 Markdown 语法，段落直接添加

        normalized = "\n\n".join(parts)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        if not normalized:
            raise RuntimeError("No readable text extracted from web page.")
        return normalized

    @staticmethod
    def _extract_title(html: str) -> Optional[str]:
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser") #解析 HTML
            if soup.title and soup.title.string:
                return soup.title.string.strip()
            heading = soup.find("h1")
            if heading:
                return heading.get_text(" ", strip=True)
            return None

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL) #用正则表达式提取 title 标签的内容
        if title_match:
            return WebLoader._clean_text(title_match.group(1))
        heading_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
        if heading_match:  #如果没有 title 标签，就尝试提取第一个 h1 标签的内容作为标题
            return WebLoader._clean_text(heading_match.group(1))
        return None

    @staticmethod
    def _extract_images(html: str) -> list[str]:
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            return [img.get("src", "") for img in soup.find_all("img") if img.get("src")] #提取所有 img 标签的 src 属性，src 是 HTML <img> 标签的标准属性，表示图片地址。
        return re.findall(r'<img[^>]+src=["\'](.*?)["\']', html, flags=re.IGNORECASE) #用正则表达式提取所有 img 标签的 src 属性

    def _website_name(self, source: str) -> str:
        domain = urlparse(source).netloc.lower().removeprefix("www.")
        return self.WHITELIST[domain]["name"]

    @staticmethod
    def _page_type(source: str) -> str:
        path = urlparse(source).path.lower()
        if "recipe" in path:
            return "recipe"
        if "guide" in path:
            return "guide"
        if "manual" in path:
            return "manual"
        if "tutorial" in path:
            return "tutorial"
        return "other"

    @staticmethod
    def _build_session() -> Any:
        if requests is None:
            raise RuntimeError(
                "requests is required for live web loading. Install it with `pip install requests`."
            )
        return requests.Session()

    @staticmethod
    def _html_to_markdown_without_bs4(html: str) -> str:
        cleaned = re.sub(
            r"<(script|style|noscript)\b.*?>.*?</\1>",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        parts: list[str] = []

        title = WebLoader._extract_title(cleaned)
        if title:
            parts.append(f"# {title}")

        block_pattern = re.compile(
            r"<(h1|h2|h3|p|li)\b[^>]*>(.*?)</\1>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        for tag, content in block_pattern.findall(cleaned):
            text = WebLoader._clean_text(content)
            if not text:
                continue
            tag_name = tag.lower()
            if tag_name == "h1":
                parts.append(f"# {text}")
            elif tag_name == "h2":
                parts.append(f"## {text}")
            elif tag_name == "h3":
                parts.append(f"### {text}")
            elif tag_name == "li":
                parts.append(f"- {text}")
            else:
                parts.append(text)

        normalized = "\n\n".join(parts)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        if not normalized:
            raise RuntimeError("No readable text extracted from web page.")
        return normalized

    @staticmethod
    def _clean_text(value: str) -> str:
        no_tags = re.sub(r"<[^>]+>", " ", value)
        return re.sub(r"\s+", " ", unescape(no_tags)).strip()
