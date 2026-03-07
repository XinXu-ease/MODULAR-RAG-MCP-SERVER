# Loader 扩展规范 - PDF + Web 爬取双模态支持

> 本文档为 DEV_SPEC.md 的补充，详述如何将仅支持 PDF 的 Loader 扩展为支持 PDF 和网站爬取两种数据源的双模态架构。

## 1. 核心设计原则

### 1.1 框架保持不变
- 保留现有 Pipeline 的分层设计：Loader → Splitter → Transform → Embed → Upsert
- 保留各层的职责划分与抽象接口
- 新增 WebLoader 作为 BaseLoader 的另一个实现，与 PDFLoader 并行存在
- LoaderFactory 根据 source_type 参数选择调用 PDFLoader 或 WebLoader

### 1.2 最小化改动
- Splitter、Transform、Embed、Upsert 等后续模块**无需改动**
- 只需调整 Document 的 metadata 结构定义，为 PDF 和 Website 两种数据源都提供清晰、可扩展的字段设计
- 存储层（Chroma、BM25、SQLite）**无需改动**，只需确保 metadata 兼容性

### 1.3 Metadata 灵活适配
- 引入 `doc_type` 字段区分数据源类型：`pdf` 或 `website`
- 为每种数据源定义必填字段和可选字段
- 后续模块（检索、评估）根据 `doc_type` 灵活处理

---

## 2. Loader 架构设计

### 2.1 BaseLoader 抽象接口

```python
# src/loaders/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class Document:
    """统一的文档对象"""
    id: str                    # 全局唯一文档ID
    source: str               # 数据源表示：PDF路径 或 Website URL
    text: str                 # 规范化Markdown正文
    metadata: Dict[str, Any]  # 灵活的元数据字典
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'source': self.source,
            'text': self.text,
            'metadata': self.metadata
        }


class BaseLoader(ABC):
    """Loader 抽象基类"""
    
    @abstractmethod
    def load(self, source_path: str | None = None, source_url: str | None = None) -> Document:
        """
        将原始数据源加载并解析为统一的 Document 对象。
        
        Args:
            source_path: 本地文件路径（PDFLoader使用）
            source_url: 网站URL（WebLoader使用）
            
        Returns:
            Document: 统一的文档对象
        """
        pass
    
    @abstractmethod
    def validate(self, source: str) -> bool:
        """校验数据源合法性"""
        pass
```

### 2.2 PDFLoader 实现

```python
# src/loaders/pdf_loader.py

from typing import Optional
import hashlib
import os
from datetime import datetime
import markitdown  # 或 unstructured.

class PDFLoader(BaseLoader):
    """PDF 文件解析器"""
    
    def __init__(self, image_storage_dir: str = "data/images"):
        self.image_storage_dir = image_storage_dir
        os.makedirs(image_storage_dir, exist_ok=True)
    
    def load(self, source_path: str) -> Document:
        """
        加载本地 PDF 文件。
        
        流程：
        1. 文件合法性检查
        2. 计算文件哈希（用于去重）
        3. PDF → Markdown 解析
        4. 提取元数据（页码、标题、图像）
        5. 返回 Document 对象
        """
        
        # 1. 校验文件存在
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"PDF file not found: {source_path}")
        
        # 2. 计算文件哈希
        file_hash = self._compute_hash(source_path)
        
        # 3. 获取文件信息
        file_stat = os.stat(source_path)
        file_size = file_stat.st_size
        modification_time = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        
        # 4. PDF → Markdown 解析
        try:
            markdown_text = markitdown.markitdown(source_path)
        except Exception as e:
            raise RuntimeError(f"Failed to parse PDF: {e}")
        
        # 5. 提取标题（简单启发式：第一行H1标题或文件名）
        lines = markdown_text.split('\n')
        title = None
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break
        if not title:
            title = os.path.basename(source_path)
        
        # 6. 提取嵌入图像列表（正则匹配 ![...](image_path) 模式）
        import re
        image_pattern = r'!\[.*?\]\((.*?\.(?:png|jpg|jpeg|gif|webp))\)'
        images = re.findall(image_pattern, markdown_text, re.IGNORECASE)
        
        # 7. 生成文档ID（基于源路径和哈希）
        doc_id = f"pdf_{hashlib.md5(source_path.encode()).hexdigest()}"
        
        # 8. 构建 metadata
        metadata = {
            "doc_type": "pdf",
            "source": source_path,
            "source_hash": file_hash,  # 用于去重
            "file_size": file_size,
            "modification_time": modification_time,
            "title": title,
            "page_count": self._count_pages(markdown_text),
            "images": images,  # 图像路径列表
            "loaded_at": datetime.utcnow().isoformat()
        }
        
        return Document(
            id=doc_id,
            source=source_path,
            text=markdown_text,
            metadata=metadata
        )
    
    def validate(self, source: str) -> bool:
        """校验是否为有效的PDF路径"""
        return source.lower().endswith('.pdf') and os.path.exists(source)
    
    def _compute_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        """计算文件 SHA256 哈希"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _count_pages(self, markdown_text: str) -> int:
        """估计PDF页数（基于markdown中page标记）"""
        import re
        # 假设markitdown会插入 <!--Page X--> 之类的标记
        page_marks = len(re.findall(r'<!--.*?[Pp]age.*?-->', markdown_text))
        return max(page_marks or 1, 1)
```

