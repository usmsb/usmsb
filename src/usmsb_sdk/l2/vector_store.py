# -*- coding: utf-8 -*-
"""
VectorStore - 向量存储与检索

支持：
- ChromaDB 集成
- FAISS 集成
- 内存向量存储（无依赖版）
"""

import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class VectorEntry:
    """向量条目"""
    id: str
    vector: list[float]
    content: Any
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


class InMemoryVectorStore:
    """
    内存向量存储
    
    简单的向量存储，不依赖外部库。
    """
    
    def __init__(self, dim: int = 1536):
        self.dim = dim
        self.entries: dict[str, VectorEntry] = {}
    
    def add(self, vector: list[float], content: Any, metadata: dict | None = None) -> str:
        """添加向量"""
        if len(vector) != self.dim:
            raise ValueError(f"Vector dimension must be {self.dim}")
        
        entry_id = str(uuid.uuid4())
        entry = VectorEntry(
            id=entry_id,
            vector=vector,
            content=content,
            metadata=metadata or {}
        )
        
        self.entries[entry_id] = entry
        return entry_id
    
    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        """
        搜索相似向量
        
        使用余弦相似度。
        """
        if len(query_vector) != self.dim:
            raise ValueError(f"Query vector dimension must be {self.dim}")
        
        results = []
        
        for entry in self.entries.values():
            # 计算余弦相似度
            similarity = self._cosine_similarity(query_vector, entry.vector)
            results.append({
                "id": entry.id,
                "content": entry.content,
                "metadata": entry.metadata,
                "similarity": similarity,
            })
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results[:top_k]
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a[i] * b[i] for i in range(len(a)))
        norm_a = sum(a[i] * a[i] for i in range(len(a))) ** 0.5
        norm_b = sum(b[i] * b[i] for i in range(len(b))) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    def delete(self, entry_id: str) -> bool:
        """删除条目"""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False
    
    def clear(self) -> None:
        """清空"""
        self.entries.clear()
    
    def count(self) -> int:
        """条目数量"""
        return len(self.entries)


class VectorStore:
    """
    统一向量存储接口
    
    支持多种后端：
    - memory: 内存存储
    - chroma: ChromaDB
    - faiss: FAISS
    """
    
    def __init__(
        self,
        backend: str = "memory",
        dim: int = 1536,
        persist_dir: str | None = None,
        collection_name: str = "default"
    ):
        self.backend = backend
        self.dim = dim
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        
        # 初始化后端
        if backend == "memory":
            self._backend = InMemoryVectorStore(dim=dim)
        elif backend == "chroma":
            self._backend = self._init_chroma()
        elif backend == "faiss":
            self._backend = self._init_faiss()
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    def _init_chroma(self):
        """初始化 ChromaDB"""
        try:
            import chromadb
            client = chromadb.Client()
            collection = client.create_collection(self.collection_name)
            
            class ChromaBackend:
                def __init__(self, collection):
                    self.collection = collection
                
                def add(self, vector, content, metadata):
                    entry_id = str(uuid.uuid4())
                    self.collection.add(
                        embeddings=[vector],
                        documents=[str(content)],
                        metadatas=[metadata or {}],
                        ids=[entry_id]
                    )
                    return entry_id
                
                def search(self, query_vector, top_k):
                    results = self.collection.query(
                        query_embeddings=[query_vector],
                        n_results=top_k
                    )
                    return [
                        {
                            "id": results["ids"][0][i],
                            "content": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "distance": results["distances"][0][i],
                        }
                        for i in range(len(results["ids"][0]))
                    ]
            
            return ChromaBackend(collection)
        
        except ImportError:
            print("[VectorStore] ChromaDB not installed, falling back to memory")
            return InMemoryVectorStore(dim=self.dim)
    
    def _init_faiss(self):
        """初始化 FAISS"""
        try:
            import faiss
            import numpy as np
            
            index = faiss.IndexFlatIP(self.dim)  # Inner Product (cosine sim with normalized vectors)
            
            class FaissBackend:
                def __init__(self, index, dim):
                    self.index = index
                    self.dim = dim
                    self.entries = {}
                    self._id_counter = 0
                
                def add(self, vector, content, metadata):
                    # 归一化
                    norm = sum(v*v for v in vector) ** 0.5
                    normalized = [v/norm for v in vector] if norm > 0 else vector
                    
                    arr = np.array([normalized], dtype=np.float32)
                    self.index.add(arr)
                    
                    entry_id = str(self._id_counter)
                    self._id_counter += 1
                    
                    self.entries[entry_id] = {
                        "content": content,
                        "metadata": metadata or {}
                    }
                    return entry_id
                
                def search(self, query_vector, top_k):
                    norm = sum(v*v for v in query_vector) ** 0.5
                    normalized = [v/norm for v in query_vector] if norm > 0 else query_vector
                    
                    arr = np.array([normalized], dtype=np.float32)
                    distances, indices = self.index.search(arr, top_k)
                    
                    results = []
                    for i, idx in enumerate(indices[0]):
                        if idx < 0:
                            continue
                        entry_id = str(idx)
                        if entry_id in self.entries:
                            results.append({
                                "id": entry_id,
                                "content": self.entries[entry_id]["content"],
                                "metadata": self.entries[entry_id]["metadata"],
                                "similarity": float(distances[0][i]),
                            })
                    return results
            
            return FaissBackend(index, self.dim)
        
        except ImportError:
            print("[VectorStore] FAISS not installed, falling back to memory")
            return InMemoryVectorStore(dim=self.dim)
    
    def add(
        self,
        content: Any,
        vector: list[float] | None = None,
        metadata: dict | None = None,
        text: str | None = None
    ) -> str:
        """
        添加内容
        
        如果没有提供 vector，会使用 text 生成 embedding。
        """
        if vector is None and text:
            vector = self._embed_text(text)
        
        if vector is None:
            raise ValueError("Either vector or text must be provided")
        
        return self._backend.add(vector, content, metadata)
    
    def search(
        self,
        query_vector: list[float] | None = None,
        query_text: str | None = None,
        top_k: int = 5
    ) -> list[dict]:
        """
        搜索
        
        Args:
            query_vector: 查询向量
            query_text: 查询文本（会自动生成向量）
            top_k: 返回数量
            
        Returns:
            list of {id, content, metadata, similarity}
        """
        if query_vector is None and query_text:
            query_vector = self._embed_text(query_text)
        
        if query_vector is None:
            raise ValueError("Either query_vector or query_text must be provided")
        
        return self._backend.search(query_vector, top_k)
    
    def _embed_text(self, text: str) -> list[float]:
        """
        生成文本 embedding
        
        简化实现：使用 hash 生成伪向量。
        实际应调用 OpenAI/LocalAI 等嵌入 API。
        """
        # 简化：基于文本生成固定维度的向量
        import hashlib
        
        # 使用 MD5 hash 作为伪随机种子
        hash_bytes = hashlib.md5(text.encode()).digest()
        
        # 将 hash 转换为固定维度的浮点数向量
        vector = []
        for i in range(self.dim):
            byte_idx = i % len(hash_bytes)
            value = (hash_bytes[byte_idx] / 255.0 - 0.5) * 2  # 归一化到 [-1, 1]
            vector.append(value)
        
        return vector
    
    def delete(self, entry_id: str) -> bool:
        """删除"""
        return self._backend.delete(entry_id)
    
    def count(self) -> int:
        """数量"""
        return self._backend.count()
    
    def __repr__(self) -> str:
        return f"VectorStore(backend={self.backend}, dim={self.dim}, count={self.count()})"
