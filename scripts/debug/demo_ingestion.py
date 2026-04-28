#!/usr/bin/env python3
"""
可运行的摄取演示脚本 - 直接摄取 PDF
"""

import sys
from pathlib import Path

# 配置路径
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.pipeline import IngestionPipeline


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     运行 PDF 摄取                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # ==================== PATH 变量在这里设置 ====================
    # 🔴 关键：只需要设置 PDF 路径，collection 使用默认名
    pdf_path = "data/pdfs/"              # ← 修改这里指向你的 PDF 目录
    # ============================================================
    
    # 默认集合名
    collection_name = "ingested_documents"
    
    print(f"📂 摄取路径: {pdf_path}")
    print(f"📋 集合名: {collection_name}")
    print("=" * 80)
    
    # 初始化摄取管道
    pipeline = IngestionPipeline()
    
    # 处理路径（支持 URL / 单个文件 / 目录）
    if pdf_path.startswith("http://") or pdf_path.startswith("https://"):
        # Web 摄取
        sources = [pdf_path]
    else:
        # 本地文件摄取
        path = Path(pdf_path)
        if path.is_file():
            sources = [str(path)]
        elif path.is_dir():
            # 目录：递归找所有 PDF
            sources = sorted([str(p) for p in path.rglob("*.pdf")])
        else:
            print(f"❌ 路径不存在: {pdf_path}")
            return 1
    
    if not sources:
        print("❌ 没有找到要摄取的文件")
        return 1
    
    print(f"📝 找到 {len(sources)} 个文件要摄取:\n")
    for src in sources:
        print(f"   • {src}")
    print("\n开始摄取...\n")
    
    # 摄取每个源
    success = True
    for source in sources:
        result = pipeline.run(source=source, collection=collection_name, force=False)
        if result.success:
            print(f"✅ OK  {source}")
            print(f"   └─ chunks={result.metrics.total_chunks} skipped={result.metrics.skipped_chunks} latency={result.metrics.total_latency_ms}ms")
        else:
            print(f"❌ ERR {source}")
            print(f"   └─ error={result.error}")
            success = False
    
    print("\n" + "=" * 80)
    if success:
        print("✅ 摄取完成！")
    else:
        print("⚠️  部分摄取失败")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    main()
