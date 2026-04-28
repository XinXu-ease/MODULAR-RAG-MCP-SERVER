"""Test official LangChain MarkdownHeaderTextSplitter."""

from src.core.settings import get_settings
from src.libs.splitter.splitter_factory import create_splitter

# Test 1: Load config
print("=" * 60)
print("TEST 1: Configuration Loading")
print("=" * 60)
settings = get_settings()
print(f"Chunking Strategy: {settings.ingestion.chunking_strategy}")
print(f"Chunk Size: {settings.ingestion.chunk_size}")
print(f"Chunk Overlap: {settings.ingestion.chunk_overlap}")
print(f"Refiner Use LLM: {settings.ingestion.refiner_use_llm}")

# Test 2: Create splitter
print("\n" + "=" * 60)
print("TEST 2: Splitter Creation")
print("=" * 60)
splitter = create_splitter(settings)
print(f"Splitter Type: {type(splitter).__name__}")
print(f"Splitter: {splitter}")

# Test 3: Split markdown text
print("\n" + "=" * 60)
print("TEST 3: Markdown Splitting")
print("=" * 60)

sample_markdown = """# Coffee Guide

## Introduction
Learn how to make perfect espresso.

### Requirements
- Machine
- Coffee beans
- Water

## Instructions

### Step 1
Preheat the machine for 5-10 minutes. This is very important.

### Step 2
Grind the coffee to medium-fine consistency. Use about 18-20 grams per shot.

### Step 3
Tamp and extract. The process should take 25-30 seconds.

## Tips
- Use fresh beans (within 2 weeks of roast)
- Experiment with grind size
- Keep equipment clean

## Conclusion
With practice, you'll master espresso brewing."""

chunks = splitter.split(sample_markdown)

print(f"Total chunks: {len(chunks)}\n")
for i, chunk in enumerate(chunks, 1):
    print(f"Chunk {i} ({len(chunk)} chars):")
    print("-" * 40)
    # Show first 150 chars of each chunk
    preview = chunk.replace("\n", " ")[:150]
    print(preview + ("..." if len(chunk) > 150 else ""))
    print()
