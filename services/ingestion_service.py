"""
services/ingestion_service.py

The Orchestrator. 
Ties together Crawlers, Parsers, Chunkers, and the Vector Store.
"""

import json
import re
from typing import List
from loguru import logger

from data_collection.crawler.base_crawler import SourceType, DataSource, CrawlResult
from data_collection.crawler.git_crawler import GitCrawler
from data_collection.crawler.pdf_crawler import PDFCrawler
from data_collection.crawler.dataset_crawler import KaggleArXivCrawler

from data_collection.parser.base_parser import ParsedDocument
from data_collection.parser.code_parser import CodeParser
from data_collection.chunker.code_chunker import CodeChunker

from vectordb.store import DeepThoughtVectorStore, CollectionName, Document


def clean_metadata(metadata: dict) -> dict:
    """Clean metadata dictionary to be ChromaDB compatible."""
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            cleaned[key] = [str(v) if not isinstance(v, (str, int, float)) else v for v in value]
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


PDF_NOISE_LINE_RE = re.compile(
    r"^(?:document\s*#:|page\s+\d+|copyright|intel\(|examples?$)\b",
    re.IGNORECASE,
)


def build_pdf_page_title(source_name: str, page_num: int, text: str) -> str:
    """Build a semantic label for a PDF page from its visible heading text."""
    for raw_line in str(text or "").splitlines():
        line = " ".join(raw_line.split()).strip("-: ")
        if not line:
            continue

        if re.match(r"^Document\s*#:", line, flags=re.IGNORECASE):
            continue

        # Remove leading pagination boilerplate but keep the substantive heading.
        line = re.sub(r"^\d+[-–]\d+\s+", "", line).strip("-: ")
        if not line:
            continue
        if PDF_NOISE_LINE_RE.match(line):
            continue

        return f"{source_name} | {line[:120]}"

    return f"{source_name} page {page_num}"


class IngestionService:
    def __init__(self):
        self.db = DeepThoughtVectorStore()
        self.code_parser = CodeParser()
        self.chunker = CodeChunker(max_tokens=512)

    async def ingest_source(self, source: DataSource):
        """Main pipeline: Crawl -> Parse -> Chunk -> Store"""
        logger.info(f"⚙️ Initializing pipeline for source: {source.name}")

        crawler = self._get_crawler(source.source_type)
        if not crawler:
            return

        collection_name = self._get_target_collection(source)
        total_chunks_added = 0
        file_count = 0

        # 🌟 開始流式處理
        async for result in crawler.crawl(source):
            # 🌟 新增：針對「單個檔案」的保護罩
            try:
                if not result.is_ok:
                    continue

                # Parse
                docs = self._parse_result(result, source)
                if not docs:
                    continue

                # Chunk
                chunks = self.chunker.chunk_many(docs)
                if not chunks:
                    continue

                # Convert & Clean
                store_docs = [
                    Document(
                        content=chunk.content,
                        metadata=clean_metadata(chunk.metadata),
                    )
                    for chunk in chunks
                ]

                # Store
                added = self.db.add_documents(store_docs, collection_name)
                total_chunks_added += added
                file_count += 1

                if file_count % 100 == 0:
                    logger.info(f"  ... {source.name} Progress: {file_count} files | {total_chunks_added} chunks")

            except Exception as e:
                # 🌟 這裡就是你的要求：錯了就紀錄，然後跳過咩！
                file_info = result.metadata.get('file_path', result.uri)
                logger.error(f"  ⚠️ Skipping {file_info} due to error: {e}")
                # 這裡不 raise，迴圈會繼續處理下一個 result
                continue

        logger.info(f"🎉 Completed {source.name} | Total files: {file_count} | Total chunks: {total_chunks_added}")

    def _get_crawler(self, source_type: SourceType):
        if source_type == SourceType.GIT_REPO:
            return GitCrawler()
        elif source_type == SourceType.PDF_SPEC:
            return PDFCrawler()
        elif source_type == SourceType.LOCAL_DATASET:
            return KaggleArXivCrawler()
        return None

    def _get_target_collection(self, source: DataSource) -> CollectionName:
        if source.name == "linux_kernel":
            return CollectionName.KERNEL_SOURCE
        elif "intel" in source.name:
            return CollectionName.HARDWARE_SPECS
        elif source.name == "arxiv_kaggle":
            return CollectionName.PAPERS
        return CollectionName.KERNEL_DISCUSSION

    def _parse_result(self, result: CrawlResult, source: DataSource) -> List[ParsedDocument]:
        """Route to the correct parser based on source type."""
        
        # 處理 Git Repo (C/C++/Python)
        if source.source_type == SourceType.GIT_REPO:
            return self.code_parser.parse(result)
            
        # 處理 ArXiv JSONL
        elif source.source_type == SourceType.LOCAL_DATASET:
            try:
                paper = json.loads(result.content.decode("utf-8"))
                # 將 Title, Authors, Abstract 壓成字串讓 Embedder 吃
                content = (
                    f"TITLE: {paper.get('title', '')}\n"
                    f"AUTHORS: {paper.get('authors', '')}\n\n"
                    f"ABSTRACT:\n{paper.get('abstract', paper.get('summary', ''))}"
                )
                return [ParsedDocument(
                    content=content,
                    doc_type="paper",
                    source_name=source.name,
                    uri=result.uri,
                    metadata=result.metadata
                )]
            except Exception as e:
                logger.warning(f"Failed to parse ArXiv JSON: {e}")
                return []
                
        # 處理 PDF (簡易版文字提取)
        elif source.source_type == SourceType.PDF_SPEC:
            try:
                import pypdf
                import io
                pdf_file = io.BytesIO(result.content)
                reader = pypdf.PdfReader(pdf_file)
                
                docs = []
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text or not text.strip():
                        continue

                    page_metadata = result.metadata.copy()
                    page_metadata["page_num"] = page_num + 1
                    page_metadata["title"] = build_pdf_page_title(
                        source_name=source.name,
                        page_num=page_num + 1,
                        text=text,
                    )
                    
                    docs.append(ParsedDocument(
                        content=text,
                        doc_type="pdf_page",
                        source_name=source.name,
                        uri=f"{result.uri}#page={page_num+1}",
                        metadata=page_metadata
                    ))
                    
                logger.info(f"  📄 Splitted PDF into {len(docs)} pages.")
                return docs
                
            except ImportError:
                logger.error("pip install pypdf to parse PDFs!")
                return []
            except Exception as e:
                logger.warning(f"Failed to parse PDF: {e}")
                return []