### 2.3 WebLoader 实现

```python
# src/loaders/web_loader.py

import hashlib
from datetime import datetime
from typing import Dict, Optional, Set
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

class WebLoader(BaseLoader):
    """网站爬取解析器"""
    
    # 白名单网站配置
    WHITELIST = {
        "breville.com": {
            "name": "Breville",
            "paths": ["/recipes", "/tutorials", "/manuals"],
            "page_types": ["recipe", "tutorial", "manual"]
        },
        "baratza.com": {
            "name": "Baratza",
            "paths": ["/brew-guides", "/manuals"],
            "page_types": ["guide", "manual"]
        },
        "fellowproducts.com": {
            "name": "Fellow",
            "paths": ["/brew-guides", "/brew-talks"],
            "page_types": ["guide", "talk"]
        },
        "stumptowncoffee.com": {
            "name": "Stumptown",
            "paths": ["/brew-guides"],
            "page_types": ["guide"]
        },
        "bluebottlecoffee.com": {
            "name": "Blue Bottle",
            "paths": ["/brew-guides"],
            "page_types": ["guide"]
        },
        "hariousa.com": {
            "name": "Hario USA",
            "paths": ["/recipes", "/guides"],
            "page_types": ["recipe", "guide"]
        },
        "aeropress.com": {
            "name": "AeroPress",
            "paths": ["/recipes", "/how-to"],
            "page_types": ["recipe", "how-to"]
        },
        "chemexcoffeemaker.com": {
            "name": "Chemex",
            "paths": ["/brew"],
            "page_types": ["brew"]
        }
    }
    
    def __init__(self, cache_days: int = 7, timeout: int = 10):
        """
        初始化WebLoader。
        
        Args:
            cache_days: 缓存天数（超过该天数的URL需重新爬取）
            timeout: HTTP请求超时（秒）
        """
        self.cache_days = cache_days
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def load(self, source_url: str) -> Document:
        """
        爬取网站页面。
        
        流程：
        1. URL白名单检验
        2. HTTP请求获取页面
        3. HTML清理与Markdown转换
        4. Recipe/Guide识别与参数提取
        5. 返回 Document 对象
        """
        
        # 1. 白名单检验
        if not self.validate(source_url):
            raise ValueError(f"URL 不在白名单中: {source_url}")
        
        # 2. HTTP 请求
        try:
            response = self.session.get(source_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch URL: {e}")
        
        # 3. HTML 解析与清理
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 移除脚本、样式、导航、页脚等干扰元素
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', '.sidebar', '.ads']):
            tag.decompose()
        
        # 提取主要内容（启发式：main/article/content 标签或最大文本块）
        main_content = self._extract_main_content(soup)
        
        # 转换为 Markdown（简单的HTML→Markdown转换）
        markdown_text = self._html_to_markdown(main_content)
        
        # 4. 页面类型识别与参数提取
        page_type = self._detect_page_type(markdown_text, source_url)
        recipe_params = None
        if page_type == "recipe":
            recipe_params = self._extract_recipe_params(markdown_text, soup)
        
        # 5. 元数据构建
        title = soup.title.string if soup.title else "Untitled"
        website_name = self._get_website_name(source_url)
        url_hash = hashlib.sha256(source_url.encode()).hexdigest()
        
        # 提取嵌入图像列表
        images = [img.get('src', '') for img in soup.find_all('img')]
        images = [img for img in images if img]  # 过滤空值
        
        doc_id = f"web_{url_hash[:12]}"
        
        metadata = {
            "doc_type": "website",
            "source": source_url,
            "source_hash": url_hash,  # 用于去重
            "website_name": website_name,
            "page_type": page_type,
            "title": title,
            "fetched_at": datetime.utcnow().isoformat(),
            "recipe_params": recipe_params,  # 仅当page_type='recipe'时存在
            "images": images,
            "response_code": response.status_code
        }
        
        return Document(
            id=doc_id,
            source=source_url,
            text=markdown_text,
            metadata=metadata
        )
    
    def validate(self, source: str) -> bool:
        """校验URL是否在白名单中"""
        try:
            parsed = urlparse(source)
            domain = parsed.netloc.replace('www.', '')
            
            # 检查是否在白名单中
            for whitelisted_domain in self.WHITELIST.keys():
                if domain == whitelisted_domain or domain.endswith('.' + whitelisted_domain):
                    # 检查路径是否匹配
                    path = parsed.path.lower()
                    allowed_paths = self.WHITELIST[whitelisted_domain]['paths']
                    if any(allowed_path.lower() in path for allowed_path in allowed_paths):
                        return True
            
            return False
        except Exception:
            return False
    
    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """提取页面主要内容区域"""
        # 优先查找常见的主要内容标签
        for selector in ['main', 'article[role="main"]', '[role="main"]', '.content', '#content']:
            element = soup.select_one(selector)
            if element:
                return element
        
        # 降级：使用最大的文本块
        # 简化起见，这里返回整个body
        return soup.body or soup
    
    def _html_to_markdown(self, html_content) -> str:
        """简单的HTML→Markdown转换"""
        # 这里可以使用 html2text 或 markdownify 库
        # 简化实现：保留文本内容和基本格式
        text_content = html_content.get_text(separator='\n', strip=True)
        return text_content
    
    def _detect_page_type(self, markdown_text: str, url: str) -> str:
        """检测页面类型（recipe/guide/manual/other）"""
        text_lower = markdown_text.lower()
        url_lower = url.lower()
        
        # 基于关键词和URL路径进行分类
        if any(kw in text_lower or kw in url_lower for kw in ['recipe', 'how to', 'instructions', 'ingredients']):
            return "recipe"
        elif any(kw in text_lower or kw in url_lower for kw in ['guide', 'brew']):
            return "guide"
        elif 'manual' in text_lower or 'manual' in url_lower:
            return "manual"
        else:
            return "other"
    
    def _extract_recipe_params(self, markdown_text: str, soup: BeautifulSoup) -> Optional[Dict]:
        """提取Recipe结构化参数"""
        params = {}
        
        # 启发式规则：查找常见的参数模式
        patterns = {
            "servings": r"(?:servings?|yield|makes?)[:\s]+(\d+)",
            "prep_time_minutes": r"(?:prep\s)?(?:time|duration)[:\s]+(\d+)\s*(?:min|minutes?)",
            "brew_time_minutes": r"(?:brew|steep|brewing?)\s*(?:time|duration)[:\s]+(\d+)\s*(?:min|minutes?)",
            "water_temperature_celsius": r"(?:water\s)?(?:temp|temperature)[:\s]+(\d+)°?[Cc]",
            "coffee_grams": r"(?:coffee|beans?|grounds?)[:\s]+(\d+)g(?:rams?)?",
            "water_grams": r"(?:water)[:\s]+(\d+)g(?:rams?)?|(?:water)[:\s]+(\d+)\s*ml"
        }
        
        for param_name, pattern in patterns.items():
            match = re.search(pattern, markdown_text, re.IGNORECASE)
            if match:
                try:
                    params[param_name] = int(match.group(1))
                except (ValueError, IndexError):
                    pass
        
        return params if params else None
    
    def _get_website_name(self, url: str) -> str:
        """从URL提取网站名"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        
        for whitelisted_domain, config in self.WHITELIST.items():
            if domain == whitelisted_domain or domain.endswith('.' + whitelisted_domain):
                return config.get('name', domain)
        
        return domain
```

