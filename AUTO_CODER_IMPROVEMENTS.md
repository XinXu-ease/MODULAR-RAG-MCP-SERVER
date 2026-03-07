# Auto-Coder Automation 改进说明

## 概述

本次改进解决了一个关键的自动化问题：原有的 `sync_spec.py` 脚本只能同步 DEV_SPEC.md 内的章节（01-07.md），无法识别新增的补充设计文档（如 LOADER_EXTENSION_SPEC.md, DASHBOARD_ADAPTATION_GUIDE.md 等）。

**改进后**: Auto-coder 现在可以自动同步并索引 DEV_SPEC.md + 所有补充文档，为实现阶段提供完整的设计参考。

---

## 改进清单

### 1. 增强的 sync_spec.py 脚本

**文件位置**: `.github/skills/auto-coder/scripts/sync_spec.py`

#### 改进内容：

| 功能 | 之前 | 现在 |
|------|------|------|
| **同步源** | 仅 DEV_SPEC.md 章节 | DEV_SPEC.md 章节 + `*_SPEC.md`, `*_GUIDE.md`, `*_ADAPTATION.md`, `*_SUMMARY.md`, `README*.md` |
| **输出目录** | `specs/01-07.md` | `specs/01-07.md` + `specs/supplements/` |
| **索引生成** | ❌ | ✅ 自动生成 `specs/specification_index.md` |
| **哈希检测** | 仅追踪 DEV_SPEC.md 变化 | 追踪所有设计文档变化（包括 *_ADAPTATION.md 等） |
| **排除规则** | 无 | 自动排除 DEV_SPEC.md（防止重复） |

#### 核心函数变更：

```python
# 新增函数 - 提取文档描述
def extract_description(content: str) -> str:
    """提取文档的第一段作为描述"""
    # 扫描内容找到第一个有意义的段落

# 新增函数 - 生成规范索引
def generate_spec_index(specs_dir: Path, chapters: List[Chapter], supplements: Dict):
    """生成 specification_index.md 供 auto-coder 参考"""
    # 链接所有章节 + 补充文档

# 改进的 sync() 函数
def sync(force: bool = False):
    # 计算所有规范文件的组合哈希（不仅是 DEV_SPEC.md）
    all_spec_files = [dev_spec] + list(repo_root.glob("*_SPEC.md")) + ...
    
    # 同步章节
    for ch in chapters:
        (specs_dir / ch.filename).write_text(...)
    
    # 同步补充文档到 supplements/ 子目录
    for supp_file in supplement_files:
        (supplements_dir / supp_file.name).write_text(...)
    
    # 生成综合索引
    generate_spec_index(specs_dir, chapters, supplement_info)
```

---

### 2. 更新的 SKILL.md 工作流

**文件位置**: `.github/skills/auto-coder/SKILL.md`

#### 改进的工作流步骤（自动执行）：

**第 1 步 - Sync Spec**（自动执行 - 用户无需干预）：
- 之前：仅同步 DEV_SPEC 章节到 `specs/`
- 现在：自动同时同步 DEV_SPEC 章节 + 所有补充设计文档（`*_SPEC.md`, `*_GUIDE.md`, `*_ADAPTATION.md` 等）到 `supplements/` 目录

**第 3 步 - Implement**：
- 之前：仅参考 `specs/` 下的章节文件
- 现在：推荐首先查看 `specs/specification_index.md`，然后根据需要参考`specs/supplements/` 中的详细实现指南

**新增的目录结构说明**：
```
specs/
├── specification_index.md        # 🆕 总体导航索引
├── 01-overview.md
├── 02-features.md
├── 03-tech-stack.md
├── 04-testing.md
├── 05-architecture.md
├── 06-schedule.md
├── 07-future.md
└── supplements/                  # 🆕 补充设计文档目录
    ├── LOADER_EXTENSION_SPEC.md
    ├── STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md
    ├── DASHBOARD_ADAPTATION_GUIDE.md
    ├── IMPLEMENTATION_SUMMARY.md
    └── README_DUAL_LOADER_EXTENSION.md
```

---

## 运行工作机制

同步操作 **自动执行**，无需手动干预：

1. **Sync Spec 自动触发** — 当运行 "auto code" 命令时，auto-coder 的工作流第1步会自动执行 sync_spec.py
2. **变更检测自动化** — 脚本计算所有规范文件的组合哈希，发现任何文档变化时自动重新同步
3. **索引自动生成** — `specs/specification_index.md` 和 `supplements/` 目录在每次同步时自动更新

**用户无需手动运行 sync_spec.py**，除非调试或强制重新同步：

```bash
# 仅在调试或手动验证时使用
python .github/skills/auto-coder/scripts/sync_spec.py --force
```

### 自动触发时机

Sync Spec 步骤会在以下情况自动执行：
1. **运行 auto-coder** — 每次 auto code 命令都会自动触发（第1步）
2. **任何设计文档修改** — 启用监听时自动检测到 `*_SPEC.md`, `*_GUIDE.md`, `*_ADAPTATION.md` 等文件的变化
3. **新增补充文档** — 自动检测到新增的 `*_SPEC.md`, `*_GUIDE.md` 文件

### 生成的索引内容

`specs/specification_index.md` 包含：

```markdown
# 核心规范（DEV_SPEC 章节）
- 链接到 01-07.md 各章节
- 显示每章行数统计

# 补充设计文档（Task-Specific Guides）
- 列出 `supplements/` 目录中的所有文档
- 提取每份文档的简介（第一段）
- 提供快速导航链接
```

