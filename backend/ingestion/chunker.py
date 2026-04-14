"""Chunk structured markdown by ## and ### headers."""

import re


def chunk_markdown(markdown: str) -> list[dict]:
    """
    Split markdown into chunks at ## and ### boundaries.

    Each chunk dict has:
        section_header: str  — the nearest ## or ### heading
        content: str         — text under that heading

    No cross-section overlap: prepending the previous section's tail into the
    next section's content was corrupting thin sections (e.g. a "Grading Policies"
    header with minimal body would end up containing course-objectives text from the
    preceding "Expected Learning Outcomes" section, breaking semantic search).
    Sections are already coherent semantic units; retrieval handles cross-boundary
    context by returning multiple relevant chunks.
    """
    # Split on ## or ### headers, keeping the header in each piece
    pattern = re.compile(r"(?=^#{2,3} )", re.MULTILINE)
    sections = pattern.split(markdown)

    chunks: list[dict] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.splitlines()
        header = lines[0].lstrip("#").strip()
        body = "\n".join(lines[1:]).strip()

        chunks.append({"section_header": header, "content": body})

    return chunks