### 2.4 LoaderFactory

```python
# src/loaders/factory.py

from typing import Literal
from .base import BaseLoader
from .pdf_loader import PDFLoader
from .web_loader import WebLoader

class LoaderFactory:
    """Loader 工厂类，根据数据源类型选择相应的加载器"""
    
    @staticmethod
    def get_loader(source_type: Literal["pdf", "website"]) -> BaseLoader:
        """
        获取对应类型的Loader实例。
        
        Args:
            source_type: "pdf" 或 "website"
            
        Returns:
            BaseLoader子类实例
        """
        if source_type == "pdf":
            return PDFLoader()
        elif source_type == "website":
            return WebLoader()
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
```

---

## 3. Pipeline 集成设计

### 3.1 IngestionPipeline 修改

在现有的 `IngestionPipeline` 中添加对 source_type 的支持：

```python
# src/ingestion/pipeline.py - 修改示意

class IngestionPipeline:
    """数据摄取管道"""
    
    def run(
        self,
        source_type: Literal["pdf", "website"],
        source_path: str | None = None,
        source_url: str | None = None,
        collection: str = "default",
        on_progress: Callable | None = None
    ) -> IngestionResult:
        """
        执行完整的摄取流水线。
        
        Args:
            source_type: "pdf" 或 "website"
            source_path: PDF文件路径（当source_type="pdf"时必填）
            source_url: 网站URL（当source_type="website"时必填）
            collection: 存储集合名
            on_progress: 进度回调函数
            
        Returns:
            IngestionResult
        """
        
        # 1. Loader 阶段
        loader = LoaderFactory.get_loader(source_type)
        
        if source_type == "pdf":
            if not source_path:
                raise ValueError("source_path required for PDF source")
            document = loader.load(source_path=source_path)
        elif source_type == "website":
            if not source_url:
                raise ValueError("source_url required for website source")
            document = loader.load(source_url=source_url)
        else:
            raise ValueError(f"Unsupported source_type: {source_type}")
        
        # 2. 去重检查（使用source_hash）
        if self._is_duplicate(document.metadata.get("source_hash")):
            return IngestionResult(status="skipped", reason="Duplicate content")
        
        # 3. 后续流程保持不变：Splitter → Transform → Embed → Upsert
        chunks = self._splitter.split(document)
        enriched_chunks = self._transform(chunks)
        embeddings = self._embed(enriched_chunks)
        self._upsert(embeddings, collection)
        
        return IngestionResult(status="success", chunk_count=len(chunks))
    
    def _is_duplicate(self, source_hash: str) -> bool:
        """检查文件/URL是否已处理过"""
        # 从ingestion_history表查询
        pass
```

