"""
Code-Aware Chunking Service for GitHub repositories.

Chunks files based on their content type:
- Code: Function/class-level extraction
- Docs: Header-based chunking (markdown)
- Config: Atomic (whole-file) chunking
- Metadata: Atomic with structured extraction
- CI: Atomic per workflow file
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from services.github_service import RepoFile

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A chunk of content ready for embedding and indexing."""
    id: str
    content: str
    content_type: str  # code, docs, config, metadata, ci
    chunk_type: str  # function, class, module, section, atomic
    file_path: str
    language: str
    repo_owner: str
    repo_name: str
    parent_class: str = ""
    section_header: str = ""
    is_high_value: bool = False


class ChunkingService:
    """
    Content-type-aware chunking service for code repositories.

    Strategy per content type:
    - code   → function/class-level extraction (regex-based)
    - docs   → header-based markdown chunking
    - config → atomic (whole-file if fits, else split)
    - metadata → atomic with key extraction
    - ci     → atomic per workflow file
    """

    def __init__(self, max_chunk_size: int = 1500, chunk_overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_repo_files(
        self,
        files: list[RepoFile],
        repo_owner: str,
        repo_name: str,
    ) -> list[Chunk]:
        """
        Chunk all files from a repository.

        Routes each file to the appropriate chunking strategy.
        """
        all_chunks: list[Chunk] = []

        for f in files:
            try:
                if f.content_type == "docs":
                    chunks = self._chunk_markdown(f, repo_owner, repo_name)
                elif f.content_type in ("config", "ci"):
                    chunks = self._chunk_atomic(f, repo_owner, repo_name)
                elif f.content_type == "metadata":
                    chunks = self._chunk_atomic(f, repo_owner, repo_name)
                else:  # code
                    chunks = self._chunk_code(f, repo_owner, repo_name)

                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Failed to chunk {f.path}: {e}")
                # Fallback: treat as atomic
                chunks = self._chunk_atomic(f, repo_owner, repo_name)
                all_chunks.extend(chunks)

        logger.info(
            f"Chunked {len(files)} files into {len(all_chunks)} chunks "
            f"(code={sum(1 for c in all_chunks if c.content_type == 'code')}, "
            f"docs={sum(1 for c in all_chunks if c.content_type == 'docs')}, "
            f"config={sum(1 for c in all_chunks if c.content_type in ('config', 'ci', 'metadata'))})"
        )
        return all_chunks

    # ------------------------------------------------------------------
    # Code chunking: function/class-level extraction
    # ------------------------------------------------------------------

    def _chunk_code(self, f: RepoFile, owner: str, name: str) -> list[Chunk]:
        """
        Chunk code files by extracting functions and classes.

        Uses regex-based extraction (not AST) for broad language support.
        Falls back to sliding-window if no structure is found.
        """
        if f.language in ("python", ):
            return self._chunk_python(f, owner, name)
        elif f.language in ("javascript", "typescript", "vue", "svelte"):
            return self._chunk_js_ts(f, owner, name)
        elif f.language in ("java", "csharp", "kotlin", "scala"):
            return self._chunk_curly_brace_class(f, owner, name)
        elif f.language in ("go", "rust", "cpp", "c", "swift"):
            return self._chunk_curly_brace_func(f, owner, name)
        else:
            # For unknown languages, fall back to sliding-window
            return self._chunk_sliding_window(f, owner, name)

    def _chunk_python(self, f: RepoFile, owner: str, name: str) -> list[Chunk]:
        """Chunk Python files by class and function definitions."""
        chunks: list[Chunk] = []
        lines = f.content.split("\n")

        # Regex for top-level class and function definitions
        class_re = re.compile(r"^class\s+(\w+)")
        func_re = re.compile(r"^(?:async\s+)?def\s+(\w+)")
        method_re = re.compile(r"^    (?:async\s+)?def\s+(\w+)")

        # Collect definition boundaries
        definitions: list[dict] = []
        current_class: Optional[str] = None
        current_class_start: Optional[int] = None

        for i, line in enumerate(lines):
            cm = class_re.match(line)
            if cm:
                # Close previous class if any
                if current_class is not None and current_class_start is not None:
                    pass  # classes are bounded by next class or EOF
                current_class = cm.group(1)
                current_class_start = i
                definitions.append({
                    "type": "class",
                    "name": current_class,
                    "start": i,
                    "parent_class": "",
                })
                continue

            fm = func_re.match(line)
            if fm:
                # Top-level function — also resets current_class
                current_class = None
                current_class_start = None
                definitions.append({
                    "type": "function",
                    "name": fm.group(1),
                    "start": i,
                    "parent_class": "",
                })
                continue

            mm = method_re.match(line)
            if mm and current_class:
                definitions.append({
                    "type": "method",
                    "name": mm.group(1),
                    "start": i,
                    "parent_class": current_class,
                })

        if not definitions:
            return self._chunk_sliding_window(f, owner, name)

        # Calculate end boundaries
        for idx, defn in enumerate(definitions):
            if idx + 1 < len(definitions):
                defn["end"] = definitions[idx + 1]["start"]
            else:
                defn["end"] = len(lines)

        # Build module-level header (imports + top-level code before first def)
        first_def_line = definitions[0]["start"] if definitions else len(lines)
        module_header = "\n".join(lines[:first_def_line]).strip()
        if module_header and len(module_header) > 20:
            chunks.append(self._make_chunk(
                content=module_header,
                content_type="code",
                chunk_type="module",
                file_path=f.path,
                language=f.language,
                owner=owner,
                name=name,
                is_high_value=f.is_high_value,
            ))

        # Build chunks from definitions
        for defn in definitions:
            block = "\n".join(lines[defn["start"]:defn["end"]]).rstrip()
            if not block.strip():
                continue

            # If block is too large, split with sliding window
            if len(block) > self.max_chunk_size * 2:
                sub_chunks = self._split_text(
                    block, f, owner, name,
                    chunk_type=defn["type"],
                    parent_class=defn.get("parent_class", ""),
                    section_header=defn["name"],
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append(self._make_chunk(
                    content=block,
                    content_type="code",
                    chunk_type=defn["type"],
                    file_path=f.path,
                    language=f.language,
                    owner=owner,
                    name=name,
                    parent_class=defn.get("parent_class", ""),
                    section_header=defn["name"],
                    is_high_value=f.is_high_value,
                ))

        return chunks if chunks else self._chunk_sliding_window(f, owner, name)

    def _chunk_js_ts(self, f: RepoFile, owner: str, name: str) -> list[Chunk]:
        """Chunk JS/TS files by function/class/export definitions."""
        chunks: list[Chunk] = []
        lines = f.content.split("\n")

        # Patterns for JS/TS
        patterns = [
            (re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)"), "class"),
            (re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)"), "function"),
            (re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("), "function"),
            (re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_]\w*)\s*=>"), "function"),
            (re.compile(r"^(?:export\s+)?interface\s+(\w+)"), "class"),
            (re.compile(r"^(?:export\s+)?type\s+(\w+)"), "class"),
        ]

        definitions: list[dict] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            for pat, def_type in patterns:
                m = pat.match(stripped)
                if m:
                    definitions.append({
                        "type": def_type,
                        "name": m.group(1),
                        "start": i,
                        "parent_class": "",
                    })
                    break

        if not definitions:
            return self._chunk_sliding_window(f, owner, name)

        # Use brace-matching to find boundaries
        return self._build_chunks_from_definitions(definitions, lines, f, owner, name)

    def _chunk_curly_brace_class(self, f: RepoFile, owner: str, name: str) -> list[Chunk]:
        """Chunk Java/C#/Kotlin files by class definitions."""
        lines = f.content.split("\n")

        patterns = [
            (re.compile(r"(?:public|private|protected|internal)?\s*(?:static\s+)?(?:abstract\s+)?class\s+(\w+)"), "class"),
            (re.compile(r"(?:public|private|protected|internal)?\s*interface\s+(\w+)"), "class"),
            (re.compile(r"(?:public|private|protected|internal)?\s*enum\s+(\w+)"), "class"),
        ]

        definitions: list[dict] = []
        for i, line in enumerate(lines):
            for pat, def_type in patterns:
                m = pat.search(line)
                if m:
                    definitions.append({
                        "type": def_type,
                        "name": m.group(1),
                        "start": i,
                        "parent_class": "",
                    })
                    break

        if not definitions:
            return self._chunk_sliding_window(f, owner, name)

        return self._build_chunks_from_definitions(definitions, lines, f, owner, name)

    def _chunk_curly_brace_func(self, f: RepoFile, owner: str, name: str) -> list[Chunk]:
        """Chunk Go/Rust/C++ files by function definitions."""
        lines = f.content.split("\n")

        patterns = [
            (re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)"), "function"),  # Rust
            (re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)"), "function"),  # Go
            (re.compile(r"^(?:[\w:*&<> ]+)\s+(\w+)\s*\("), "function"),  # C/C++
        ]

        definitions: list[dict] = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            for pat, def_type in patterns:
                m = pat.match(stripped)
                if m:
                    definitions.append({
                        "type": def_type,
                        "name": m.group(1),
                        "start": i,
                        "parent_class": "",
                    })
                    break

        if not definitions:
            return self._chunk_sliding_window(f, owner, name)

        return self._build_chunks_from_definitions(definitions, lines, f, owner, name)

    def _build_chunks_from_definitions(
        self, definitions: list[dict], lines: list[str],
        f: RepoFile, owner: str, name: str,
    ) -> list[Chunk]:
        """Build chunks from definition boundaries, handling braces."""
        chunks: list[Chunk] = []

        # Module header (before first definition)
        if definitions:
            header = "\n".join(lines[:definitions[0]["start"]]).strip()
            if header and len(header) > 20:
                chunks.append(self._make_chunk(
                    content=header, content_type="code", chunk_type="module",
                    file_path=f.path, language=f.language,
                    owner=owner, name=name, is_high_value=f.is_high_value,
                ))

        # Set end boundaries
        for idx, defn in enumerate(definitions):
            if idx + 1 < len(definitions):
                defn["end"] = definitions[idx + 1]["start"]
            else:
                defn["end"] = len(lines)

        for defn in definitions:
            block = "\n".join(lines[defn["start"]:defn["end"]]).rstrip()
            if not block.strip():
                continue

            if len(block) > self.max_chunk_size * 2:
                sub = self._split_text(
                    block, f, owner, name,
                    chunk_type=defn["type"],
                    section_header=defn["name"],
                )
                chunks.extend(sub)
            else:
                chunks.append(self._make_chunk(
                    content=block, content_type="code", chunk_type=defn["type"],
                    file_path=f.path, language=f.language,
                    owner=owner, name=name,
                    section_header=defn["name"],
                    is_high_value=f.is_high_value,
                ))

        return chunks if chunks else self._chunk_sliding_window(f, owner, name)

    # ------------------------------------------------------------------
    # Markdown / docs chunking
    # ------------------------------------------------------------------

    def _chunk_markdown(self, f: RepoFile, owner: str, name: str) -> list[Chunk]:
        """Chunk markdown files by headers (same strategy as Module 4)."""
        chunks: list[Chunk] = []
        lines = f.content.split("\n")

        header_re = re.compile(r"^(#{1,6})\s+(.+)")
        sections: list[dict] = []
        current_header = f.path  # Default section

        section_start = 0
        for i, line in enumerate(lines):
            hm = header_re.match(line)
            if hm:
                # Close previous section
                if i > section_start:
                    sections.append({
                        "header": current_header,
                        "start": section_start,
                        "end": i,
                    })
                current_header = hm.group(2).strip()
                section_start = i

        # Last section
        if section_start < len(lines):
            sections.append({
                "header": current_header,
                "start": section_start,
                "end": len(lines),
            })

        if not sections:
            return self._chunk_atomic(f, owner, name)

        for sec in sections:
            block = "\n".join(lines[sec["start"]:sec["end"]]).strip()
            if not block:
                continue

            # Prepend file path + section header context to the chunk content
            # so keyword search can match on section titles and file identity
            context_prefix = f"File: {f.path}"
            if sec["header"] and sec["header"] != f.path:
                context_prefix += f" | Section: {sec['header']}"
            enriched_block = f"{context_prefix}\n\n{block}"

            if len(enriched_block) > self.max_chunk_size * 2:
                sub = self._split_text(
                    enriched_block, f, owner, name,
                    chunk_type="section",
                    section_header=sec["header"],
                )
                chunks.extend(sub)
            else:
                chunks.append(self._make_chunk(
                    content=enriched_block, content_type="docs", chunk_type="section",
                    file_path=f.path, language=f.language,
                    owner=owner, name=name,
                    section_header=sec["header"],
                    is_high_value=f.is_high_value,
                ))

        return chunks

    # ------------------------------------------------------------------
    # Atomic / config chunking
    # ------------------------------------------------------------------

    def _chunk_atomic(self, f: RepoFile, owner: str, name: str) -> list[Chunk]:
        """
        Chunk file as a single atomic unit (or split if too large).

        Used for config, metadata, and CI files.
        """
        content = f.content.strip()
        if not content:
            return []

        if len(content) <= self.max_chunk_size:
            return [self._make_chunk(
                content=content,
                content_type=f.content_type,
                chunk_type="atomic",
                file_path=f.path,
                language=f.language,
                owner=owner,
                name=name,
                section_header=f.path,
                is_high_value=f.is_high_value,
            )]

        return self._split_text(
            content, f, owner, name,
            chunk_type="atomic",
            section_header=f.path,
        )

    # ------------------------------------------------------------------
    # Sliding window fallback
    # ------------------------------------------------------------------

    def _chunk_sliding_window(self, f: RepoFile, owner: str, name: str) -> list[Chunk]:
        """Fallback chunking using a sliding window with overlap."""
        return self._split_text(
            f.content, f, owner, name,
            chunk_type="module",
            section_header=f.path,
        )

    def _split_text(
        self,
        text: str,
        f: RepoFile,
        owner: str,
        name: str,
        chunk_type: str = "module",
        parent_class: str = "",
        section_header: str = "",
    ) -> list[Chunk]:
        """Split text into overlapping windows."""
        chunks: list[Chunk] = []
        text = text.strip()
        if not text:
            return chunks

        start = 0
        part = 0
        while start < len(text):
            end = start + self.max_chunk_size
            segment = text[start:end]

            # Try to break at a newline
            if end < len(text):
                last_nl = segment.rfind("\n")
                if last_nl > self.max_chunk_size // 3:
                    segment = segment[:last_nl]
                    end = start + last_nl

            chunks.append(self._make_chunk(
                content=segment.strip(),
                content_type=f.content_type,
                chunk_type=chunk_type,
                file_path=f.path,
                language=f.language,
                owner=owner,
                name=name,
                parent_class=parent_class,
                section_header=f"{section_header} (part {part})" if part > 0 else section_header,
                is_high_value=f.is_high_value,
            ))

            start = end - self.chunk_overlap if end < len(text) else len(text)
            part += 1

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_chunk(
        self,
        content: str,
        content_type: str,
        chunk_type: str,
        file_path: str,
        language: str,
        owner: str,
        name: str,
        parent_class: str = "",
        section_header: str = "",
        is_high_value: bool = False,
    ) -> Chunk:
        """Create a Chunk with a deterministic ID."""
        # Deterministic ID from content hash + path
        hash_input = f"{owner}/{name}/{file_path}/{section_header}/{content[:200]}"
        chunk_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
        safe_path = re.sub(r"[^a-zA-Z0-9_-]", "-", file_path)[:60]
        chunk_id = f"{owner}-{name}-{safe_path}-{chunk_hash}".lower()
        chunk_id = re.sub(r"-+", "-", chunk_id).strip("-")

        return Chunk(
            id=chunk_id,
            content=content,
            content_type=content_type,
            chunk_type=chunk_type,
            file_path=file_path,
            language=language,
            repo_owner=owner,
            repo_name=name,
            parent_class=parent_class,
            section_header=section_header,
            is_high_value=is_high_value,
        )
