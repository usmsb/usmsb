"""
Knowledge Base Adapters

This module provides adapters for different knowledge base systems:
- IKnowledgeBaseAdapter: Base interface for all knowledge base adapters
- VectorDBKnowledgeBaseAdapter: Adapter for vector databases (Pinecone, Weaviate, Milvus, Chroma)
- GraphDBKnowledgeBaseAdapter: Adapter for graph databases (Neo4j, ArangoDB)

These adapters enable RAG (Retrieval-Augmented Generation) capabilities.
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeSourceType(StrEnum):
    """Types of knowledge sources."""
    VECTOR_DB = "vector_db"
    GRAPH_DB = "graph_db"
    DOCUMENT_STORE = "document_store"
    HYBRID = "hybrid"


@dataclass
class KnowledgeEntry:
    """A single knowledge entry."""
    entry_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    score: float = 0.0
    source: str = ""


@dataclass
class KnowledgeQueryResult:
    """Result of a knowledge query."""
    query: str
    entries: list[KnowledgeEntry] = field(default_factory=list)
    total_count: int = 0
    query_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class IKnowledgeBaseAdapter(ABC):
    """
    知识库适配器接口

    封装知识检索、知识图谱查询等能力。
    """

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize the knowledge base connection."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the knowledge base connection."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the knowledge base is available."""
        pass

    @abstractmethod
    async def query_knowledge(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> KnowledgeQueryResult:
        """
        Query the knowledge base.

        Args:
            query: The query string
            context: Additional context for the query
            **kwargs: Additional parameters

        Returns:
            KnowledgeQueryResult with matching entries
        """
        pass

    @abstractmethod
    async def retrieve_facts(
        self,
        entity: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> list[str]:
        """
        Retrieve facts about an entity.

        Args:
            entity: The entity to retrieve facts about
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            List of fact strings
        """
        pass

    @abstractmethod
    async def add_knowledge(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        **kwargs
    ) -> str:
        """
        Add knowledge to the knowledge base.

        Args:
            content: The content to add
            metadata: Metadata associated with the content
            **kwargs: Additional parameters

        Returns:
            ID of the added entry
        """
        pass

    @abstractmethod
    async def delete_knowledge(self, entry_id: str) -> bool:
        """Delete knowledge by ID."""
        pass

    @abstractmethod
    async def update_knowledge(
        self,
        entry_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update knowledge entry."""
        pass


# ============== Vector DB Adapter ==============

class VectorDBKnowledgeBaseAdapter(IKnowledgeBaseAdapter):
    """
    向量数据库知识库适配器

    支持与主流向量数据库集成，进行语义搜索和RAG。
    支持多种后端：ChromaDB, Pinecone, Weaviate, Milvus, FAISS
    """

    def __init__(
        self,
        db_type: str = "chroma",
        embedding_function: callable | None = None,
        llm_adapter: Any | None = None,
    ):
        """
        Initialize Vector DB adapter.

        Args:
            db_type: Type of vector database ("chroma", "pinecone", "weaviate", "milvus", "faiss")
            embedding_function: Function to generate embeddings
            llm_adapter: LLM adapter for generating embeddings
        """
        self.db_type = db_type
        self.embedding_function = embedding_function
        self.llm_adapter = llm_adapter
        self._client = None
        self._collection = None
        self._initialized = False

        # In-memory fallback
        self._memory_store: dict[str, dict[str, Any]] = {}
        self._memory_embeddings: dict[str, list[float]] = {}

    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize the vector database connection."""
        try:
            if self.db_type == "chroma":
                return await self._init_chroma(config)
            elif self.db_type == "pinecone":
                return await self._init_pinecone(config)
            elif self.db_type == "weaviate":
                return await self._init_weaviate(config)
            elif self.db_type == "milvus":
                return await self._init_milvus(config)
            else:
                # Use in-memory store
                logger.info("Using in-memory vector store")
                self._initialized = True
                return True

        except Exception as e:
            logger.error(f"Failed to initialize vector DB: {e}")
            return False

    async def _init_chroma(self, config: dict[str, Any]) -> bool:
        """Initialize ChromaDB."""
        try:
            import chromadb

            persist_dir = config.get("persist_directory", "./chroma_db")
            collection_name = config.get("collection_name", "usmsb_knowledge")

            self._client = chromadb.PersistentClient(path=persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "USMSB Knowledge Base"}
            )

            self._initialized = True
            logger.info(f"ChromaDB initialized: {collection_name}")
            return True

        except ImportError:
            logger.warning("ChromaDB not installed, using in-memory store")
            return True
        except Exception as e:
            logger.error(f"ChromaDB init error: {e}")
            return False

    async def _init_pinecone(self, config: dict[str, Any]) -> bool:
        """Initialize Pinecone."""
        try:
            import pinecone

            api_key = config.get("api_key")
            environment = config.get("environment", "us-west1-gcp")
            index_name = config.get("index_name", "usmsb-knowledge")

            if not api_key:
                logger.warning("Pinecone API key not provided")
                return False

            pinecone.init(api_key=api_key, environment=environment)

            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=config.get("dimension", 1536),
                    metric="cosine"
                )

            self._client = pinecone.Index(index_name)
            self._initialized = True
            logger.info(f"Pinecone initialized: {index_name}")
            return True

        except ImportError:
            logger.warning("Pinecone not installed, using in-memory store")
            return True
        except Exception as e:
            logger.error(f"Pinecone init error: {e}")
            return False

    async def _init_weaviate(self, config: dict[str, Any]) -> bool:
        """Initialize Weaviate."""
        try:
            import weaviate

            url = config.get("url", "http://localhost:8080")
            self._client = weaviate.Client(url)

            # Create schema if not exists
            class_obj = {
                "class": "USMSBKnowledge",
                "properties": [
                    {"name": "content", "dataType": ["text"]},
                    {"name": "metadata", "dataType": ["object"]},
                ]
            }

            if not self._client.schema.exists("USMSBKnowledge"):
                self._client.schema.create_class(class_obj)

            self._initialized = True
            logger.info(f"Weaviate initialized: {url}")
            return True

        except ImportError:
            logger.warning("Weaviate not installed, using in-memory store")
            return True
        except Exception as e:
            logger.error(f"Weaviate init error: {e}")
            return False

    async def _init_milvus(self, config: dict[str, Any]) -> bool:
        """Initialize Milvus."""
        try:
            from pymilvus import (
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                connections,
                utility,
            )

            host = config.get("host", "localhost")
            port = config.get("port", "19530")
            collection_name = config.get("collection_name", "usmsb_knowledge")

            connections.connect("default", host=host, port=port)

            if utility.has_collection(collection_name):
                self._collection = Collection(collection_name)
            else:
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=config.get("dimension", 1536)),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                ]
                schema = CollectionSchema(fields=fields, description="USMSB Knowledge Base")
                self._collection = Collection(collection_name, schema)

            self._initialized = True
            logger.info(f"Milvus initialized: {collection_name}")
            return True

        except ImportError:
            logger.warning("pymilvus not installed, using in-memory store")
            return True
        except Exception as e:
            logger.error(f"Milvus init error: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the connection."""
        self._initialized = False
        self._client = None
        self._collection = None

    async def is_available(self) -> bool:
        """Check availability."""
        return self._initialized

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text."""
        if self.embedding_function:
            return self.embedding_function(text)

        if self.llm_adapter:
            try:
                return await self.llm_adapter.embed(text)
            except Exception as e:
                logger.error(f"Embedding error: {e}")

        # Fallback: simple hash-based embedding (not for production)
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes[:32]]

    async def query_knowledge(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
        **kwargs
    ) -> KnowledgeQueryResult:
        """Query the vector database."""
        start_time = time.time()
        entries = []

        try:
            query_embedding = await self._get_embedding(query)

            if self.db_type == "chroma" and self._collection:
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )

                for i, doc in enumerate(results.get("documents", [[]])[0]):
                    distance = results.get("distances", [[]])[0][i] if results.get("distances") else 0
                    score = 1 - distance  # Convert distance to similarity
                    if score >= min_score:
                        entries.append(KnowledgeEntry(
                            entry_id=results.get("ids", [[]])[0][i] if results.get("ids") else str(i),
                            content=doc,
                            metadata=results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {},
                            score=score,
                            source="chroma"
                        ))

            elif self.db_type == "pinecone" and self._client:
                results = self._client.query(
                    vector=query_embedding,
                    top_k=top_k,
                    include_metadata=True
                )

                for match in results.get("matches", []):
                    if match.get("score", 0) >= min_score:
                        entries.append(KnowledgeEntry(
                            entry_id=match["id"],
                            content=match.get("metadata", {}).get("content", ""),
                            metadata=match.get("metadata", {}),
                            score=match.get("score", 0),
                            source="pinecone"
                        ))

            else:
                # In-memory search
                entries = await self._memory_search(query_embedding, top_k, min_score)

        except Exception as e:
            logger.error(f"Query error: {e}")

        return KnowledgeQueryResult(
            query=query,
            entries=entries,
            total_count=len(entries),
            query_time=time.time() - start_time,
        )

    async def _memory_search(
        self,
        query_embedding: list[float],
        top_k: int,
        min_score: float
    ) -> list[KnowledgeEntry]:
        """Search in-memory store."""
        results = []

        for entry_id, data in self._memory_store.items():
            stored_embedding = self._memory_embeddings.get(entry_id, [])
            if stored_embedding:
                score = self._cosine_similarity(query_embedding, stored_embedding)
                if score >= min_score:
                    results.append(KnowledgeEntry(
                        entry_id=entry_id,
                        content=data.get("content", ""),
                        metadata=data.get("metadata", {}),
                        embedding=stored_embedding,
                        score=score,
                        source="memory"
                    ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(x ** 2 for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def retrieve_facts(
        self,
        entity: str,
        context: dict[str, Any] | None = None,
        top_k: int = 5,
        **kwargs
    ) -> list[str]:
        """Retrieve facts about an entity."""
        result = await self.query_knowledge(
            query=f"facts about {entity}",
            context=context,
            top_k=top_k,
            **kwargs
        )
        return [entry.content for entry in result.entries]

    async def add_knowledge(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        entry_id: str | None = None,
        **kwargs
    ) -> str:
        """Add knowledge to the vector database."""
        entry_id = entry_id or hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:16]
        embedding = await self._get_embedding(content)

        try:
            if self.db_type == "chroma" and self._collection:
                self._collection.add(
                    ids=[entry_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[metadata or {}]
                )
            elif self.db_type == "pinecone" and self._client:
                self._client.upsert(
                    vectors=[(entry_id, embedding, {"content": content, **(metadata or {})})]
                )
            else:
                # In-memory store
                self._memory_store[entry_id] = {
                    "content": content,
                    "metadata": metadata or {},
                }
                self._memory_embeddings[entry_id] = embedding

            logger.debug(f"Added knowledge: {entry_id}")
            return entry_id

        except Exception as e:
            logger.error(f"Add knowledge error: {e}")
            raise

    async def delete_knowledge(self, entry_id: str) -> bool:
        """Delete knowledge by ID."""
        try:
            if self.db_type == "chroma" and self._collection:
                self._collection.delete(ids=[entry_id])
            elif self.db_type == "pinecone" and self._client:
                self._client.delete(ids=[entry_id])
            else:
                self._memory_store.pop(entry_id, None)
                self._memory_embeddings.pop(entry_id, None)

            return True

        except Exception as e:
            logger.error(f"Delete knowledge error: {e}")
            return False

    async def update_knowledge(
        self,
        entry_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update knowledge entry."""
        try:
            # For vector DBs, usually need to delete and re-add
            if content:
                await self.delete_knowledge(entry_id)
                await self.add_knowledge(content, metadata, entry_id)
            return True

        except Exception as e:
            logger.error(f"Update knowledge error: {e}")
            return False

    async def batch_add(
        self,
        entries: list[dict[str, Any]]
    ) -> list[str]:
        """Add multiple entries at once."""
        entry_ids = []
        for entry in entries:
            entry_id = await self.add_knowledge(
                content=entry.get("content", ""),
                metadata=entry.get("metadata"),
            )
            entry_ids.append(entry_id)
        return entry_ids


# ============== Graph DB Adapter ==============

class GraphDBKnowledgeBaseAdapter(IKnowledgeBaseAdapter):
    """
    图数据库知识库适配器

    支持与图数据库集成，进行知识图谱查询和推理。
    支持 Neo4j, ArangoDB 等。
    """

    def __init__(self, db_type: str = "neo4j"):
        """
        Initialize Graph DB adapter.

        Args:
            db_type: Type of graph database ("neo4j", "arangodb")
        """
        self.db_type = db_type
        self._client = None
        self._initialized = False

        # In-memory fallback
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []

    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize the graph database connection."""
        try:
            if self.db_type == "neo4j":
                return await self._init_neo4j(config)
            elif self.db_type == "arangodb":
                return await self._init_arangodb(config)
            else:
                logger.info("Using in-memory graph store")
                self._initialized = True
                return True

        except Exception as e:
            logger.error(f"Failed to initialize graph DB: {e}")
            return False

    async def _init_neo4j(self, config: dict[str, Any]) -> bool:
        """Initialize Neo4j."""
        try:
            from neo4j import GraphDatabase

            uri = config.get("uri", "bolt://localhost:7687")
            user = config.get("user", "neo4j")
            password = config.get("password")

            self._client = GraphDatabase.driver(uri, auth=(user, password))

            # Test connection
            with self._client.session() as session:
                session.run("RETURN 1")

            self._initialized = True
            logger.info(f"Neo4j initialized: {uri}")
            return True

        except ImportError:
            logger.warning("neo4j not installed, using in-memory store")
            return True
        except Exception as e:
            logger.error(f"Neo4j init error: {e}")
            return False

    async def _init_arangodb(self, config: dict[str, Any]) -> bool:
        """Initialize ArangoDB."""
        try:
            from arango import ArangoClient

            host = config.get("host", "http://localhost:8529")
            database = config.get("database", "usmsb")
            username = config.get("username", "root")
            password = config.get("password", "")

            client = ArangoClient(hosts=host)
            self._client = client.db(database, username=username, password=password)

            self._initialized = True
            logger.info(f"ArangoDB initialized: {database}")
            return True

        except ImportError:
            logger.warning("python-arango not installed, using in-memory store")
            return True
        except Exception as e:
            logger.error(f"ArangoDB init error: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the connection."""
        if self._client and self.db_type == "neo4j":
            self._client.close()
        self._initialized = False
        self._client = None

    async def is_available(self) -> bool:
        """Check availability."""
        return self._initialized

    async def query_knowledge(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> KnowledgeQueryResult:
        """Query the graph database."""
        start_time = time.time()
        entries = []

        try:
            if self.db_type == "neo4j" and self._client:
                entries = await self._query_neo4j(query, context, **kwargs)
            elif self.db_type == "arangodb" and self._client:
                entries = await self._query_arangodb(query, context, **kwargs)
            else:
                entries = await self._query_memory(query, context, **kwargs)

        except Exception as e:
            logger.error(f"Query error: {e}")

        return KnowledgeQueryResult(
            query=query,
            entries=entries,
            total_count=len(entries),
            query_time=time.time() - start_time,
        )

    async def _query_neo4j(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> list[KnowledgeEntry]:
        """Query Neo4j."""
        entries = []

        with self._client.session() as session:
            # Full-text search
            cypher = """
            CALL db.index.fulltext.queryNodes('knowledge_index', $query)
            YIELD node, score
            RETURN node.id as id, node.content as content, node.metadata as metadata, score
            LIMIT 10
            """

            result = session.run(cypher, query=query)
            for record in result:
                entries.append(KnowledgeEntry(
                    entry_id=record["id"],
                    content=record["content"],
                    metadata=json.loads(record["metadata"]) if record["metadata"] else {},
                    score=record["score"],
                    source="neo4j"
                ))

        return entries

    async def _query_arangodb(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> list[KnowledgeEntry]:
        """Query ArangoDB."""
        entries = []

        aql = """
        FOR doc IN knowledge_view
        SEARCH ANALYZER(doc.content IN TOKENS(@query, 'text_en'), 'text_en')
        SORT BM25(doc) DESC
        LIMIT 10
        RETURN doc
        """

        cursor = self._client.aql.execute(aql, bind_vars={"query": query})
        for doc in cursor:
            entries.append(KnowledgeEntry(
                entry_id=doc["_key"],
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {}),
                score=doc.get("_score", 0),
                source="arangodb"
            ))

        return entries

    async def _query_memory(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> list[KnowledgeEntry]:
        """Query in-memory store."""
        entries = []
        query_lower = query.lower()

        for node_id, node in self._nodes.items():
            if query_lower in node.get("content", "").lower():
                entries.append(KnowledgeEntry(
                    entry_id=node_id,
                    content=node.get("content", ""),
                    metadata=node.get("properties", {}),
                    source="memory"
                ))

        return entries

    async def retrieve_facts(
        self,
        entity: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> list[str]:
        """Retrieve facts about an entity from the graph."""
        facts = []

        try:
            if self.db_type == "neo4j" and self._client:
                with self._client.session() as session:
                    cypher = """
                    MATCH (e:Entity {name: $entity})-[r]->(related)
                    RETURN type(r) as relation, related.name as related_entity, related.content as content
                    """
                    result = session.run(cypher, entity=entity)
                    for record in result:
                        fact = f"{entity} {record['relation']} {record['related_entity']}"
                        if record['content']:
                            fact += f": {record['content']}"
                        facts.append(fact)

            elif self.db_type == "arangodb" and self._client:
                aql = """
                FOR v, e, p IN 1..1 OUTBOUND @entity knowledge_edges
                RETURN CONCAT(p.vertices[0].name, ' ', e.type, ' ', v.name)
                """
                cursor = self._client.aql.execute(aql, bind_vars={"entity": entity})
                facts = list(cursor)

            else:
                # Memory store
                for edge in self._edges:
                    if edge.get("source") == entity or edge.get("target") == entity:
                        facts.append(f"{edge['source']} {edge['type']} {edge['target']}")

        except Exception as e:
            logger.error(f"Retrieve facts error: {e}")

        return facts

    async def add_knowledge(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        entry_id: str | None = None,
        entity_type: str = "Knowledge",
        **kwargs
    ) -> str:
        """Add knowledge as a node in the graph."""
        entry_id = entry_id or hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:16]

        try:
            if self.db_type == "neo4j" and self._client:
                with self._client.session() as session:
                    session.run(
                        f"""
                        CREATE (n:{entity_type} {{
                            id: $id,
                            content: $content,
                            metadata: $metadata,
                            created_at: timestamp()
                        }})
                        """,
                        id=entry_id,
                        content=content,
                        metadata=json.dumps(metadata or {}),
                    )

            elif self.db_type == "arangodb" and self._client:
                collection = self._client.collection("knowledge_nodes")
                collection.insert({
                    "_key": entry_id,
                    "content": content,
                    "metadata": metadata or {},
                    "type": entity_type,
                })

            else:
                self._nodes[entry_id] = {
                    "content": content,
                    "properties": metadata or {},
                    "type": entity_type,
                }

            return entry_id

        except Exception as e:
            logger.error(f"Add knowledge error: {e}")
            raise

    async def delete_knowledge(self, entry_id: str) -> bool:
        """Delete knowledge node."""
        try:
            if self.db_type == "neo4j" and self._client:
                with self._client.session() as session:
                    session.run("MATCH (n {id: $id}) DETACH DELETE n", id=entry_id)

            elif self.db_type == "arangodb" and self._client:
                collection = self._client.collection("knowledge_nodes")
                collection.delete(entry_id)

            else:
                self._nodes.pop(entry_id, None)
                self._edges = [
                    e for e in self._edges
                    if e.get("source") != entry_id and e.get("target") != entry_id
                ]

            return True

        except Exception as e:
            logger.error(f"Delete knowledge error: {e}")
            return False

    async def update_knowledge(
        self,
        entry_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update knowledge node."""
        try:
            if self.db_type == "neo4j" and self._client:
                with self._client.session() as session:
                    updates = []
                    params = {"id": entry_id}
                    if content:
                        updates.append("n.content = $content")
                        params["content"] = content
                    if metadata:
                        updates.append("n.metadata = $metadata")
                        params["metadata"] = json.dumps(metadata)

                    if updates:
                        session.run(
                            f"MATCH (n {{id: $id}}) SET {', '.join(updates)}",
                            **params
                        )

            else:
                if entry_id in self._nodes:
                    if content:
                        self._nodes[entry_id]["content"] = content
                    if metadata:
                        self._nodes[entry_id]["properties"].update(metadata)

            return True

        except Exception as e:
            logger.error(f"Update knowledge error: {e}")
            return False

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Add a relationship between two nodes."""
        try:
            if self.db_type == "neo4j" and self._client:
                with self._client.session() as session:
                    session.run(
                        f"""
                        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
                        CREATE (source)-[r:{relation_type} $properties]->(target)
                        """,
                        source_id=source_id,
                        target_id=target_id,
                        properties=properties or {},
                    )

            elif self.db_type == "arangodb" and self._client:
                collection = self._client.collection("knowledge_edges")
                collection.insert({
                    "_from": f"knowledge_nodes/{source_id}",
                    "_to": f"knowledge_nodes/{target_id}",
                    "type": relation_type,
                    **(properties or {}),
                })

            else:
                self._edges.append({
                    "source": source_id,
                    "target": target_id,
                    "type": relation_type,
                    "properties": properties or {},
                })

            return True

        except Exception as e:
            logger.error(f"Add relation error: {e}")
            return False

    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3,
    ) -> list[dict[str, Any]]:
        """Find path between two nodes."""
        paths = []

        try:
            if self.db_type == "neo4j" and self._client:
                with self._client.session() as session:
                    result = session.run(
                        """
                        MATCH path = shortestPath((start {id: $start_id})-[*..{max_depth}]-(end {id: $end_id}))
                        RETURN [node in nodes(path) | node.id] as nodes,
                               [rel in relationships(path) | type(rel)] as relations
                        """.replace("{max_depth}", str(max_depth)),
                        start_id=start_id,
                        end_id=end_id,
                    )
                    for record in result:
                        paths.append({
                            "nodes": record["nodes"],
                            "relations": record["relations"],
                        })

            else:
                # Simple BFS for in-memory
                paths = self._find_path_memory(start_id, end_id, max_depth)

        except Exception as e:
            logger.error(f"Find path error: {e}")

        return paths

    def _find_path_memory(
        self,
        start_id: str,
        end_id: str,
        max_depth: int,
    ) -> list[dict[str, Any]]:
        """Find path in memory store using BFS."""
        # Build adjacency list
        adj = defaultdict(list)
        for edge in self._edges:
            adj[edge["source"]].append((edge["target"], edge["type"]))
            adj[edge["target"]].append((edge["source"], edge["type"]))

        # BFS
        queue = [(start_id, [start_id], [])]
        visited = {start_id}
        paths = []

        while queue:
            current, path, relations = queue.pop(0)

            if current == end_id:
                paths.append({"nodes": path, "relations": relations})
                continue

            if len(path) > max_depth:
                continue

            for neighbor, rel_type in adj[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((
                        neighbor,
                        path + [neighbor],
                        relations + [rel_type]
                    ))

        return paths