---

## 4. Metadata 字段规范

### 4.1 通用必填字段

所有Document都必须包含：

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `doc_type` | str | `"pdf"` 或 `"website"` |
| `source` | str | PDF路径 或 Website URL |
| `title` | str | 文档标题 |
| `source_hash` | str | SHA256哈希，用于去重 |
| `images` | List[str] | 页内图像列表 |

### 4.2 PDF特有字段

| 字段名 | 类型 | 说明 | 必填 |
|-------|------|------|-----|
| `file_size` | int | 文件大小（字节） | 是 |
| `modification_time` | str | 文件修改时间（ISO格式） | 是 |
| `page_count` | int | 总页数 | 是 |
| `page_list` | List[int] | 包含的页码列表（可选） | 否 |

### 4.3 Website特有字段

| 字段名 | 类型 | 说明 | 必填 |
|-------|------|------|-----|
| `website_name` | str | 网站显示名（从白名单映射） | 是 |
| `page_type` | str | `"recipe"/"guide"/"manual"/"other"` | 是 |
| `fetched_at` | str | 抓取时间（ISO格式） | 是 |
| `recipe_params` | Dict | 提取的参数（份量、温度等） | 否 |
| `response_code` | int | HTTP响应码 | 否 |

---

## 5. 存储层适配

