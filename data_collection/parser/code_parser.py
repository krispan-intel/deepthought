"""
data_collection/parser/code_parser.py

Tree-sitter based parser for source code files.
Handles C, C++, Rust, Java, Python.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from data_collection.crawler.base_crawler import CrawlResult
from data_collection.parser.base_parser import BaseParser, ParsedDocument


# ─────────────────────────────────────────────────────────────────
# Tree-sitter Language Setup
# ─────────────────────────────────────────────────────────────────

def _load_languages() -> Dict[str, Any]:
    """Load tree-sitter language bindings."""
    languages = {}

    try:
        import tree_sitter_c
        from tree_sitter import Language
        languages[".c"] = Language(tree_sitter_c.language())
        languages[".h"] = Language(tree_sitter_c.language())
        logger.debug("  tree-sitter C loaded")
    except ImportError:
        logger.warning("tree-sitter-c not available")

    try:
        import tree_sitter_cpp
        from tree_sitter import Language
        languages[".cpp"] = Language(tree_sitter_cpp.language())
        languages[".cc"]  = Language(tree_sitter_cpp.language())
        languages[".cxx"] = Language(tree_sitter_cpp.language())
        languages[".hpp"] = Language(tree_sitter_cpp.language())
        logger.debug("  tree-sitter C++ loaded")
    except ImportError:
        logger.warning("tree-sitter-cpp not available")

    try:
        import tree_sitter_rust
        from tree_sitter import Language
        languages[".rs"] = Language(tree_sitter_rust.language())
        logger.debug("  tree-sitter Rust loaded")
    except ImportError:
        logger.warning("tree-sitter-rust not available")

    try:
        import tree_sitter_java
        from tree_sitter import Language
        languages[".java"] = Language(tree_sitter_java.language())
        logger.debug("  tree-sitter Java loaded")
    except ImportError:
        logger.warning("tree-sitter-java not available")

    return languages


LANGUAGES = _load_languages()


# ─────────────────────────────────────────────────────────────────
# Node Type Definitions per Language
# ─────────────────────────────────────────────────────────────────

TARGET_NODE_TYPES = {
    "c": [
        "function_definition",
        "struct_specifier",
        "union_specifier",
        "enum_specifier",
        "type_definition",
        "preproc_def",
        "preproc_function_def",
    ],
    "cpp": [
        "function_definition",
        "class_specifier",
        "struct_specifier",
        "namespace_definition",
        "template_declaration",
    ],
    "rust": [
        "function_item",
        "struct_item",
        "enum_item",
        "trait_item",
        "impl_item",
        "macro_definition",
        "mod_item",
    ],
    "java": [
        "method_declaration",
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
    ],
}

EXTENSION_TO_LANG = {
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp",
    ".cxx": "cpp", ".hpp": "cpp",
    ".rs": "rust",
    ".java": "java",
}


# ─────────────────────────────────────────────────────────────────
# Kernel-specific Metadata Extractors
# ─────────────────────────────────────────────────────────────────

def detect_subsystem(file_path: str) -> str:
    """Detect Linux kernel subsystem from file path."""
    path = file_path.lower()

    subsystem_map = {
        "arch/x86":       "x86",
        "kernel/sched":   "scheduler",
        "kernel/bpf":     "bpf",
        "mm/":            "memory_management",
        "net/":           "networking",
        "drivers/":       "drivers",
        "fs/":            "filesystem",
        "security/":      "security",
        "include/linux":  "kernel_headers",
        "tools/perf":     "perf",
        "lib/":           "kernel_lib",
        "init/":          "init",
        "ipc/":           "ipc",
    }

    for prefix, subsystem in subsystem_map.items():
        if prefix in path:
            return subsystem

    return "other"


def extract_kernel_attributes(text: str) -> List[str]:
    """Extract Linux kernel function attributes."""
    import re
    attrs = []
    patterns = [
        r"__init", r"__exit", r"__cold", r"__hot",
        r"__always_inline", r"noinline", r"__noreturn",
        r"__must_check", r"__pure", r"__const",
        r"EXPORT_SYMBOL", r"EXPORT_SYMBOL_GPL",
        r"module_init", r"module_exit",
        r"SYSCALL_DEFINE\d",
        r"DEFINE_\w+",
    ]
    for pattern in patterns:
        if re.search(pattern, text):
            attrs.append(pattern.replace(r"\d", "N").replace(r"\w+", "*"))
    return attrs


def extract_config_guards(text: str) -> List[str]:
    """Extract CONFIG_ guards from source code."""
    import re
    configs = re.findall(r"CONFIG_[A-Z0-9_]+", text)
    return list(set(configs))


def extract_inline_asm(text: str) -> List[str]:
    """Extract inline assembly blocks."""
    import re
    asm_blocks = re.findall(
        r'asm\s+(?:volatile\s+)?\([^;]+\)',
        text,
        re.DOTALL,
    )
    return asm_blocks


# ─────────────────────────────────────────────────────────────────
# Main Code Parser
# ─────────────────────────────────────────────────────────────────

class CodeParser(BaseParser):
    """
    Tree-sitter based source code parser.

    Extracts semantic units (functions, structs, enums)
    with rich metadata for DeepThought's RAG pipeline.
    """

    def can_parse(self, result: CrawlResult) -> bool:
        file_path = result.metadata.get("file_path", "")
        suffix = Path(file_path).suffix.lower()
        return suffix in LANGUAGES

    def parse(self, result: CrawlResult) -> List[ParsedDocument]:
        file_path = result.metadata.get("file_path", "unknown")
        suffix = Path(file_path).suffix.lower()
        lang_name = EXTENSION_TO_LANG.get(suffix, "c")

        if suffix not in LANGUAGES:
            logger.warning(f"No tree-sitter parser for: {suffix}")
            return self._fallback_parse(result)

        try:
            content_str = result.content.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Decode error {file_path}: {e}")
            return []

        language = LANGUAGES[suffix]
        docs = self._parse_with_treesitter(
            content=content_str,
            language=language,
            lang_name=lang_name,
            file_path=file_path,
            source_name=result.source_name,
            base_metadata=result.metadata,
        )

        # Special handling for kernel headers
        if "include/linux" in file_path or file_path.endswith(".h"):
            docs = self._enrich_header_docs(docs, content_str)

        logger.debug(
            f"  Parsed {file_path}: {len(docs)} nodes"
        )
        return docs

    def _parse_with_treesitter(
        self,
        content: str,
        language: Any,
        lang_name: str,
        file_path: str,
        source_name: str,
        base_metadata: dict,
    ) -> List[ParsedDocument]:

        from tree_sitter import Parser

        parser = Parser(language)
        tree = parser.parse(bytes(content, "utf-8"))

        target_types = TARGET_NODE_TYPES.get(lang_name, [])
        docs = []

        self._traverse_tree(
            node=tree.root_node,
            content=content,
            target_types=target_types,
            file_path=file_path,
            source_name=source_name,
            base_metadata=base_metadata,
            docs=docs,
        )

        return docs

    def _traverse_tree(
        self,
        node: Any,
        content: str,
        target_types: List[str],
        file_path: str,
        source_name: str,
        base_metadata: dict,
        docs: List[ParsedDocument],
    ):
        """Recursively traverse AST and extract target nodes."""

        if node.type in target_types:
            doc = self._node_to_document(
                node=node,
                content=content,
                file_path=file_path,
                source_name=source_name,
                base_metadata=base_metadata,
            )
            if doc:
                docs.append(doc)
            # Don't recurse into matched nodes to avoid duplicates
            return

        for child in node.children:
            self._traverse_tree(
                node=child,
                content=content,
                target_types=target_types,
                file_path=file_path,
                source_name=source_name,
                base_metadata=base_metadata,
                docs=docs,
            )

    def _node_to_document(
        self,
        node: Any,
        content: str,
        file_path: str,
        source_name: str,
        base_metadata: dict,
    ) -> Optional[ParsedDocument]:
        """Convert a tree-sitter node to a ParsedDocument."""

        node_text = content[node.start_byte:node.end_byte]

        # Skip very short nodes (likely noise)
        if len(node_text.strip()) < 20:
            return None

        # Find preceding comment block
        preceding_comment = self._find_preceding_comment(
            node, content
        )

        # Full content = comment + code
        full_content = (
            f"{preceding_comment}\n{node_text}"
            if preceding_comment
            else node_text
        )

        # Extract name
        name = self._extract_name(node, content)

        # Build metadata
        metadata = {
            **base_metadata,
            "node_type": node.type,
            "name": name,
            "file_path": file_path,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "line_count": node.end_point[0] - node.start_point[0] + 1,
            "subsystem": detect_subsystem(file_path),
            "kernel_attributes": extract_kernel_attributes(node_text),
            "config_guards": extract_config_guards(node_text),
            "has_inline_asm": bool(extract_inline_asm(node_text)),
            "source": source_name,
        }

        return ParsedDocument(
            content=full_content,
            doc_type="kernel_source",
            source_name=source_name,
            uri=base_metadata.get(
                "uri",
                f"{source_name}:{file_path}:{node.start_point[0]}"
            ),
            metadata=metadata,
        )

    def _find_preceding_comment(
        self,
        node: Any,
        content: str,
    ) -> str:
        """
        Find the comment block immediately preceding a node.
        Critical for understanding function purpose.
        """
        comments = []
        current = node.prev_named_sibling

        while current and current.type == "comment":
            comment_text = content[
                current.start_byte:current.end_byte
            ]
            comments.insert(0, comment_text)
            current = current.prev_named_sibling

        return "\n".join(comments)

    def _extract_name(self, node: Any, content: str) -> str:
        """Extract the name identifier from a node."""
        # Try common name child node types
        for child in node.children:
            if child.type in (
                "identifier",
                "type_identifier",
                "field_identifier",
            ):
                return content[child.start_byte:child.end_byte]

            # For function_definition: look inside declarator
            if child.type in (
                "function_declarator",
                "pointer_declarator",
            ):
                for grandchild in child.children:
                    if grandchild.type in (
                        "identifier",
                        "field_identifier",
                    ):
                        return content[
                            grandchild.start_byte:grandchild.end_byte
                        ]

        return "unknown"

    def _enrich_header_docs(
        self,
        docs: List[ParsedDocument],
        content: str,
    ) -> List[ParsedDocument]:
        """
        Extra enrichment for kernel header files.
        Headers define the API surface - very important for DeepThought.
        """
        for doc in docs:
            if doc.metadata.get("node_type") == "struct_specifier":
                doc.metadata["is_kernel_api"] = True
                doc.metadata["doc_subtype"] = "kernel_struct"
        return docs

    def _fallback_parse(
        self,
        result: CrawlResult,
    ) -> List[ParsedDocument]:
        """Fallback: treat entire file as one document."""
        try:
            content = result.content.decode("utf-8", errors="replace")
        except Exception:
            return []

        return [ParsedDocument(
            content=content,
            doc_type="source_file",
            source_name=result.source_name,
            uri=result.uri,
            metadata=result.metadata,
        )]
