"""
data_collection/parser/kconfig_parser.py

Parser for Linux Kernel Kconfig files.

Kconfig is invaluable for DeepThought:
- Reveals feature dependencies (CONFIG_A depends on CONFIG_B)
- Explains WHY features exist (help text)
- Shows hardware constraints (depends on X86_64)
- Maps the design decision space of the kernel
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from data_collection.crawler.base_crawler import CrawlResult
from data_collection.parser.base_parser import BaseParser, ParsedDocument


@dataclass
class KconfigEntry:
    """A single Kconfig configuration entry."""
    name: str
    entry_type: str            # "bool" | "tristate" | "int" | "string"
    description: str
    help_text: str
    depends_on: List[str] = field(default_factory=list)
    selects: List[str] = field(default_factory=list)
    implies: List[str] = field(default_factory=list)
    default_value: Optional[str] = None
    file_path: str = ""
    line_number: int = 0

    def to_text(self) -> str:
        """Convert to human-readable text for embedding."""
        lines = [
            f"Kernel Config: CONFIG_{self.name}",
            f"Type: {self.entry_type}",
            f"Description: {self.description}",
        ]
        if self.help_text:
            lines.append(f"Help: {self.help_text}")
        if self.depends_on:
            lines.append(f"Depends on: {', '.join(self.depends_on)}")
        if self.selects:
            lines.append(f"Selects: {', '.join(self.selects)}")
        if self.implies:
            lines.append(f"Implies: {', '.join(self.implies)}")
        if self.default_value:
            lines.append(f"Default: {self.default_value}")
        return "\n".join(lines)


@dataclass
class KconfigDependencyGraph:
    """
    Dependency graph built from all Kconfig entries.

    For DeepThought: nodes that are densely connected but have
    no direct edge between them are potential Void locations.
    """
    entries: Dict[str, KconfigEntry] = field(default_factory=dict)

    def get_dependencies(self, config_name: str) -> List[str]:
        """Get all configs that CONFIG_X depends on."""
        entry = self.entries.get(config_name)
        if not entry:
            return []
        return entry.depends_on

    def get_dependents(self, config_name: str) -> List[str]:
        """Get all configs that depend on CONFIG_X."""
        return [
            name for name, entry in self.entries.items()
            if config_name in entry.depends_on
        ]

    def get_selected_by(self, config_name: str) -> List[str]:
        """Get all configs that select CONFIG_X."""
        return [
            name for name, entry in self.entries.items()
            if config_name in entry.selects
        ]

    def find_isolated_clusters(self) -> List[List[str]]:
        """
        Find groups of configs that are related but isolated
        from other groups. These boundaries are potential Voids.
        """
        visited = set()
        clusters = []

        def dfs(node: str, cluster: List[str]):
            if node in visited:
                return
            visited.add(node)
            cluster.append(node)
            entry = self.entries.get(node)
            if entry:
                for dep in entry.depends_on + entry.selects:
                    clean = re.sub(r"[^A-Z0-9_]", "", dep)
                    if clean:
                        dfs(clean, cluster)

        for name in self.entries:
            if name not in visited:
                cluster: List[str] = []
                dfs(name, cluster)
                if len(cluster) > 1:
                    clusters.append(cluster)

        return clusters


class KconfigParser(BaseParser):
    """
    Parser for Linux Kernel Kconfig files.

    Produces:
    1. One ParsedDocument per Kconfig entry (for RAG)
    2. A KconfigDependencyGraph (for Void detection)
    """

    def can_parse(self, result: CrawlResult) -> bool:
        file_path = result.metadata.get("file_path", "")
        return Path(file_path).name == "Kconfig"

    def parse(self, result: CrawlResult) -> List[ParsedDocument]:
        try:
            content = result.content.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Kconfig decode error: {e}")
            return []

        file_path = result.metadata.get("file_path", "unknown")
        entries = self._parse_kconfig(content, file_path)

        docs = []
        for entry in entries:
            docs.append(ParsedDocument(
                content=entry.to_text(),
                doc_type="kconfig_entry",
                source_name=result.source_name,
                uri=f"{result.source_name}:{file_path}:{entry.name}",
                metadata={
                    "config_name": f"CONFIG_{entry.name}",
                    "entry_type": entry.entry_type,
                    "depends_on": entry.depends_on,
                    "selects": entry.selects,
                    "implies": entry.implies,
                    "file_path": file_path,
                    "line_number": entry.line_number,
                    "subsystem": self._detect_subsystem(file_path),
                    "domain_tags": ["linux", "kernel", "kconfig"],
                    "parser_hint": "kconfig",
                }
            ))

        logger.debug(
            f"  Kconfig {file_path}: {len(entries)} entries"
        )
        return docs

    def parse_to_graph(
        self,
        results: List[CrawlResult],
    ) -> KconfigDependencyGraph:
        """
        Parse multiple Kconfig files into a dependency graph.
        Used by the Forager for structural Void detection.
        """
        graph = KconfigDependencyGraph()

        for result in results:
            if not self.can_parse(result):
                continue
            try:
                content = result.content.decode("utf-8", errors="replace")
                file_path = result.metadata.get("file_path", "")
                entries = self._parse_kconfig(content, file_path)
                for entry in entries:
                    graph.entries[entry.name] = entry
            except Exception as e:
                logger.warning(f"Kconfig graph error: {e}")

        logger.info(
            f"✅ Kconfig graph: {len(graph.entries)} entries"
        )
        return graph

    def _parse_kconfig(
        self,
        content: str,
        file_path: str,
    ) -> List[KconfigEntry]:
        """Parse Kconfig file content into KconfigEntry list."""

        entries = []
        current: Optional[KconfigEntry] = None
        in_help = False
        help_indent = 0
        line_number = 0

        for line in content.split("\n"):
            line_number += 1
            stripped = line.strip()

            # New config block
            if re.match(r"^config\s+\w+", stripped):
                if current:
                    entries.append(current)
                name = stripped.split()[1]
                current = KconfigEntry(
                    name=name,
                    entry_type="bool",
                    description="",
                    help_text="",
                    file_path=file_path,
                    line_number=line_number,
                )
                in_help = False
                continue

            if current is None:
                continue

            # Type + description
            type_match = re.match(
                r"^\s+(bool|tristate|int|string|hex)"
                r'(?:\s+"([^"]*)")?',
                line,
            )
            if type_match:
                current.entry_type = type_match.group(1)
                if type_match.group(2):
                    current.description = type_match.group(2)
                in_help = False
                continue

            # depends on
            dep_match = re.match(r"^\s+depends\s+on\s+(.+)", line)
            if dep_match:
                deps_raw = dep_match.group(1).strip()
                # Extract CONFIG names from boolean expressions
                deps = re.findall(r"[A-Z][A-Z0-9_]+", deps_raw)
                current.depends_on.extend(deps)
                in_help = False
                continue

            # select
            sel_match = re.match(r"^\s+select\s+(\w+)", line)
            if sel_match:
                current.selects.append(sel_match.group(1))
                in_help = False
                continue

            # imply
            imp_match = re.match(r"^\s+imply\s+(\w+)", line)
            if imp_match:
                current.implies.append(imp_match.group(1))
                in_help = False
                continue

            # default
            def_match = re.match(r"^\s+default\s+(.+)", line)
            if def_match:
                current.default_value = def_match.group(1).strip()
                in_help = False
                continue

            # help / ---help---
            if re.match(r"^\s+(help|---help---)", stripped):
                in_help = True
                # Detect indentation level of help text
                help_indent = len(line) - len(line.lstrip()) + 2
                continue

            # Accumulate help text
            if in_help:
                if line.strip() == "":
                    current.help_text += "\n"
                elif len(line) - len(line.lstrip()) >= help_indent:
                    current.help_text += line.strip() + " "
                else:
                    in_help = False

        # Don't forget the last entry
        if current:
            entries.append(current)

        return entries

    def _detect_subsystem(self, file_path: str) -> str:
        """Detect subsystem from Kconfig file path."""
        path = file_path.lower()
        if "arch/x86" in path:
            return "x86"
        if "kernel/sched" in path:
            return "scheduler"
        if "mm/" in path:
            return "memory_management"
        if "net/" in path:
            return "networking"
        if "drivers/" in path:
            return "drivers"
        if "security/" in path:
            return "security"
        return "other"
