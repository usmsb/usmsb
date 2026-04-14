# -*- coding: utf-8 -*-
"""
RAG - 检索增强生成

RAG = Retrieval + Augmented + Generation

功能：
- 文档分块
- 向量检索
- 上下文组装
"""

import uuid
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Chunk:
    """文档块"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: dict = field(default_factory=dict)
    chunk_index: int = 0
    total_chunks: int = 1
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Document:
    """文档"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""
    chunks: list[Chunk] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "chunk_count": len(self.chunks),
            "metadata": self.metadata,
        }


class TextSplitter:
    """
    文本分块器
    
    支持多种分块策略：
    - 固定长度
    - 句子边界
    - 段落边界
    - 递归分块
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        split_by: str = "sentence"  # sentence, paragraph, token
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.split_by = split_by
    
    def split_text(self, text: str) -> list[str]:
        """
        分块文本
        
        Args:
            text: 输入文本
            
        Returns:
            list[str]: 文本块列表
        """
        if self.split_by == "sentence":
            return self._split_by_sentence(text)
        elif self.split_by == "paragraph":
            return self._split_by_paragraph(text)
        elif self.split_by == "token":
            return self._split_by_token(text)
        else:
            return self._split_fixed(text)
    
    def _split_by_sentence(self, text: str) -> list[str]:
        """按句子分块"""
        # 句子结束符
        sentence_endings = re.compile(r'[。！？\.!?]+')
        
        # 分割句子
        sentences = sentence_endings.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 合并成块
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # 重叠
                words = current_chunk.split()
                overlap_words = words[-self.chunk_overlap//10:] if len(words) > 5 else []
                current_chunk = " ".join(overlap_words) + " " + sentence + " "
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_paragraph(self, text: str) -> list[str]:
        """按段落分块"""
        paragraphs = text.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_token(self, text: str) -> list[str]:
        """按 token 分块（简化为按单词数）"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunks.append(" ".join(chunk_words))
        
        return chunks
    
    def _split_fixed(self, text: str) -> list[str]:
        """固定长度分块"""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunks.append(text[i:i + self.chunk_size])
        return chunks


class RAG:
    """
    RAG - 检索增强生成
    
    完整的 RAG 管道：
    1. 文档 -> 分块
    2. 块 -> 向量化
    3. 查询 -> 检索 -> 组装上下文
    
    使用方式：
    ```python
    rag = RAG(vector_store)
    
    # 添加文档
    doc = rag.add_document("标题", "长文本内容...")
    
    # 检索
    results = rag.retrieve("查询文本", top_k=5)
    
    # 组装上下文
    context = rag.assemble_context(results)
    ```
    """
    
    def __init__(
        self,
        vector_store: Any,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        embedder=None  # 嵌入函数
    ):
        self.vector_store = vector_store
        self.splitter = TextSplitter(chunk_size, chunk_overlap)
        self.embedder = embedder or self._default_embedder
        
        # 文档存储
        self.documents: dict[str, Document] = {}
        
        # Chunk ID 到 Document ID 的映射
        self.chunk_to_doc: dict[str, str] = {}
    
    def _default_embedder(self, text: str) -> list[float]:
        """默认嵌入函数"""
        return self.vector_store._embed_text(text)
    
    def add_document(
        self,
        title: str,
        content: str,
        metadata: dict | None = None
    ) -> Document:
        """
        添加文档
        
        Args:
            title: 文档标题
            content: 文档内容
            metadata: 元数据
            
        Returns:
            Document
        """
        # 创建文档
        doc = Document(
            title=title,
            content=content,
            metadata=metadata or {}
        )
        
        # 分块
        chunks = self.splitter.split_text(content)
        
        # 向量化并存储
        for i, chunk_text in enumerate(chunks):
            chunk = Chunk(
                content=chunk_text,
                metadata={
                    "title": title,
                    "chunk_index": i,
                    **metadata or {}
                },
                chunk_index=i,
                total_chunks=len(chunks)
            )
            
            doc.chunks.append(chunk)
            
            # 向量化
            vector = self.embedder(chunk_text)
            
            # 存储到向量数据库
            chunk_id = self.vector_store.add(
                content=chunk_text,
                vector=vector,
                metadata=chunk.metadata
            )
            
            # 映射
            self.chunk_to_doc[chunk_id] = doc.id
        
        self.documents[doc.id] = doc
        
        return doc
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: dict | None = None
    ) -> list[dict]:
        """
        检索相关块
        
        Args:
            query: 查询文本
            top_k: 返回数量
            filter_metadata: 元数据过滤
            
        Returns:
            list of {chunk_id, document, content, metadata, similarity}
        """
        # 向量化查询
        query_vector = self.embedder(query)
        
        # 搜索
        results = self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k
        )
        
        # 增强结果
        enhanced = []
        for r in results:
            chunk_id = r["id"]
            doc_id = self.chunk_to_doc.get(chunk_id)
            doc = self.documents.get(doc_id) if doc_id else None
            
            enhanced.append({
                "chunk_id": chunk_id,
                "document": doc.to_dict() if doc else None,
                "content": r["content"],
                "metadata": r.get("metadata", {}),
                "similarity": r.get("similarity", 0.0),
            })
        
        return enhanced
    
    def assemble_context(
        self,
        retrieved: list[dict],
        max_length: int = 2000,
        include_source: bool = True
    ) -> str:
        """
        组装上下文
        
        Args:
            retrieved: retrieve() 返回的结果
            max_length: 最大长度
            include_source: 是否包含来源信息
            
        Returns:
            str: 组装好的上下文
        """
        context_parts = []
        total_length = 0
        
        for r in retrieved:
            chunk_text = r["content"]
            metadata = r.get("metadata", {})
            
            # 添加来源信息
            if include_source and metadata.get("title"):
                part = f"[来源: {metadata['title']}]\n{chunk_text}\n"
            else:
                part = chunk_text + "\n\n"
            
            # 检查长度
            if total_length + len(part) > max_length:
                break
            
            context_parts.append(part)
            total_length += len(part)
        
        return "".join(context_parts)
    
    def query(
        self,
        query: str,
        top_k: int = 5,
        max_context_length: int = 2000
    ) -> dict:
        """
        完整的 RAG 查询
        
        Args:
            query: 查询
            top_k: 检索数量
            max_context_length: 最大上下文长度
            
        Returns:
            dict: {
                "context": 组装好的上下文,
                "sources": 来源列表,
                "retrieved": 原始检索结果
            }
        """
        # 检索
        retrieved = self.retrieve(query, top_k)
        
        # 组装上下文
        context = self.assemble_context(retrieved, max_context_length)
        
        # 来源列表
        sources = []
        for r in retrieved:
            metadata = r.get("metadata", {})
            if metadata.get("title"):
                sources.append({
                    "title": metadata["title"],
                    "chunk_index": metadata.get("chunk_index", 0),
                })
        
        return {
            "context": context,
            "sources": sources,
            "retrieved": retrieved,
        }
    
    def get_document(self, doc_id: str) -> Document | None:
        """获取文档"""
        return self.documents.get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id not in self.documents:
            return False
        
        # 删除向量
        doc = self.documents[doc_id]
        for chunk in doc.chunks:
            # 找到 chunk_id 并删除
            for cid, did in list(self.chunk_to_doc.items()):
                if did == doc_id:
                    self.vector_store.delete(cid)
                    del self.chunk_to_doc[cid]
        
        del self.documents[doc_id]
        return True
    
    def __repr__(self) -> str:
        return f"RAG(docs={len(self.documents)}, chunks={len(self.chunk_to_doc)})"
