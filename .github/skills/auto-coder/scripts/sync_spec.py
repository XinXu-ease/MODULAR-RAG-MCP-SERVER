#!/usr/bin/env python3
"""
Spec Sync — splits DEV_SPEC.md into chapter files under auto-coder/specs/,
and synchronizes additional spec/guide documents (e.g., LOADER_EXTENSION_SPEC.md).

Usage:
    python scripts/sync_spec.py [--force]
    
This script:
1. Syncs chapters from DEV_SPEC.md → specs/01-07.md
2. Syncs supplementary docs (*_SPEC.md, *_GUIDE.md) → specs/supplements/
3. Generates specification_index.md for auto-coder reference
"""

import hashlib
import re
import sys
from pathlib import Path
from typing import List, Tuple, NamedTuple, Dict


class Chapter(NamedTuple):
    number: int
    cn_title: str
    filename: str
    start_line: int
    end_line: int
    line_count: int


# Chapter number -> English slug (encoding-independent)
NUMBER_SLUG_MAP = {
    1: "overview",
    2: "features",
    3: "tech-stack",
    4: "testing",
    5: "architecture",
    6: "schedule",
    7: "future",
}


def _slug(chapter_num: int, title: str) -> str:
    if chapter_num in NUMBER_SLUG_MAP:
        return NUMBER_SLUG_MAP[chapter_num]
    # Fallback: sanitize whatever title text we have
    clean = re.sub(r'[^\w]+', '-', title, flags=re.ASCII).strip('-').lower()
    return clean or f"chapter-{chapter_num}"