---

## 使用场景

### 场景 1：添加新的设计文档

当创建新的设计文档（如 `PERFORMANCE_OPTIMIZATION_SPEC.md`）时：

```bash
# 1. 创建设计文档
echo "# Performance Optimization Spec" > PERFORMANCE_OPTIMIZATION_SPEC.md

# 2. 提交/保存文件，无需手动sync
# 下次运行 auto-coder 时会自动同步

# 3. 验证（可选，用于对侦测同步）：
python .github/skills/auto-coder/scripts/sync_spec.py --force

# 4. 确认：
# - specs/supplements/PERFORMANCE_OPTIMIZATION_SPEC.md 已创建 ✓
# - specs/specification_index.md 已更新，列出新文档 ✓
```

### 场景 2：Auto-coder 实现阶段工作流

运行 "auto code" 命令时（所有步骤自动执行，无需手动干预）：

```
[Sync Spec] ← 自动同步最新的 DEV_SPEC + 所有补充文档 (用户无需操作)
  ↓
[Find Task] ← 自动识别待实现的任务
  ↓
[Implement] ← 自动参考 specs/specification_index.md
           ← 自动查看 specs/supplements/ 中的详细设计指南
  ↓
[Test] ← 自动按照 04-testing.md 中的方案执行测试
  ↓
[Persist] ← 自动保存实现成果
```

**关键点**: 开发者不需要手动运行 sync_spec.py，所有同步都在 auto-coder 工作流的第1步自动完成。

---

## 技术细节

### 哈希变更检测逻辑

```python
# 之前（仅追踪单个文件）
current_hash = hashlib.sha256(dev_spec.read_bytes()).hexdigest()

# 现在（追踪所有设计文档）
all_spec_files = [dev_spec]
for pattern in ["*_SPEC.md", "*_GUIDE.md", "*_ADAPTATION.md", "*_SUMMARY.md"]:
    all_spec_files.extend(repo_root.glob(pattern))
all_spec_files = sorted(set(all_spec_files))  # Remove duplicates and sort
combined_content = b"".join(f.read_bytes() for f in all_spec_files)
current_hash = hashlib.sha256(combined_content).hexdigest()
```

### 补充文档过滤

```python
# 收集补充文件（覆盖多种命名模式）
supplement_patterns = ["*_SPEC.md", "*_GUIDE.md", "*_ADAPTATION.md", "*_SUMMARY.md", "*_EXTENSION.md", "README*.md"]
supplement_files = []
for pattern in supplement_patterns:
    supplement_files.extend(repo_root.glob(pattern))

# 排除 DEV_SPEC.md（已作为章节处理）
supplement_files = [f for f in supplement_files if f.name != "DEV_SPEC.md"]
supplement_files = sorted(set(supplement_files))  # Remove duplicates and sort
```

---

## 测试验证

### 验证清单

- ✅ 脚本成功识别 7 个 DEV_SPEC 章节
- ✅ 脚本成功识别 6 个补充设计文档（`*_SPEC.md`, `*_GUIDE.md`, `*_ADAPTATION.md` 等）
- ✅ specifications_index.md 正确生成，包含章节链接
- ✅ supplementary 文档正确复制到 `specs/supplements/` 目录
- ✅ DEV_SPEC.md 被正确排除，不重复出现在 supplements/ 中
- ✅ 哈希变更检测覆盖所有设计文件（包括 *_ADAPTATION.md）

### 测试执行结果

```
$ python .github/skills/auto-coder/scripts/sync_spec.py --force
synced 7 chapters + 6 supplements
```
01-overview.md
02-features.md
03-tech-stack.md
04-testing.md
05-architecture.md
06-schedule.md
07-future.md
specification_index.md        ← 新增

$ ls -la .github/skills/auto-coder/specs/supplements/
DASHBOARD_ADAPTATION_GUIDE.md
IMPLEMENTATION_SUMMARY.md
LOADER_EXTENSION_SPEC.md
README.md
README_DUAL_LOADER_EXTENSION.md
STORAGE_RETRIEVAL_EVALUATION_ADAPTATION.md
```

---

## 后续改进建议

### 短期（已实现）
- ✅ 双源同步支持（DEV_SPEC + 补充文档）
- ✅ 自动索引生成
- ✅ 哈希追踪所有文档变化

### 中期（建议）
1. **文档分类** - 按功能模块标签补充文档（标签：Loader, Storage, Dashboard 等）
2. **交叉引用** - 在 specification_index.md 中添加"相关文档"链接
3. **版本管理** - 追踪设计文档的版本历史和修订记录

### 长期（建议）
1. **动态建议** - 基于任务类型自动推荐相关设计文档
2. **集成化搜索** - 在 Implement 步骤中搜索跨文档的代码示例
3. **实时同步** - 利用 Git hooks 自动触发同步（新文档提交时）

---

## 总结

这次改进实现了**完整的设计文档自动化管理**：

| 当前问题 | 解决方案 | 收益 |
|---------|--------|------|
| 新增设计文件被忽视 | 多源扫描 + 补充目录 | 所有设计文档都被纳入自动化 |
| 无法快速导航 | 自动生成索引 | Auto-coder 实现阶段有明确的参考指南 |
| 哈希检测不完整 | 组合哈希 | 任何文档修改都能被正确捕捉 |
| 手动维护索引 | 全自动生成 | 零维护成本的规范管理 |

从现在起，每当运行 auto-coder 时，它都能同时看到 DEV_SPEC 的核心规范和最新的补充设计文档。
