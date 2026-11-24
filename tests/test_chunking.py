from rag import chunking, corpus
from rag.corpus import Doc

DOC = Doc("d1", "Title", "svc", 1, "x.md", """# Title
Intro paragraph that is long enough to stand on its own as a chunk, with several words in it, more words here.

## Steps
1. Run this:
```bash
# not a heading, a shell comment
echo hi
```
2. Then check the output and confirm that the result is what you expected before continuing.

## Tiny
ok
""")


def test_heading_chunks_follow_sections_and_keep_code_blocks_whole():
    chunks = chunking.heading(DOC, DOC.body)
    assert [c.section for c in chunks] == ["Overview", "Steps"]
    assert "# not a heading" in chunks[1].text and "echo hi" in chunks[1].text


def test_tiny_sections_are_merged_into_the_previous_chunk():
    chunks = chunking.heading(DOC, DOC.body)
    assert chunks[-1].text.endswith("ok")


def test_embed_text_carries_the_title_and_section_header():
    assert chunking.heading(DOC, DOC.body)[1].embed_text.startswith("Title > Steps\n")


def test_fixed_windows_overlap_and_cover_the_document():
    body = " ".join(f"word{i}" for i in range(400))
    chunks = chunking.fixed(DOC, body, size=128, overlap=16)
    assert len(chunks) > 1
    assert chunks[0].text.split()[-1] in chunks[1].text   # overlap
    assert chunks[-1].text.endswith("word399")


def test_chunk_ids_are_unique_for_the_whole_corpus():
    for name, fn in chunking.STRATEGIES.items():
        ids = [c.chunk_id for d in corpus.load() for c in fn(d, d.body)]
        assert len(ids) == len(set(ids)), name


def test_heading_chunks_fit_the_embedding_model():
    for d in corpus.load():
        for c in chunking.heading(d, d.body):
            assert chunking.n_tokens(c.embed_text) <= 512