def detect_chapters(content: str) -> List[Chapter]:
    lines = content.split('\n')
    starts: List[Tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        m = re.match(r'^## (\d+)\.\s+(.+)$', line)
        if m:
            starts.append((int(m.group(1)), m.group(2).strip(), i))
    if not starts:
        raise ValueError("No chapters found. Expected '## N. Title'")
    chapters = []
    for idx, (num, title, start) in enumerate(starts):
        end = starts[idx + 1][2] if idx + 1 < len(starts) else len(lines)
        chapters.append(Chapter(num, title, f"{num:02d}-{_slug(num, title)}.md", start, end, end - start))
    return chapters


def extract_description(content: str) -> str:
    """Extract first paragraph (non-title, non-code) as description."""
    lines = content.split('\n')
    description_lines = []
    in_code_block = False
    
    for line in lines:
        # Skip title lines and empty lines at start
        if line.startswith('#'):
            continue
        
        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        
        if in_code_block:
            continue
        
        # Collect non-empty lines until we hit a heading or another code block
        if line.strip() and not line.strip().startswith('>'):
            description_lines.append(line.strip())
            if len(description_lines) >= 3:  # Limit to ~3 lines
                break
    
    return ' '.join(description_lines)[:200]  # Limit to 200 chars


def generate_spec_index(specs_dir: Path, chapters: List[Chapter], supplements: Dict[str, dict]):
    """Generate specification_index.md for auto-coder reference."""
    index_content = """# 📚 Specification Index

This index lists all available specifications and design documents for auto-coder reference.

## 设计文档总览

Auto-coder implementation should reference these documents during task development:

---

## 核心规范（DEV_SPEC 章节）

| # | Chapter | Description |
|---|---------|-------------|"""
    
    for ch in chapters:
        # Clean title
        clean_title = ch.cn_title.replace('(', '').replace(')', '').strip()
        index_content += f"\n| {ch.number} | [{clean_title}](./{ch.filename}) | {ch.line_count} lines |"
    
    index_content += """

---

## 补充设计文档（Task-Specific Guides）

When implementing tasks related to the topics below, reference these supplementary guides:

"""
    
    if supplements:
        index_content += """| Document | Purpose | Location |
|----------|---------|----------|"""
        
        for filename, info in sorted(supplements.items()):
            # Extract purpose from filename
            purpose = filename.replace('_', ' ').replace('.md', '')
            detail = info.get('description', 'Design and implementation guide')
            index_content += f"\n| {purpose} | {detail[:80]}... | `supplements/{filename}` |"
    else:
        index_content += "*No supplementary guides found yet.*"
    
    index_content += """

---

## 文档查阅指南

### For Implementation Tasks

1. **First**: Read relevant chapter from DEV_SPEC (e.g., `05-architecture.md` for structure)
2. **Then**: Check supplementary guides in `supplements/` for detailed code examples
3. **Key Files**:
   - `supplements/LOADER_EXTENSION_SPEC.md` - Complete Loader implementation with code
   - `supplements/STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md` - Storage/retrieval/evaluation module changes
   - `supplements/DASHBOARD_ADAPTATION_GUIDE.md` - UI component design
   - `supplements/IMPLEMENTATION_SUMMARY.md` - Overall project plan and checklist
   - `supplements/README_DUAL_LOADER_EXTENSION.md` - Quick navigation guide

### For Testing

Reference `04-testing.md` for testing conventions, then check supplement docs for test scenarios.

### For Schedule Updates

Reference `06-schedule.md` to mark task completion status.

---

## 同步信息

- **Generated**: Auto-synced by `scripts/sync_spec.py`
- **Last Update**: Each time you run `python scripts/sync_spec.py`
- **Source**: 
  - DEV_SPEC.md (main specification)
  - Root directory `*_SPEC.md`, `*_GUIDE.md` (supplementary documents)

---

**提示**: 这份索引由脚本自动生成。如有新增设计文档，运行 sync_spec.py 查看最新列表。
"""
    
    (specs_dir / "specification_index.md").write_text(index_content, encoding='utf-8')



def sync(force: bool = False):
    skill_dir = Path(__file__).parent.parent          # auto-coder/
    repo_root = skill_dir.parent.parent.parent        # project root
    dev_spec  = repo_root / "DEV_SPEC.md"
    specs_dir = skill_dir / "specs"
    hash_file = skill_dir / ".spec_hash"
    supplements_dir = specs_dir / "supplements"

    if not dev_spec.exists():
        print(f"ERROR: {dev_spec} not found"); sys.exit(1)

    # Hash check (combined hash of all spec files)
    all_spec_files = [dev_spec]
    for pattern in ["*_SPEC.md", "*_GUIDE.md", "*_ADAPTATION.md", "*_SUMMARY.md"]:
        all_spec_files.extend(repo_root.glob(pattern))
    all_spec_files = sorted(set(all_spec_files))  # Remove duplicates and sort
    combined_content = b"".join(f.read_bytes() for f in all_spec_files)
    current_hash = hashlib.sha256(combined_content).hexdigest()
    
    if not force and hash_file.exists() and hash_file.read_text().strip() == current_hash:
        print("specs up-to-date"); return

    content = dev_spec.read_text(encoding='utf-8')
    chapters = detect_chapters(content)
    lines = content.split('\n')

    specs_dir.mkdir(parents=True, exist_ok=True)
    supplements_dir.mkdir(parents=True, exist_ok=True)

    # Clean orphans in main specs dir
    old = {f.name for f in specs_dir.glob("*.md") if f.name != "supplements"}
    new = {ch.filename for ch in chapters}
    for f in old - new:
        (specs_dir / f).unlink()

    # Write main chapters
    for ch in chapters:
        (specs_dir / ch.filename).write_text('\n'.join(lines[ch.start_line:ch.end_line]), encoding='utf-8')

    # Sync supplementary docs (*_SPEC.md, *_GUIDE.md, *_ADAPTATION.md, *_SUMMARY.md, *_EXTENSION.md, etc.)
    supplement_patterns = ["*_SPEC.md", "*_GUIDE.md", "*_ADAPTATION.md", "*_SUMMARY.md", "*_EXTENSION.md", "README*.md"]
    supplement_files = []
    for pattern in supplement_patterns:
        supplement_files.extend(repo_root.glob(pattern))
    
    # Exclude DEV_SPEC.md as it's handled as chapters
    supplement_files = [f for f in supplement_files if f.name != "DEV_SPEC.md"]
    supplement_files = sorted(set(supplement_files))  # Remove duplicates and sort
    
    # Clean orphans in supplements dir
    old_supplements = {f.name for f in supplements_dir.glob("*.md")}
    new_supplements = {f.name for f in supplement_files}
    for f in old_supplements - new_supplements:
        (supplements_dir / f).unlink()
    
    # Copy/sync supplementary files
    supplement_info = {}
    for supp_file in supplement_files:
        dest = supplements_dir / supp_file.name
        dest.write_text(supp_file.read_text(encoding='utf-8'), encoding='utf-8')
        # Extract first paragraph as description
        content_text = supp_file.read_text(encoding='utf-8')
        first_para = extract_description(content_text)
        supplement_info[supp_file.name] = {
            "path": str(supp_file.relative_to(repo_root)),
            "description": first_para
        }

    # Generate specification index
    generate_spec_index(specs_dir, chapters, supplement_info)

    hash_file.write_text(current_hash)
    print(f"synced {len(chapters)} chapters + {len(supplement_files)} supplements")


if __name__ == "__main__":
    sync(force="--force" in sys.argv)