### 5.1 ingestion_history 表扩展

原表结构已支持通用哈希，无需修改。但记录新增两个字段以区分来源：

```sql
ALTER TABLE ingestion_history ADD COLUMN source_type TEXT CHECK(source_type IN ('pdf', 'website'));
ALTER TABLE ingestion_history ADD COLUMN url_hash TEXT;  -- Website URL的哈希
```

### 5.2 Chroma metadata 兼容性

Chroma支持灵活的metadata字典存储，现有实现无需改动。后续查询时可按 `doc_type` 过滤：

```python
# 例：仅检索PDF文档
results = chroma_collection.query(
    embedding=query_embedding,
    where={"doc_type": {"$eq": "pdf"}},
    n_results=10
)
```

### 5.3 BM25 索引兼容性

BM25索引器同样无需改动，接受通用的Document对象。

---

## 6. 质量评估与测试适配

### 6.1 golden_test_set 扩展

评估测试集应包含两种数据源的样本：

```json
[
    {
        "query": "How to brew AeroPress?",
        "source_docs": [
            {
                "id": "pdf_001",
                "doc_type": "pdf",
                "source": "documents/brewing_guide.pdf",
                "expected_relevance": 0.9
            },
            {
                "id": "web_001",
                "doc_type": "website",
                "source": "https://aeropress.com/recipes",
                "expected_relevance": 0.95
            }
        ]
    }
]
```

### 6.2 评估指标调整

- 现有指标（Hit Rate, MRR, Faithfulness等）无需改动
- 可新增按 `doc_type` 分组的评估报告，查看两阶数据源的性能差异

---

## 7. 实施清单

- [ ] 实现 `BaseLoader` 抽象接口
- [ ] 实现 `PDFLoader`（包括文件哈希计算、Markdown转换、元数据抽取）
- [ ] 实现 `WebLoader`（包括白名单验证、HTML爬取、Recipe识别、参数提取）
- [ ] 实现 `LoaderFactory`
- [ ] 修改 `IngestionPipeline` 以支持 `source_type` 参数
- [ ] 修改 `ingestion_history` 表以记录source_type和url_hash
- [ ] 更新 `DocumentManager.delete_document()` 以支持按source_type删除
- [ ] 添加单元测试：PDFLoader / WebLoader / 去重逻辑
- [ ] 添加集成测试：端到端Pipeline测试
- [ ] 扩展 golden_test_set，加入Website样本
- [ ] 更新 Dashboard，在Ingestion管理页展示source_type筛选

---

## 8. 向后兼容性

- Pipeline 默认 `source_type="pdf"`，保持现有使用逻辑
- 新增 `source_type="website"` 参数为可选
- Document 内部结构完全兼容，后续的 Splitter/Transform/Embed/评估 等模块**零改动**

