"""Test the new semantic boundary splitter."""

from src.libs.splitter.langchain_splitter import MarkdownSplitter

# Sample text with sentences that should NOT be cut
sample = """# How to Make Espresso

## Preparation

First, you need to preheat the machine. This is very important for quality extraction. Second, grind your coffee to medium-fine consistency. The grind size is crucial for proper extraction.

## Steps

1. Insert the portafilter into the group head. Make sure it's properly locked.
2. Start the extraction. Water should flow steadily for 25-30 seconds.
3. Stop when you have about 1-1.5 ounces of espresso in your cup.

## Final Notes

Always clean your equipment immediately after use. This prevents coffee oils from building up and affecting future shots."""

splitter = MarkdownSplitter(chunk_size=200, chunk_overlap=50)
chunks = splitter.split(sample)

print("=" * 80)
print(f"Total chunks: {len(chunks)}")
print("=" * 80)

for i, chunk in enumerate(chunks, 1):
    print(f"\nChunk {i} ({len(chunk)} chars):")
    print("-" * 60)
    # Show the chunk
    lines = chunk.split('\n')
    for line in lines[:10]:  # First 10 lines
        print(f"  {line}")
    if len(lines) > 10:
        print(f"  ... ({len(lines)} lines total)")
    print("-" * 60)
    
    # Check for cut-off sentences
    if chunk and not chunk.strip().endswith(('.', '。', '!', '！', '?', '？', '\n\n')):
        print("  ⚠️  WARNING: Chunk ends mid-sentence!")
