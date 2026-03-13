# Smart Knowledge Memory Management System Design

**[English](#smart-knowledge-memory-management-system-design) | [中文](#智能知识记忆管理系统设计方案)**

> Version: v3.0 (Intelligent Enhancement Edition)
> Date: 2026-02-23
> Status: Based on Technical Expert Debate

---

## 1. Core Design Philosophy

### 1.1 Design Goal

**Not making a "good boy AI" (bound by rules), but making a "super smart AI" (truly intelligent memory system)**

| V2 Design (Wrong Direction) | V3 Design (Correct Direction) |
|----------------------------|------------------------------|
| Value Constraint Layer | Intelligent Memory Architecture |
| Safety Boundary | Context Understanding |
| Gradual Autonomy | Active Reasoning |
| Human Approval | User Intent Recognition |
| Fallibilism | Precise Recall |

### 1.2 Core Problems (Expert Consensus)

Through debate among 10+ technical experts, core problems identified:

1. **Semantic Understanding** - How to achieve efficient, scalable semantic knowledge storage and retrieval
2. **Context Association** - How to align retrieval results with current task context
3. **Knowledge Organization** - How to organize entity relationships using knowledge graphs, support reasoning
4. **User Intent** - How to understand user true intent, provide precise memory feedback
5. **Vector Recall** - How to achieve high precision, high recall rate in massive information
6. **Logical Reasoning** - How to perform effective logical reasoning and consistency checking
7. **Causal Reasoning** - How to understand causal relationships, perform counterfactual reasoning
8. **Spatial Reasoning** - How to handle spatial relationships and location understanding
9. **Tool Calling** - How to intelligently select and orchestrate tools
10. **AGI Architecture** - How to form a unified "neural-symbolic hybrid system"

### 1.3 AGI Core Architecture (Expert Consensus)

Based on expert discussion, AGI core architecture should be:

> **"Event-driven neural-symbolic hybrid system"**
> - Dynamic cognitive graph as bone
> - Perception flow as flesh
> - Causal reasoning as brain
> - Tool calling as hands
> - Semantic understanding as blood, permeating all processes

```
User Input → Intent Recognition → Graph Activation → Causal Reasoning → Decision → Tool Execution → Feedback Loop → Graph Update
    ↑                                                                      ↓
    └────────────────────────── Continuous Evolution Loop ←─────────────────────────────────┘
```

---

## 2. System Architecture

### 2.1 Overall Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Smart Knowledge Memory Management System                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           User Interaction Layer                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   Query    │  │ Explicit    │  │  Implicit   │  │   Intent    │    │   │
│  │  │  Input     │  │ Memory      │  │ Feedback    │  │ Understanding│    │   │
│  │  │            │  │ Request     │  │ Capture     │  │   Engine    │    │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │   │
│  └─────────┼────────────────┼────────────────┼────────────────┼────────────┘   │
│            │                │                │                │                 │
│            ▼                ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        Smart Memory Core Layer                            │   │
│  │                                                                          │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │                     Context Understanding Engine                  │   │   │
│  │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │   │
│  │   │  │  Intent  │  │  Entity  │  │  State   │  │  Context  │      │   │   │
│  │   │  │Classify │  │Extract   │  │ Tracking │  │Graph Build│      │   │   │
│  │   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                     │   │
│  │                                    ▼                                     │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │                     Hybrid Retrieval Engine                       │   │   │
│  │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │   │
│  │   │  │  Vector  │  │ Keyword  │  │  Graph   │  │  Hybrid  │      │   │   │
│  │   │  │Retrieval │  │Retrieval │  │Retrieval │  │ Rerank   │      │   │   │
│  │   │  │(Semantic)│  │ (BM25)   │  │(Knowledge)│ │          │      │   │   │
│  │   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                     │   │
│  │                                    ▼                                     │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │                     Memory Fusion Layer                         │   │   │
│  │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │   │
│  │   │  │Conflict  │  │  Entity  │  │Relation  │  │Consistency│     │   │   │
│  │   │  │Detection │  │  Linking │  │Reasoning │  │Checking  │      │   │   │
│  │   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                       │
│                                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        Hierarchical Memory Storage Layer                  │   │
│  │                                                                          │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │   │
│  │  │  Working      │  │  Episodic     │  │  Semantic     │           │   │
│  │  │  Memory       │  │  Memory       │  │  Memory       │           │   │
│  │  │  (Working)   │  │  (Episodic)   │  │  (Semantic)   │           │   │
│  │  │                │  │                │  │                │           │   │
│  │  │ - Current ctx │  │ - Session hist│  │ - Knowledge   │           │   │
│  │  │ - Immediate   │  │ - Interaction │  │   graph       │           │   │
│  │  │   state       │  │   sequence    │  │ - Vector idx │           │   │
│  │  │ - KV cache    │  │ - Vector store│  │ - Structured  │           │   │
│  │  │                │  │                │  │   DB          │           │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘           │   │
│  │                                                                          │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │   │
│  │  │ User Profile  │  │  Entity        │  │  Credential   │           │   │
│  │  │  Memory       │  │  Memory        │  │  Memory       │           │   │
│  │  │(User Profile) │  │  (Entity)      │  │ (Credential)  │           │   │
│  │  │                │  │                │  │                │           │   │
│  │  │ - User prefs  │  │ - Accessed    │  │ - API Keys    │           │   │
│  │  │ - Behavior    │  │   entities    │  │ - Access ctx  │           │   │
│  │  │   patterns    │  │ - Web content │  │ - Quota state │           │   │
│  │  │ - Key info   │  │ - API records │  │                │           │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Module Design

### 3.1 Context Understanding Engine

**Purpose**: Let AI truly "understand" what the current conversation is about

```python
class ContextUnderstandingEngine:
    """
    Context Understanding Engine
    Solve: Align retrieval results with current task context
    """

    def __init__(
        self,
        intent_classifier: IntentClassifier,
        entity_extractor: EntityExtractor,
        state_tracker: StateTracker,
        context_graph_builder: ContextGraphBuilder
    ):
        self.intent = intent_classifier
        self.entity = entity_extractor
        self.state = state_tracker
        self.graph = context_graph_builder

    async def understand(
        self,
        user_input: str,
        conversation_history: List[Turn]
    ) -> ContextUnderstanding:
        """
        Understand user input context
        """
        # 1. Intent recognition - What does user want to do now?
        intent = await self.intent.classify(user_input)

        # 2. Entity extraction - What entities are involved?
        entities = await self.entity.extract(user_input)

        # 3. State tracking - Dialog state machine changes
        state_change = await self.state.update(
            current_state=self.state.current,
            new_input=user_input,
            intent=intent
        )

        # 4. Build context graph - Relationships between entities
        context_graph = await self.graph.build(
            current_entities=entities,
            conversation_history=conversation_history,
            current_intent=intent
        )

        return ContextUnderstanding(
            intent=intent,
            entities=entities,
            state=state_change,
            context_graph=context_graph,
            relevance_keywords=self._extract_keywords(user_input)
        )


class IntentClassifier:
    """
    Intent Classifier
    Distinguish user's true intent
    """

    INTENT_TYPES = {
        # Information retrieval
        "query_knowledge": "Query knowledge",
        "clarify": "Clarify question",
        "explain_concept": "Explain concept",

        # Task execution
        "perform_action": "Perform action",
        "create_content": "Create content",
        "analyze_data": "Analyze data",

        # Memory related (new)
        "remember_this": "Remember this",
        "recall_memory": "Recall information",
        "update_memory": "Update memory",
        "forget_this": "Forget this",

        # Interaction
        "casual_chat": "Casual chat",
        "give_feedback": "Give feedback"
    }

    async def classify(self, user_input: str) -> IntentResult:
        """
        Use LLM for intent classification
        """
        prompt = f"""
        Analyze user input and determine intent.

        User input: {user_input}

        Available intent types:
        - query_knowledge: Query knowledge
        - clarify: Clarify question
        - remember_this: Remember something (user says "remember", "must remember")
        - recall_memory: Recall information (user asks what was said before)
        - update_memory: Update memory (user corrects previous info)
        - perform_action: Perform action
        - casual_chat: Casual chat

        Output JSON format:
        {{"intent": "xxx", "confidence": 0.95, "reasoning": "Why this judgment"}}
        """

        result = await self.llm.complete(prompt)
        return IntentResult(**json.loads(result))
```

### 3.2 Hybrid Retrieval Engine

**Purpose**: High precision, high recall rate knowledge retrieval

```python
class HybridRetrievalEngine:
    """
    Hybrid Retrieval Engine
    Combines vector, keyword, and knowledge graph retrieval methods
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        keyword_retriever: KeywordRetriever,
        graph_retriever: GraphRetriever,
        reranker: CrossEncoderReranker
    ):
        self.vector = vector_retriever
        self.keyword = keyword_retriever
        self.graph = graph_retriever
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        context: ContextUnderstanding,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Multi-channel recall + unified ranking
        """
        # 1. Query expansion - Enrich query
        expanded_query = await self._expand_query(query, context)

        # 2. Parallel three-channel recall
        vector_results = await self.vector.search(
            query=expanded_query,
            top_k=top_k * 2
        )

        keyword_results = await self.keyword.search(
            query=expanded_query,
            top_k=top_k * 2
        )

        graph_results = await self.graph.search(
            query=expanded_query,
            context_graph=context.context_graph,
            top_k=top_k * 2
        )

        # 3. Merge candidate set
        all_candidates = self._merge_results(
            vector_results,
            keyword_results,
            graph_results
        )

        # 4. Unified ranking (Rerank)
        reranked = await self.reranker.rank(
            query=expanded_query,
            candidates=all_candidates,
            context=context,
            top_k=top_k
        )

        return reranked

    async def _expand_query(
        self,
        query: str,
        context: ContextUnderstanding
    ) -> str:
        """
        Query expansion - Add context information
        """
        # Extract related entities and relationships from context graph
        related_entities = context.context_graph.get_related_entities()

        # Build expanded query
        expansion_terms = []
        for entity in related_entities[:3]:
            expansion_terms.append(entity.name)

        if expansion_terms:
            return f"{query} {' '.join(expansion_terms)}"

        return query


class VectorRetriever:
    """
    Vector Retriever
    Optimization: Dynamic embedding + hierarchical indexing
    """

    async def search(
        self,
        query: str,
        top_k: int
    ) -> List[VectorResult]:
        """
        Vector retrieval
        """
        # 1. Dynamically select embedding model
        embedding = self._select_embedding_model(query)

        # 2. Vectorize query
        query_vector = await embedding.encode(query)

        # 3. Hierarchical index retrieval
        # Prioritize high-precision index
        results = await self.hnsw_index.search(
            query_vector=query_vector,
            top_k=top_k
        )

        # 4. If insufficient results, supplement from secondary index
        if len(results) < top_k:
            fallback = await self.ivf_pq_index.search(
                query_vector=query_vector,
                top_k=top_k - len(results)
            )
            results.extend(fallback)

        return results


class KeywordRetriever:
    """
    Keyword Retriever
    Use BM25, ensure exact matching
    """

    async def search(
        self,
        query: str,
        top_k: int
    ) -> List[KeywordResult]:
        """
        BM25 retrieval
        """
        # 1. Query preprocessing
        tokens = self._tokenize(query)

        # 2. BM25 scoring
        scores = self.bm25.get_scores(tokens)

        # 3. Get Top-K
        top_indices = np.argsort(scores)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            results.append(KeywordResult(
                doc_id=self.doc_ids[idx],
                score=scores[idx],
                matched_terms=self._get_matched_terms(tokens, idx)
            ))

        return results


class GraphRetriever:
    """
    Knowledge Graph Retriever
    Support entity-relationship path retrieval
    """

    async def search(
        self,
        query: str,
        context_graph: ContextGraph,
        top_k: int
    ) -> List[GraphResult]:
        """
        Knowledge graph retrieval
        """
        # 1. Extract entities from query
        query_entities = await self.entity_extractor.extract(query)

        # 2. Find these entities in the graph
        graph_paths = []

        for entity in query_entities:
            # 1-2 hop relationship query
            paths = await self.kg.query_relations(
                start_entity=entity,
                max_hops=2
            )
            graph_paths.extend(paths)

        # 3. Sort and return
        sorted_paths = sorted(
            graph_paths,
            key=lambda p: p.relevance_score,
            reverse=True
        )[:top_k]

        return sorted_paths


class CrossEncoderReranker:
    """
    Cross-Encoder Re-ranking
    Use LLM to finely rank candidate results
    """

    async def rank(
        self,
        query: str,
        candidates: List[Candidate],
        context: ContextUnderstanding,
        top_k: int
    ) -> List[RetrievalResult]:
        """
        Unified ranking
        """
        # Build ranking prompt
        prompt = f"""You are a professional knowledge retrieval ranking expert.
        Given user query and related candidate knowledge, please judge the importance of each candidate knowledge for answering user's question.

        User query: {query}

        Current intent: {context.intent}
        Entities involved: {[e.name for e in context.entities]}

        Candidate knowledge:
        {self._format_candidates(candidates)}

        Please rank by importance, output JSON format:
        {{"rankings": [doc_id_1, doc_id_2, ...], "reasons": {{"doc_id": "reason"}}}}
        """

        result = await self.llm.complete(prompt)
        ranked = json.loads(result)

        # Return ranked results
        final_results = []
        for doc_id in ranked["rankings"][:top_k]:
            candidate = self._find_candidate(candidates, doc_id)
            final_results.append(RetrievalResult(
                doc_id=doc_id,
                content=candidate.content,
                source=candidate.source,
                score=candidate.score,
                rerank_score=1.0 / (ranked["rankings"].index(doc_id) + 1)
            ))

        return final_results
```

### 3.3 Explicit Memory Processing

**Purpose**: Process explicit requirements like "must remember this"

```python
class ExplicitMemoryProcessor:
    """
    Explicit Memory Processor
    Process content that user explicitly asks to remember
    """

    async def process(
        self,
        user_input: str,
        memory_request: MemoryRequest
    ) -> MemoryProcessingResult:
        """
        Process explicit memory request
        """
        # 1. Determine if it's an explicit memory request
        is_explicit = self._is_explicit_request(user_input)

        if not is_explicit:
            return MemoryProcessingResult(
                processed=False,
                reason="Not an explicit memory request"
            )

        # 2. Extract content to remember
        content = await self._extract_memory_content(
            user_input,
            memory_request
        )

        # 3. Entity recognition and linking
        entities = await self.entity_extractor.extract(content)

        # 4. Set forced priority (not affected by normal confidence evaluation)
        memory_entry = MemoryEntry(
            content=content,
            entities=entities,
            priority=MemoryPriority.EXPLICIT_REQUIRED,  # Highest priority
            emphasis_level=memory_request.emphasis_level or 5,
            source="user_explicit",
            retention_policy=RetentionPolicy.PERMANENT,  # Permanent retention
            verify_on_recall=True  # Verify on recall
        )

        # 5. Write to memory storage
        await self.memory_store.store(memory_entry)

        # 6. Confirm memory to user
        await self._confirm_to_user(content)

        return MemoryProcessingResult(
            processed=True,
            memory_id=memory_entry.id,
            priority="Highest priority - User explicitly requested"
        )

    def _is_explicit_request(self, text: str) -> bool:
        """
        Determine if it's an explicit memory request
        """
        explicit_patterns = [
            r"记住",
            r"一定要记住",
            r"别忘了",
            r"请记住",
            r"帮我记着",
            r"这很重要",
            r"不要忘记",
            r"务必记住"
        ]

        for pattern in explicit_patterns:
            if re.search(pattern, text):
                return True

        return False


class MemoryRecallProcessor:
    """
    Memory Recall Processor
    Triggered when user asks "what did I say before"
    """

    async def recall(
        self,
        user_query: str,
        user_id: str,
        context: ContextUnderstanding
    ) -> RecallResult:
        """
        Recall relevant memory
        """
        # 1. Determine if it's a recall request
        is_recall = self._is_recall_request(user_query)

        if not is_recall:
            return RecallResult(is_recall=False)

        # 2. Extract keywords to recall
        recall_keywords = self._extract_recall_keywords(user_query)

        # 3. Prioritize retrieval from explicit memories
        explicit_memories = await self.memory_store.query(
            user_id=user_id,
            priority_gte=MemoryPriority.EXPLICIT_REQUIRED,
            keywords=recall_keywords
        )

        # 4. If explicit memories insufficient, expand retrieval
        if len(explicit_memories) < 3:
            all_memories = await self.memory_store.query(
                user_id=user_id,
                keywords=recall_keywords,
                limit=10
            )
        else:
            all_memories = explicit_memories

        # 5. Format recall results
        formatted = self._format_recall(all_memories)

        return RecallResult(
            is_recall=True,
            memories=all_memories,
            formatted_response=formatted
        )

    def _is_recall_request(self, text: str) -> bool:
        """
        Determine if it's a recall request
        """
        recall_patterns = [
            r"我之前.*说过",
            r"之前.*告诉.*你",
            r"记得.*吗",
            r"我之前.*提到",
            r"上次.*说了",
            r"之前.*怎么.*说"
        ]

        for pattern in recall_patterns:
            if re.search(pattern, text):
                return True

        return False
```

### 3.4 Credential & Entity Management

**Purpose**: Securely store API Keys and other credentials, manage accessed entities

```python
class CredentialManager:
    """
    Credential Manager
    Securely store API Keys, Tokens, etc.
    """

    def __init__(
        self,
        encryption_service: EncryptionService,
        quota_tracker: QuotaTracker
    ):
        self.encrypt = encryption_service
        self.quota = quota_tracker
        self.secure_storage = SecureStorage()

    async def store_credential(
        self,
        entity_id: str,
        credential_type: str,
        credential_value: str,
        metadata: dict
    ) -> str:
        """
        Store credential (encrypted)
        """
        # 1. Encrypt and store
        encrypted = self.encrypt.encrypt(credential_value)

        # 2. Record credential information
        credential = Credential(
            id=self._generate_id(),
            entity_id=entity_id,
            type=credential_type,
            encrypted_value=encrypted,
            metadata=metadata,
            created_at=datetime.now(),
            expires_at=metadata.get("expires_at"),
            quota_total=metadata.get("quota"),
            quota_used=0
        )

        # 3. Store
        await self.secure_storage.save(credential)

        # 4. Initialize quota tracking
        await self.quota.init(credential.id, metadata.get("quota", 0))

        return credential.id

    async def get_valid_credential(
        self,
        entity_id: str
    ) -> Optional[Credential]:
        """
        Get valid credential
        """
        credentials = await self.secure_storage.get_by_entity(entity_id)

        for cred in credentials:
            # Check if expired
            if cred.expires_at and cred.expires_at < datetime.now():
                continue

            # Check quota
            quota_status = await self.quota.get_status(cred.id)
            if quota_status.remaining <= 0:
                continue

            return cred

        return None

    async def use_credential(
        self,
        credential_id: str,
        usage: int = 1
    ) -> bool:
        """
        Record credential usage
        """
        return await self.quota.record_usage(credential_id, usage)


class EntityTracker:
    """
    Entity Tracker
    Record accessed web pages, APIs, etc.
    """

    async def record_access(
        self,
        entity_type: str,
        entity_id: str,
        content: dict,
        credentials_used: str,
        context: AccessContext
    ) -> EntityRecord:
        """
        Record entity access
        """
        record = EntityRecord(
            id=self._generate_id(),
            entity_type=entity_type,  # "web_page", "api_endpoint", "service"
            entity_id=entity_id,
            content_summary=self._summarize(content),
            credentials_used=credentials_used,
            access_time=datetime.now(),
            access_context=context,
            content_hash=self._hash(content)
        )

        await self.entity_store.save(record)

        # Update entity index
        await self._update_entity_index(record)

        return record

    async def get_entity_history(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[EntityRecord]:
        """
        Get entity access history
        """
        return await self.entity_store.query(
            entity_id=entity_id,
            order_by="access_time",
            desc=True,
            limit=limit
        )

    async def find_related_entities(
        self,
        entity_id: str,
        max_distance: int = 2
    ) -> List[EntityRecord]:
        """
        Find related entities (through access context correlation)
        """
        # Find access records for this entity
        main_record = await self.entity_store.get(entity_id)

        # Find other entities accessed in same session/time range
        related = await self.entity_store.query(
            access_context_session=main_record.access_context.session_id,
            time_window=timedelta(hours=1),
            exclude_id=entity_id
        )

        return related
```

### 3.5 Hierarchical Memory Storage

**Purpose**: Different memory types use different storage methods

```python
class HierarchicalMemoryStore:
    """
    Hierarchical Memory Storage
    Working Memory → Episodic Memory → Long-term Memory
    """

    def __init__(
        self,
        working_memory: WorkingMemory,
        episodic_memory: EpisodicMemory,
        semantic_memory: SemanticMemory,
        user_profile_memory: UserProfileMemory
    ):
        self.working = working_memory      # Current context (memory/KV)
        self.episodic = episodic_memory    # Session history (vector + structured)
        self.semantic = semantic_memory    # Knowledge (graph + vector)
        self.profile = user_profile_memory  # User profile

    async def store(
        self,
        memory: MemoryEntry,
        context: ContextUnderstanding
    ):
        """
        Intelligently select storage layer
        """
        # Decide storage location based on intent and content
        if context.intent == "remember_this":
            # Explicit memory request → User profile + Long-term memory
            await self.profile.store(memory)
            await self.semantic.store(memory)

        elif context.intent == "perform_action":
            # Action related → Episodic memory
            await self.episodic.store(memory)

        elif memory.emphasis_level >= 4:
            # High emphasis → Long-term memory
            await self.semantic.store(memory)

        else:
            # Default → Episodic memory
            await self.episodic.store(memory)

    async def retrieve(
        self,
        query: str,
        context: ContextUnderstanding,
        memory_types: List[str] = None
    ) -> List[MemoryEntry]:
        """
        Hierarchical retrieval
        """
        results = []

        # Decide which layers to retrieve
        if memory_types is None:
            memory_types = self._determine_relevant_layers(context)

        # Parallel retrieval of each layer
        if "working" in memory_types:
            working_results = await self.working.retrieve(query, context)
            results.extend(working_results)

        if "episodic" in memory_types:
            episodic_results = await self.episodic.retrieve(query, context)
            results.extend(episodic_results)

        if "semantic" in memory_types:
            semantic_results = await self.semantic.retrieve(query, context)
            results.extend(semantic_results)

        if "profile" in memory_types:
            profile_results = await self.profile.retrieve(query, context)
            results.extend(profile_results)

        return results


class WorkingMemory:
    """
    Working Memory - Current context
    Technology: Redis / In-memory KV
    """

    async def store(self, key: str, value: Any, ttl: int = 3600):
        """Store current context"""
        await self.redis.setex(f"working:{key}", ttl, json.dumps(value))

    async def retrieve(self, query: str, context: ContextUnderstanding):
        """Retrieve current relevant context"""
        # Get key state of current session from KV
        current_state = await self.redis.get(f"working:session:{context.session_id}")

        # Get recent N conversation turns
        recent_turns = await self.redis.lrange(
            f"working:history:{context.session_id}",
            -5, -1
        )

        return self._parse_working_memory(current_state, recent_turns)


class UserProfileMemory:
    """
    User Profile Memory
    Store user's explicit requirements, preferences, key information
    """

    async def store(self, memory: MemoryEntry):
        """
        Store user profile
        """
        # Extract user features
        profile_features = await self._extract_features(memory)

        # Write to user profile
        await self.profile_store.update(
            user_id=memory.user_id,
            features=profile_features,
            memory_ref=memory.id
        )

        # Also write to semantic memory (permanent storage)
        await self.semantic_memory.store(memory)

    async def retrieve(self, query: str, context: ContextUnderstanding):
        """
        Retrieve user profile
        """
        # Get user profile
        profile = await self.profile_store.get(context.user_id)

        # Retrieve relevant content from profile
        relevant_features = []
        for feature in profile.features:
            if self._is_relevant(feature, query):
                relevant_features.append(feature)

        return relevant_features
```

---

## 4. Key Technical Solutions Summary

### 4.1 Expert Consensus Technical Solutions

| Core Problem | Technical Solution | Technical Components |
|--------------|-------------------|---------------------|
| Semantic Understanding | Dynamic Embedding + Hybrid Vector | Multi-model selection + Dense/Sparse fusion |
| Context Association | Context-aware Retrieval | Intent classification + Entity extraction + Context graph |
| Knowledge Organization | Neural-symbolic Hybrid | GraphRAG + GNN reasoning + LLM CoT |
| User Intent | Three-layer Intent Understanding | Intent classification + State tracking + Memory feedback |
| Vector Recall | Multi-channel Recall + Rerank | Vector+Keyword+Graph → Cross-Encoder |

### 4.2 Retrieval Flow

```
User Input
    ↓
Intent Recognition (Query? Recall? Remember?)
    ↓
Context Graph Build (Entity relationships)
    ↓
Query Expansion (Add related entities)
    ↓
┌────────────────────────────────────┐
│         Three-channel Parallel      │
│  ┌────────┐ ┌────────┐ ┌────────┐ │
│  │ Vector │ │Keyword │ │ Graph  │ │
│  │Retrieval│ │ BM25  │ │Retrieval│ │
│  └────┬───┘ └────┬───┘ └────┬───┘ │
│       └──────────┼──────────┘      │
│                  ↓                  │
│         Candidate Merge             │
│                  ↓                  │
│      Cross-Encoder Rerank           │
│                  ↓                  │
│         Top-K Results               │
└────────────────────────────────────┘
    ↓
Memory Fusion (Conflict detection, Consistency check)
    ↓
Return Results + Write to Memory
```

---

## 5. Integration with Existing System

### 5.1 Keep Some V2 Modules

| Module | Keep | Reason |
|--------|------|--------|
| Value & Constraint Layer | **Delete** | Hinders intelligence |
| Safety Boundary | **Delete** | Hinders intelligence |
| Gradual Autonomy | **Delete** | Hinders intelligence |
| Memory Fusion Engine | **Keep** | Conflict resolution useful |
| Autonomous Trigger System | **Keep** | Curiosity drive useful |
| External Info Source Adapter | **Keep** | Information acquisition needed |

### 5.2 New Modules

| Module | Description |
|--------|-------------|
| Context Understanding Engine | Intent recognition, Entity extraction, State tracking |
| Hybrid Retrieval Engine | Vector + Keyword + Graph hybrid retrieval |
| Explicit Memory Processor | Handle "remember" requests |
| Memory Recall Processor | Handle "recall" requests |
| Credential Manager | Secure API Key storage |
| Entity Tracker | Web/API access records |
| Hierarchical Memory Storage | Working/Episodic/Semantic/User Profile |

---

## 6. Advanced Reasoning Module

### 6.1 Logical Reasoning Engine

**Purpose**: Enable AI to perform effective logical reasoning and consistency checking

```python
class LogicalReasoningEngine:
    """
    Logical Reasoning Engine
    Based on graph expert view: Logical rules embedded in graph "constraint edges"
    """

    async def reason(
        self,
        query: str,
        knowledge_graph: KnowledgeGraph,
        context: ContextUnderstanding
    ) -> LogicalReasoningResult:
        """
        Logical reasoning
        """
        # 1. Extract logical expressions from query
        logical_form = await self._extract_logic(query)

        # 2. Find related constraint edges in graph
        constraints = await knowledge_graph.find_constraints(
            entities=context.entities,
            relation_types=["implies", "requires", "forbidden"]
        )

        # 3. Logical consistency checking
        consistency = await self._check_consistency(
            logical_form,
            constraints
        )

        # 4. Inference chain generation
        if consistency.is_consistent:
            inference_chain = await self._generate_inference(
                logical_form,
                knowledge_graph
            )
        else:
            inference_chain = []

        return LogicalReasoningResult(
            is_consistent=consistency.is_consistent,
            conflicts=consistency.conflicts,
            inference_chain=inference_chain,
            confidence=consistency.confidence
        )

    async def _check_consistency(
        self,
        logical_form: LogicalExpression,
        constraints: List[Constraint]
    ) -> ConsistencyResult:
        """
        Check logical consistency
        """
        # Use SMT solver or LLM for consistency checking
        conflicts = []

        for constraint in constraints:
            if self._conflicts(logical_form, constraint):
                conflicts.append(Conflict(
                    constraint=constraint,
                    reason="Conflicts with existing constraints"
                ))

        return ConsistencyResult(
            is_consistent=len(conflicts) == 0,
            conflicts=conflicts,
            confidence=1.0 if len(conflicts) == 0 else 0.3
        )
```

### 6.2 Causal Reasoning Engine

**Purpose**: Understand causal relationships, perform counterfactual reasoning

```python
class CausalReasoningEngine:
    """
    Causal Reasoning Engine
    Based on graph expert view: Causal relations as first-class citizens in graph (causal edges)
    """

    CAUSAL_RELATIONS = [
        "causes", "enables", "prevents",
        "leads_to", "results_in", "because_of"
    ]

    async def reason(
        self,
        query: str,
        causal_graph: CausalGraph,
        context: ContextUnderstanding
    ) -> CausalReasoningResult:
        """
        Causal reasoning
        """
        # 1. Identify causal question type
        question_type = await self._classify_causal_question(query)

        if question_type == "why":
            # Query causes
            result = await self._find_causes(query, causal_graph, context)
        elif question_type == "what_if":
            # Counterfactual reasoning
            result = await self._counterfactual_reasoning(query, causal_graph, context)
        elif question_type == "how":
            # Query causal chain
            result = await self._find_causal_chain(query, causal_graph, context)
        else:
            result = CausalReasoningResult(answer=None, confidence=0)

        return result

    async def _counterfactual_reasoning(
        self,
        query: str,
        causal_graph: CausalGraph,
        context: ContextUnderstanding
    ) -> CausalReasoningResult:
        """
        Counterfactual reasoning: What if X happened?
        """
        # 1. Extract hypothetical conditions
        counterfactual = await self._extract_counterfactual(query)

        # 2. Simulate propagation in causal graph
        effects = await causal_graph.simulate(
            intervention=counterfactual.condition,
            max_depth=3
        )

        # 3. Generate counterfactual conclusion
        conclusion = await self.llm.generate(
            prompt=f"""
            Based on causal relationship analysis:
            Hypothetical condition: {counterfactual.condition}
            Possible results: {effects}

            Describe counterfactual reasoning result in natural language.
            """
        )

        return CausalReasoningResult(
            question_type="what_if",
            counterfactual=counterfactual,
            predicted_effects=effects,
            conclusion=conclusion,
            confidence=0.8
        )
```

### 6.3 Spatial Reasoning Engine

**Purpose**: Handle spatial relationships and location understanding

```python
class SpatialReasoningEngine:
    """
    Spatial Reasoning Engine
    Based on graph expert view: Build specialized "spatial graph layer"
    """

    SPATIAL_RELATIONS = [
        "north_of", "south_of", "east_of", "west_of",
        "above", "below", "inside", "outside",
        "adjacent_to", "between", "left_of", "right_of"
    ]

    async def reason(
        self,
        query: str,
        spatial_graph: SpatialGraph,
        context: ContextUnderstanding
    ) -> SpatialReasoningResult:
        """
        Spatial reasoning
        """
        # 1. Extract spatial entities and questions
        spatial_entities = await self._extract_spatial_entities(query)

        # 2. Spatial relationship query
        spatial_relations = await self._identify_spatial_relations(
            query,
            spatial_entities
        )

        # 3. Spatial reasoning
        if "navigate" in query or "route" in query:
            # Navigation reasoning
            route = await self._find_route(
                spatial_entities,
                spatial_relations,
                spatial_graph
            )
        elif "where" in query:
            # Location reasoning
            location = await self._infer_location(
                spatial_entities,
                spatial_relations,
                spatial_graph
            )
        else:
            # Spatial relationship reasoning
            relation = await self._infer_relation(
                spatial_entities,
                spatial_graph
            )

        return SpatialReasoningResult(
            entities=spatial_entities,
            relations=spatial_relations,
            reasoning_result=route or location or relation,
            confidence=0.85
        )
```

### 6.4 Tool Orchestration Engine

**Purpose**: Intelligently select and orchestrate tools to complete complex tasks

```python
class ToolOrchestrationEngine:
    """
    Tool Orchestration Engine
    Based on graph expert view: Tools as "executable nodes" in graph
    """

    async def orchestrate(
        self,
        task: str,
        available_tools: List[Tool],
        knowledge_graph: KnowledgeGraph,
        context: ContextUnderstanding
    ) -> OrchestrationResult:
        """
        Tool orchestration
        """
        # 1. Task decomposition
        subtasks = await self._decompose_task(task)

        # 2. Select tools for each subtask
        tool_plan = []
        for subtask in subtasks:
            # Find related tools in graph
            relevant_tools = await self._select_tools(
                subtask,
                available_tools,
                knowledge_graph
            )
            tool_plan.append(SubtaskPlan(
                subtask=subtask,
                tools=relevant_tools,
                dependencies=self._find_dependencies(subtask, tool_plan)
            ))

        # 3. Sort tool execution order
        execution_order = self._topological_sort(tool_plan)

        # 4. Execute tool chain
        results = []
        for tool in execution_order:
            result = await self._execute_tool(
                tool,
                context,
                previous_results=results
            )
            results.append(ToolResult(
                tool=tool,
                output=result,
                success=True
            ))

            # 5. Write tool results back to graph
            await self._update_graph_with_result(
                tool,
                result,
                knowledge_graph
            )

        return OrchestrationResult(
            task=task,
            tool_plan=tool_plan,
            execution_order=execution_order,
            results=results,
            final_output=self._merge_results(results)
        )

    async def _select_tools(
        self,
        subtask: str,
        available_tools: List[Tool],
        knowledge_graph: KnowledgeGraph
    ) -> List[Tool]:
        """
        Tool selection: Based on semantic matching + graph relationships
        """
        # Vector similarity recall
        tool_embeddings = await self.embedding_model.encode(
            [t.description for t in available_tools]
        )
        subtask_embedding = await self.embedding_model.encode(subtask)

        scores = cosine_similarity([subtask_embedding], tool_embeddings)[0]
        top_indices = np.argsort(scores)[-5:]

        candidate_tools = [available_tools[i] for i in top_indices]

        # Graph relationship verification
        verified_tools = []
        for tool in candidate_tools:
            # Check if tool input/output matches entities in graph
            if await self._verify_tool_compatibility(tool, knowledge_graph):
                verified_tools.append(tool)

        return verified_tools[:3]
```

---

## 7. Expert Collaboration Scheme

### 7.1 Module Collaboration Relationships

| Module | Collaboration Module | Collaboration Method |
|--------|---------------------|---------------------|
| Semantic Understanding | All modules | Provide semantic representation base |
| Context Understanding | Semantic, Graph, Intent | Maintain context consistency |
| Hybrid Retrieval | Vector, Keyword, Graph | Multi-channel recall fusion |
| Logical Reasoning | Graph | Constraint edge reasoning |
| Causal Reasoning | Graph | Causal edge reasoning |
| Spatial Reasoning | Graph | Spatial graph layer |
| Tool Orchestration | Graph | Executable nodes |
| Intent Understanding | Semantic, Context | Intent disambiguation |

### 7.2 Data Flow

```
User Input
    ↓
Intent Understanding (Semantic + Context)
    ↓
┌──────────────────────────────────────────┐
│           Dynamic Cognitive Graph          │
│  ┌────────┐ ┌────────┐ ┌────────┐      │
│  │Semantic│ │ Causal │ │Spatial │      │
│  │  Layer│ │  Layer │ │  Layer │      │
│  │        │ │        │ │        │      │
│  │Constraint│ │ Causal │ │Position│      │
│  │  Edge  │ │  Edge  │ │  Edge  │      │
│  └────────┘ └────────┘ └────────┘      │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│           Reasoning Engines               │
│  ┌────────┐ ┌────────┐ ┌────────┐      │
│  │Logical │ │ Causal │ │Spatial │      │
│  └────────┘ └────────┘ └────────┘      │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│           Tool Orchestration              │
│  Tool Selection → Execute → Write back    │
└──────────────────────────────────────────┘
    ↓
Feedback Loop → Graph Update → Continuous Evolution
```

---

## 8. Key Technical Solutions Summary

### 8.1 Expert Consensus Technical Solutions

| Core Problem | Technical Solution | Technical Components |
|--------------|-------------------|---------------------|
| Semantic Understanding | Dynamic Semantic Graph + Hierarchical Attention | Multi-dimensional semantic vectors |
| Context Association | Context-aware Retrieval + Graph Verification | Intent classification + Entity linking |
| Knowledge Organization | Dynamic Hierarchical Graph + Cognitive Entropy | Importance-Timeliness-Relevance Density |
| User Intent | Bayesian Intent Inference + Multi-level Modeling | Surface→Deep→Latent intent |
| Vector Recall | Multi-channel Recall + Cross-Encoder | Vector+Keyword+Graph |
| Logical Reasoning | Constraint Edge Reasoning + SMT Solver | Graph constraint edges |
| Causal Reasoning | Causal Edges + Counterfactual Simulation | Causal graph propagation |
| Spatial Reasoning | Spatial Graph Layer | Orthogonal spatial relationships |
| Tool Orchestration | Executable Nodes + Topological Sort | Tool chain orchestration |
| **AGI Architecture** | **Neural-symbolic Hybrid System** | **Event-driven closed loop** |

---

## 9. Summary

This V3.0 design scheme is based on multiple rounds of debate among 10+ technical experts, with core improvements:

### Core Improvements

1. **Remove all rules that constrain intelligence** - No more value constraints, safety boundaries, human approval
2. **Focus on intelligence enhancement** - Context understanding, precise recall, relational reasoning, logical causality
3. **Add user intent perception** - Explicit memory, recall requests, Bayesian intent inference
4. **Add credential management** - Secure API Key storage, entity tracking
5. **Add advanced reasoning** - Logical reasoning, causal reasoning, spatial reasoning
6. **Add tool orchestration** - Intelligent tool selection and execution

### AGI Architecture

> **Event-driven neural-symbolic hybrid system**
> - Dynamic cognitive graph as bone
> - Perception flow as flesh
> - Causal reasoning as brain
> - Tool calling as hands
> - Semantic understanding as blood, permeating all processes

### Design Goal

**Our goal is AGI, not "good boy AI"**

- Not afraid of complexity
- Not afraid of performance issues (performance issues have dedicated technical experts to handle)
- Any technology that can achieve AGI can be used

**Goal**: Let AI become truly smart, able to:
- Understand semantics and context
- Perform logical and causal reasoning
- Handle spatial relationships
- Intelligently call tools
- Remember user explicit requirements
- Learn and evolve autonomously

---

**Next Step**: Ready to implement any module?

<details>
<summary><h2>中文翻译</h2></summary>

# 智能知识记忆管理系统设计方案

> 版本: v3.0 (智能增强版)
> 日期: 2026-02-23
> 状态: 基于技术专家辩论

---

## 一、核心设计理念

### 1.1 设计目标

**不是做一个"乖宝宝AI"（被规则束缚），而是要做一个"超级智慧AI"（真正智能的记忆系统）**

| V2设计（错误方向） | V3设计（正确方向） |
|-------------------|-------------------|
| 价值约束层 | 智能记忆架构 |
| 安全边界 | 上下文理解 |
| 渐进自主 | 主动推理 |
| 人类审批 | 用户意图识别 |
| 可错主义 | 精准召回 |

### 1.2 核心问题（专家共识）

通过10+位技术专家辩论，识别出核心问题：

1. **语义理解** - 如何实现高效、可扩展的语义知识存储与检索
2. **上下文关联** - 如何让检索结果与当前任务上下文对齐
3. **知识组织** - 如何用知识图谱组织实体关系，支持推理
4. **用户意图** - 如何理解用户真实意图，提供精准记忆反馈
5. **向量召回** - 如何在海量信息中实现高精度、高召回率
6. **逻辑推理** - 如何进行有效的逻辑推理和一致性检验
7. **因果推理** - 如何理解因果关系，进行反事实推理
8. **空间推理** - 如何处理空间关系和位置理解
9. **工具调用** - 如何智能选择和编排工具
10. **AGI架构** - 如何形成统一的"神经-符号混合系统"

### 1.3 AGI核心架构（专家共识）

基于专家讨论，AGI核心架构应该是：

> **"事件驱动的神经-符号混合系统"**
> - 动态认知图谱为骨
> - 感知流为肉
> - 因果推理为脑
> - 工具调用为手
> - 语义理解为血液，渗透所有过程

```
用户输入 → 意图识别 → 图谱激活 → 因果推理 → 决策 → 工具执行 → 反馈闭环 → 图谱更新
    ↑                                                                      ↓
    └────────────────────────── 持续演化循环 ←─────────────────────────────────┘
```

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      智能知识记忆管理系统 (Smart Memory System)                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           用户交互层                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ 对话输入    │  │ 显式记忆    │  │ 隐式反馈    │  │ 意图理解    │    │   │
│  │  │(Query)     │  │ 请求处理    │  │ 捕捉       │  │ 引擎       │    │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │   │
│  └─────────┼────────────────┼────────────────┼────────────────┼────────────┘   │
│            │                │                │                │                 │
│            ▼                ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        智能记忆核心层                                     │   │
│  │                                                                          │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │                     上下文理解引擎                                │   │   │
│  │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │   │
│  │   │  │ 意图识别  │  │ 实体抽取  │  │ 状态追踪  │  │ 上下文图  │      │   │   │
│  │   │  │          │  │          │  │          │  │ 构建      │      │   │   │
│  │   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                     │   │
│  │                                    ▼                                     │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │                     混合检索引擎                                │   │   │
│  │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │   │
│  │   │  │ 向量检索 关键词   │  │ 图谱      │  │ │  │ 混合     │      │   │   │
│  │   │  │(Semantic)│  │ 检索     │  │ 检索     │  │ Rerank   │      │   │   │
│  │   │  │          │  │(BM25)   │  │(Knowledge)│  │          │      │   │   │
│  │   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                    │                                     │   │
│  │                                    ▼                                     │   │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │   │                     记忆融合层                                  │   │   │
│  │   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │   │
│  │   │  │ 冲突检测  │  │ 实体链接  │  │ 关系推理  │  │ 一致性   │      │   │   │
│  │   │  │          │  │          │  │          │  │ 校验      │      │   │   │
│  │   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │   │
│  │   └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                       │
│                                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        分层记忆存储层                                    │   │
│  │                                                                          │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │   │
│  │  │  工作记忆      │  │  情景记忆      │  │  长期记忆      │           │   │
│  │  │  (Working)    │  │  (Episodic)    │  │  (Semantic)   │           │   │
│  │  │                │  │                │  │                │           │   │
│  │  │ - 当前上下文   │  │ - 会话历史     │  │ - 知识图谱    │           │   │
│  │  │ - 即时状态     │  │ - 交互序列     │  │ - 向量索引    │           │   │
│  │  │ - KV缓存      │  │ - 向量存储     │  │ - 结构化DB   │           │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘           │   │
│  │                                                                          │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │   │
│  │  │  用户画像记忆  │  │  实体记忆      │  │  凭据记忆      │           │   │
│  │  │  (User Profile)│  │  (Entity)     │  │  (Credential) │           │   │
│  │  │                │  │                │  │                │           │   │
│  │  │ - 用户偏好    │  │ - 访问实体    │  │ - API Keys   │           │   │
│  │  │ - 行为模式    │  │ - 网页内容    │  │ - 访问上下文  │           │   │
│  │  │ - 关键信息    │  │ - 接口记录    │  │ - 配额状态    │           │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块设计

### 3.1 上下文理解引擎 (Context Understanding Engine)

**目的**：让AI真正"理解"当前对话在说什么

```python
class ContextUnderstandingEngine:
    """
    上下文理解引擎
    解决：让检索结果与当前任务上下文对齐
    """

    def __init__(
        self,
        intent_classifier: IntentClassifier,
        entity_extractor: EntityExtractor,
        state_tracker: StateTracker,
        context_graph_builder: ContextGraphBuilder
    ):
        self.intent = intent_classifier
        self.entity = entity_extractor
        self.state = state_tracker
        self.graph = context_graph_builder

    async def understand(
        self,
        user_input: str,
        conversation_history: List[Turn]
    ) -> ContextUnderstanding:
        """
        理解用户输入的上下文
        """
        # 1. 意图识别 - 用户现在想做什么？
        intent = await self.intent.classify(user_input)

        # 2. 实体抽取 - 涉及哪些实体？
        entities = await self.entity.extract(user_input)

        # 3. 状态追踪 - 对话状态机变化
        state_change = await self.state.update(
            current_state=self.state.current,
            new_input=user_input,
            intent=intent
        )

        # 4. 构建上下文图 - 实体之间的关系
        context_graph = await self.graph.build(
            current_entities=entities,
            conversation_history=conversation_history,
            current_intent=intent
        )

        return ContextUnderstanding(
            intent=intent,
            entities=entities,
            state=state_change,
            context_graph=context_graph,
            relevance_keywords=self._extract_keywords(user_input)
        )


class IntentClassifier:
    """
    意图分类器
    区分用户的真实意图
    """

    INTENT_TYPES = {
        # 信息获取类
        "query_knowledge": "查询知识",
        "clarify": "澄清问题",
        "explain_concept": "解释概念",

        # 任务执行类
        "perform_action": "执行操作",
        "create_content": "创建内容",
        "analyze_data": "分析数据",

        # 记忆相关类（新增）
        "remember_this": "要求记住",
        "recall_memory": "回忆信息",
        "update_memory": "更新记忆",
        "forget_this": "要求遗忘",

        # 交互类
        "casual_chat": "闲聊",
        "give_feedback": "提供反馈"
    }

    async def classify(self, user_input: str) -> IntentResult:
        """
        使用LLM进行意图分类
        """
        prompt = f"""
        分析用户输入，判断其意图。

        用户输入: {user_input}

        可选意图类型:
        - query_knowledge: 查询知识
        - clarify: 澄清问题
        - remember_this: 要求记住某事（用户说"记住"、"一定要记住"）
        - recall_memory: 回忆信息（用户问之前说过什么）
        - update_memory: 更新记忆（用户纠正之前的信息）
        - perform_action: 执行操作
        - casual_chat: 闲聊

        输出JSON格式:
        {{"intent": "xxx", "confidence": 0.95, "reasoning": "为什么这么判断"}}
        """

        result = await self.llm.complete(prompt)
        return IntentResult(**json.loads(result))
```

### 3.2 混合检索引擎 (Hybrid Retrieval Engine)

**目的**：高精度、高召回率的知识检索

```python
class HybridRetrievalEngine:
    """
    混合检索引擎
    结合向量、关键词、知识图谱三种检索方式
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        keyword_retriever: KeywordRetriever,
        graph_retriever: GraphRetriever,
        reranker: CrossEncoderReranker
    ):
        self.vector = vector_retriever
        self.keyword = keyword_retriever
        self.graph = graph_retriever
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        context: ContextUnderstanding,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        多路召回 + 统一排序
        """
        # 1. 查询扩展 - 让query更丰富
        expanded_query = await self._expand_query(query, context)

        # 2. 并行三路召回
        vector_results = await self.vector.search(
            query=expanded_query,
            top_k=top_k * 2
        )

        keyword_results = await self.keyword.search(
            query=expanded_query,
            top_k=top_k * 2
        )

        graph_results = await self.graph.search(
            query=expanded_query,
            context_graph=context.context_graph,
            top_k=top_k * 2
        )

        # 3. 合并候选集
        all_candidates = self._merge_results(
            vector_results,
            keyword_results,
            graph_results
        )

        # 4. 统一排序（Rerank）
        reranked = await self.reranker.rank(
            query=expanded_query,
            candidates=all_candidates,
            context=context,
            top_k=top_k
        )

        return reranked

    async def _expand_query(
        self,
        query: str,
        context: ContextUnderstanding
    ) -> str:
        """
        查询扩展 - 加入上下文信息
        """
        # 从上下文图谱中提取相关实体和关系
        related_entities = context.context_graph.get_related_entities()

        # 构建扩展query
        expansion_terms = []
        for entity in related_entities[:3]:
            expansion_terms.append(entity.name)

        if expansion_terms:
            return f"{query} {' '.join(expansion_terms)}"

        return query


class VectorRetriever:
    """
    向量检索器
    优化：动态embedding + 分级索引
    """

    async def search(
        self,
        query: str,
        top_k: int
    ) -> List[VectorResult]:
        """
        向量检索
        """
        # 1. 动态选择embedding模型
        embedding = self._select_embedding_model(query)

        # 2. 向量化查询
        query_vector = await embedding.encode(query)

        # 3. 分级索引检索
        # 优先从高精度索引检索
        results = await self.hnsw_index.search(
            query_vector=query_vector,
            top_k=top_k
        )

        # 4. 如果结果不足，从次级索引补充
        if len(results) < top_k:
            fallback = await self.ivf_pq_index.search(
                query_vector=query_vector,
                top_k=top_k - len(results)
            )
            results.extend(fallback)

        return results


class KeywordRetriever:
    """
    关键词检索器
    使用BM25，保证精确匹配
    """

    async def search(
        self,
        query: str,
        top_k: int
    ) -> List[KeywordResult]:
        """
        BM25检索
        """
        # 1. 查询预处理
        tokens = self._tokenize(query)

        # 2. BM25评分
        scores = self.bm25.get_scores(tokens)

        # 3. 取Top-K
        top_indices = np.argsort(scores)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            results.append(KeywordResult(
                doc_id=self.doc_ids[idx],
                score=scores[idx],
                matched_terms=self._get_matched_terms(tokens, idx)
            ))

        return results


class GraphRetriever:
    """
    知识图谱检索器
    支持实体关系路径检索
    """

    async def search(
        self,
        query: str,
        context_graph: ContextGraph,
        top_k: int
    ) -> List[GraphResult]:
        """
        知识图谱检索
        """
        # 1. 从查询中抽取实体
        query_entities = await self.entity_extractor.extract(query)

        # 2. 在图谱中查找这些实体
        graph_paths = []

        for entity in query_entities:
            # 1-2跳关系查询
            paths = await self.kg.query_relations(
                start_entity=entity,
                max_hops=2
            )
            graph_paths.extend(paths)

        # 3. 排序返回
        sorted_paths = sorted(
            graph_paths,
            key=lambda p: p.relevance_score,
            reverse=True
        )[:top_k]

        return sorted_paths


class CrossEncoderReranker:
    """
    Cross-Encoder重排序
    用LLM对候选结果进行精细排序
    """

    async def rank(
        self,
        query: str,
        candidates: List[Candidate],
        context: ContextUnderstanding,
        top_k: int
    ) -> List[RetrievalResult]:
        """
        统一排序
        """
        # 构建排序prompt
        prompt = f"""你是一个专业的知识检索排序专家。
        给定用户查询和相关候选知识，请判断每个候选知识对回答用户问题的重要程度。

        用户查询: {query}

        当前意图: {context.intent}
        涉及实体: {[e.name for e in context.entities]}

        候选知识:
        {self._format_candidates(candidates)}

        请按重要性排序，输出JSON格式:
        {{"rankings": [doc_id_1, doc_id_2, ...], "reasons": {{"doc_id": "原因"}}}}
        """

        result = await self.llm.complete(prompt)
        ranked = json.loads(result)

        # 返回排序后的结果
        final_results = []
        for doc_id in ranked["rankings"][:top_k]:
            candidate = self._find_candidate(candidates, doc_id)
            final_results.append(RetrievalResult(
                doc_id=doc_id,
                content=candidate.content,
                source=candidate.source,
                score=candidate.score,
                rerank_score=1.0 / (ranked["rankings"].index(doc_id) + 1)
            ))

        return final_results
```

### 3.3 显式记忆处理 (Explicit Memory Processing)

**目的**：处理用户说"一定要记住"这种显式要求

```python
class ExplicitMemoryProcessor:
    """
    显式记忆处理器
    处理用户明确要求记住的内容
    """

    async def process(
        self,
        user_input: str,
        memory_request: MemoryRequest
    ) -> MemoryProcessingResult:
        """
        处理显式记忆请求
        """
        # 1. 判断是否是显式记忆请求
        is_explicit = self._is_explicit_request(user_input)

        if not is_explicit:
            return MemoryProcessingResult(
                processed=False,
                reason="非显式记忆请求"
            )

        # 2. 提取需要记忆的内容
        content = await self._extract_memory_content(
            user_input,
            memory_request
        )

        # 3. 实体识别和链接
        entities = await self.entity_extractor.extract(content)

        # 4. 设置强制优先级（不受常规置信度评估影响）
        memory_entry = MemoryEntry(
            content=content,
            entities=entities,
            priority=MemoryPriority.EXPLICIT_REQUIRED,  # 最高优先级
            emphasis_level=memory_request.emphasis_level or 5,
            source="user_explicit",
            retention_policy=RetentionPolicy.PERMANENT,  # 永久保留
            verify_on_recall=True  # 召回时验证
        )

        # 5. 写入记忆存储
        await self.memory_store.store(memory_entry)

        # 6. 确认记忆成功
        await self._confirm_to_user(content)

        return MemoryProcessingResult(
            processed=True,
            memory_id=memory_entry.id,
            priority="最高优先级 - 用户显式要求"
        )

    def _is_explicit_request(self, text: str) -> bool:
        """
        判断是否是显式记忆请求
        """
        explicit_patterns = [
            r"记住",
            r"一定要记住",
            r"别忘了",
            r"请记住",
            r"帮我记着",
            r"这很重要",
            r"不要忘记",
            r"务必记住"
        ]

        for pattern in explicit_patterns:
            if re.search(pattern, text):
                return True

        return False


class MemoryRecallProcessor:
    """
    记忆召回处理器
    当用户问"我之前说过什么"时触发
    """

    async def recall(
        self,
        user_query: str,
        user_id: str,
        context: ContextUnderstanding
    ) -> RecallResult:
        """
        召回相关记忆
        """
        # 1. 判断是否是回忆请求
        is_recall = self._is_recall_request(user_query)

        if not is_recall:
            return RecallResult(is_recall=False)

        # 2. 提取要回忆的关键词
        recall_keywords = self._extract_recall_keywords(user_query)

        # 3. 优先从显式记忆中检索
        explicit_memories = await self.memory_store.query(
            user_id=user_id,
            priority_gte=MemoryPriority.EXPLICIT_REQUIRED,
            keywords=recall_keywords
        )

        # 4. 如果显式记忆不足，扩展检索
        if len(explicit_memories) < 3:
            all_memories = await self.memory_store.query(
                user_id=user_id,
                keywords=recall_keywords,
                limit=10
            )
        else:
            all_memories = explicit_memories

        # 5. 格式化回忆结果
        formatted = self._format_recall(all_memories)

        return RecallResult(
            is_recall=True,
            memories=all_memories,
            formatted_response=formatted
        )

    def _is_recall_request(self, text: str) -> bool:
        """
        判断是否是回忆请求
        """
        recall_patterns = [
            r"我之前.*说过",
            r"之前.*告诉.*你",
            r"记得.*吗",
            r"我之前.*提到",
            r"上次.*说了",
            r"之前.*怎么.*说"
        ]

        for pattern in recall_patterns:
            if re.search(pattern, text):
                return True

        return False
```

### 3.4 凭据与实体管理 (Credential & Entity Management)

**目的**：安全存储API Key等凭据，管理访问过的实体

```python
class CredentialManager:
    """
    凭据管理器
    安全存储API Key、Token等
    """

    def __init__(
        self,
        encryption_service: EncryptionService,
        quota_tracker: QuotaTracker
    ):
        self.encrypt = encryption_service
        self.quota = quota_tracker
        self.secure_storage = SecureStorage()

    async def store_credential(
        self,
        entity_id: str,
        credential_type: str,
        credential_value: str,
        metadata: dict
    ) -> str:
        """
        存储凭据（加密）
        """
        # 1. 加密存储
        encrypted = self.encrypt.encrypt(credential_value)

        # 2. 记录凭据信息
        credential = Credential(
            id=self._generate_id(),
            entity_id=entity_id,
            type=credential_type,
            encrypted_value=encrypted,
            metadata=metadata,
            created_at=datetime.now(),
            expires_at=metadata.get("expires_at"),
            quota_total=metadata.get("quota"),
            quota_used=0
        )

        # 3. 存储
        await self.secure_storage.save(credential)

        # 4. 初始化配额追踪
        await self.quota.init(credential.id, metadata.get("quota", 0))

        return credential.id

    async def get_valid_credential(
        self,
        entity_id: str
    ) -> Optional[Credential]:
        """
        获取有效凭据
        """
        credentials = await self.secure_storage.get_by_entity(entity_id)

        for cred in credentials:
            # 检查是否过期
            if cred.expires_at and cred.expires_at < datetime.now():
                continue

            # 检查配额
            quota_status = await self.quota.get_status(cred.id)
            if quota_status.remaining <= 0:
                continue

            return cred

        return None

    async def use_credential(
        self,
        credential_id: str,
        usage: int = 1
    ) -> bool:
        """
        记录凭据使用
        """
        return await self.quota.record_usage(credential_id, usage)


class EntityTracker:
    """
    实体追踪器
    记录访问过的网页、接口等实体
    """

    async def record_access(
        self,
        entity_type: str,
        entity_id: str,
        content: dict,
        credentials_used: str,
        context: AccessContext
    ) -> EntityRecord:
        """
        记录实体访问
        """
        record = EntityRecord(
            id=self._generate_id(),
            entity_type=entity_type,  # "web_page", "api_endpoint", "service"
            entity_id=entity_id,
            content_summary=self._summarize(content),
            credentials_used=credentials_used,
            access_time=datetime.now(),
            access_context=context,
            content_hash=self._hash(content)
        )

        await self.entity_store.save(record)

        # 更新实体索引
        await self._update_entity_index(record)

        return record

    async def get_entity_history(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[EntityRecord]:
        """
        获取实体访问历史
        """
        return await self.entity_store.query(
            entity_id=entity_id,
            order_by="access_time",
            desc=True,
            limit=limit
        )

    async def find_related_entities(
        self,
        entity_id: str,
        max_distance: int = 2
    ) -> List[EntityRecord]:
        """
        查找相关实体（通过访问上下文关联）
        """
        # 找到该实体的访问记录
        main_record = await self.entity_store.get(entity_id)

        # 找到同一会话/时间范围内访问的其他实体
        related = await self.entity_store.query(
            access_context_session=main_record.access_context.session_id,
            time_window=timedelta(hours=1),
            exclude_id=entity_id
        )

        return related
```

### 3.5 分层记忆存储 (Hierarchical Memory Storage)

**目的**：不同类型的记忆用不同的存储方式

```python
class HierarchicalMemoryStore:
    """
    分层记忆存储
    工作记忆 → 情景记忆 → 长期记忆
    """

    def __init__(
        self,
        working_memory: WorkingMemory,
        episodic_memory: EpisodicMemory,
        semantic_memory: SemanticMemory,
        user_profile_memory: UserProfileMemory
    ):
        self.working = working_memory      # 当前上下文（内存/KV）
        self.episodic = episodic_memory    # 会话历史（向量+结构化）
        self.semantic = semantic_memory    # 知识（图谱+向量）
        self.profile = user_profile_memory  # 用户画像

    async def store(
        self,
        memory: MemoryEntry,
        context: ContextUnderstanding
    ):
        """
        智能选择存储层级
        """
        # 根据意图和内容决定存储位置
        if context.intent == "remember_this":
            # 显式记忆请求 → 用户画像 + 长期记忆
            await self.profile.store(memory)
            await self.semantic.store(memory)

        elif context.intent == "perform_action":
            # 行动相关 → 情景记忆
            await self.episodic.store(memory)

        elif memory.emphasis_level >= 4:
            # 高强调 → 长期记忆
            await self.semantic.store(memory)

        else:
            # 默认 → 情景记忆
            await self.episodic.store(memory)

    async def retrieve(
        self,
        query: str,
        context: ContextUnderstanding,
        memory_types: List[str] = None
    ) -> List[MemoryEntry]:
        """
        分层检索
        """
        results = []

        # 决定检索哪些层级
        if memory_types is None:
            memory_types = self._determine_relevant_layers(context)

        # 并行检索各层级
        if "working" in memory_types:
            working_results = await self.working.retrieve(query, context)
            results.extend(working_results)

        if "episodic" in memory_types:
            episodic_results = await self.episodic.retrieve(query, context)
            results.extend(episodic_results)

        if "semantic" in memory_types:
            semantic_results = await self.semantic.retrieve(query, context)
            results.extend(semantic_results)

        if "profile" in memory_types:
            profile_results = await self.profile.retrieve(query, context)
            results.extend(profile_results)

        return results


class WorkingMemory:
    """
    工作记忆 - 当前上下文
    技术：Redis / 内存KV
    """

    async def store(self, key: str, value: Any, ttl: int = 3600):
        """存储当前上下文"""
        await self.redis.setex(f"working:{key}", ttl, json.dumps(value))

    async def retrieve(self, query: str, context: ContextUnderstanding):
        """检索当前相关上下文"""
        # 从KV中获取当前会话的关键状态
        current_state = await self.redis.get(f"working:session:{context.session_id}")

        # 获取最近N轮对话
        recent_turns = await self.redis.lrange(
            f"working:history:{context.session_id}",
            -5, -1
        )

        return self._parse_working_memory(current_state, recent_turns)


class UserProfileMemory:
    """
    用户画像记忆
    存储用户的显式要求、偏好、关键信息
    """

    async def store(self, memory: MemoryEntry):
        """
        存储用户画像
        """
        # 提取用户特征
        profile_features = await self._extract_features(memory)

        # 写入用户画像
        await self.profile_store.update(
            user_id=memory.user_id,
            features=profile_features,
            memory_ref=memory.id
        )

        # 同时写入语义记忆（永久存储）
        await self.semantic_memory.store(memory)

    async def retrieve(self, query: str, context: ContextUnderstanding):
        """
        检索用户画像
        """
        # 获取用户画像
        profile = await self.profile_store.get(context.user_id)

        # 从画像中检索相关内容
        relevant_features = []
        for feature in profile.features:
            if self._is_relevant(feature, query):
                relevant_features.append(feature)

        return relevant_features
```

---

## 四、关键技术方案汇总

### 4.1 专家共识技术方案

| 核心问题 | 技术方案 | 技术组件 |
|----------|----------|----------|
| 语义理解 | 动态Embedding + 混合向量 | 多模型选择 + 稠密/稀疏融合 |
| 上下文关联 | 上下文感知检索 | 意图分类 + 实体抽取 + 上下文图 |
| 知识组织 | 神经符号混合 | GraphRAG + GNN推理 + LLM CoT |
| 用户意图 | 三层意图理解 | 意图分类 + 状态追踪 + 记忆反馈 |
| 向量召回 | 多路召回 + Rerank | 向量+关键词+图谱 → Cross-Encoder |

### 4.2 检索流程

```
用户输入
    ↓
意图识别 (是查询? 回忆? 记住?)
    ↓
上下文图构建 (实体关系)
    ↓
查询扩展 (加入相关实体)
    ↓
┌────────────────────────────────────┐
│         三路并行检索                │
│  ┌────────┐ ┌────────┐ ┌────────┐ │
│  │ 向量   │ │ 关键词  │ │ 图谱   │ │
│  │ 检索   │ │ BM25   │ │ 检索   │ │
│  └────┬───┘ └────┬───┘ └────┬───┘ │
│       └──────────┼──────────┘      │
│                  ↓                  │
│         候选集合并                   │
│                  ↓                  │
│      Cross-Encoder Rerank           │
│                  ↓                  │
│         Top-K 结果                  │
└────────────────────────────────────┘
    ↓
记忆融合 (冲突检测、一致性校验)
    ↓
返回结果 + 写入记忆
```

---

## 五、与原有系统的集成

### 5.1 保留V2的部分模块

| 模块 | 是否保留 | 原因 |
|------|----------|------|
| 价值与约束层 | **删除** | 阻碍智能 |
| 安全边界 | **删除** | 阻碍智能 |
| 渐进自主 | **删除** | 阻碍智能 |
| 记忆融合引擎 | **保留** | 冲突解决有用 |
| 自主触发系统 | **保留** | 好奇心驱动有用 |
| 外部信息源适配器 | **保留** | 信息获取需要 |

### 5.2 新增模块

| 模块 | 描述 |
|------|------|
| 上下文理解引擎 | 意图识别、实体抽取、状态追踪 |
| 混合检索引擎 | 向量+关键词+图谱混合检索 |
| 显式记忆处理器 | 处理"记住"请求 |
| 记忆召回处理器 | 处理"回忆"请求 |
| 凭据管理器 | API Key安全存储 |
| 实体追踪器 | 网页/接口访问记录 |
| 分层记忆存储 | 工作/情景/语义/用户画像 |

---

## 六、高级推理模块

### 6.1 逻辑推理引擎 (Logical Reasoning Engine)

**目的**：让AI能够进行有效的逻辑推理和一致性检验

```python
class LogicalReasoningEngine:
    """
    逻辑推理引擎
    基于图谱专家观点：逻辑规则嵌入图谱的"约束边"
    """

    async def reason(
        self,
        query: str,
        knowledge_graph: KnowledgeGraph,
        context: ContextUnderstanding
    ) -> LogicalReasoningResult:
        """
        逻辑推理
        """
        # 1. 抽取查询中的逻辑表达式
        logical_form = await self._extract_logic(query)

        # 2. 在图谱中查找相关约束边
        constraints = await knowledge_graph.find_constraints(
            entities=context.entities,
            relation_types=["implies", "requires", "forbidden"]
        )

        # 3. 逻辑一致性检验
        consistency = await self._check_consistency(
            logical_form,
            constraints
        )

        # 4. 推理链生成
        if consistency.is_consistent:
            inference_chain = await self._generate_inference(
                logical_form,
                knowledge_graph
            )
        else:
            inference_chain = []

        return LogicalReasoningResult(
            is_consistent=consistency.is_consistent,
            conflicts=consistency.conflicts,
            inference_chain=inference_chain,
            confidence=consistency.confidence
        )

    async def _check_consistency(
        self,
        logical_form: LogicalExpression,
        constraints: List[Constraint]
    ) -> ConsistencyResult:
        """
        检查逻辑一致性
        """
        # 使用SMT求解器或LLM进行一致性检验
        conflicts = []

        for constraint in constraints:
            if self._conflicts(logical_form, constraint):
                conflicts.append(Conflict(
                    constraint=constraint,
                    reason="与已有约束冲突"
                ))

        return ConsistencyResult(
            is_consistent=len(conflicts) == 0,
            conflicts=conflicts,
            confidence=1.0 if len(conflicts) == 0 else 0.3
        )
```

### 6.2 因果推理引擎 (Causal Reasoning Engine)

**目的**：理解因果关系，进行反事实推理

```python
class CausalReasoningEngine:
    """
    因果推理引擎
    基于图谱专家观点：因果关系作为图谱的一等公民(因果边)
    """

    CAUSAL_RELATIONS = [
        "causes", "enables", "prevents",
        "leads_to", "results_in", "because_of"
    ]

    async def reason(
        self,
        query: str,
        causal_graph: CausalGraph,
        context: ContextUnderstanding
    ) -> CausalReasoningResult:
        """
        因果推理
        """
        # 1. 识别因果问题类型
        question_type = await self._classify_causal_question(query)

        if question_type == "why":
            # 查询原因
            result = await self._find_causes(query, causal_graph, context)
        elif question_type == "what_if":
            # 反事实推理
            result = await self._counterfactual_reasoning(query, causal_graph, context)
        elif question_type == "how":
            # 查询因果链
            result = await self._find_causal_chain(query, causal_graph, context)
        else:
            result = CausalReasoningResult(answer=None, confidence=0)

        return result

    async def _counterfactual_reasoning(
        self,
        query: str,
        causal_graph: CausalGraph,
        context: ContextUnderstanding
    ) -> CausalReasoningResult:
        """
        反事实推理：如果X发生了会怎样？
        """
        # 1. 提取假设条件
        counterfactual = await self._extract_counterfactual(query)

        # 2. 在因果图中模拟传播
        effects = await causal_graph.simulate(
            intervention=counterfactual.condition,
            max_depth=3
        )

        # 3. 生成反事实结论
        conclusion = await self.llm.generate(
            prompt=f"""
            基于因果关系分析：
            假设条件: {counterfactual.condition}
            可能结果: {effects}

            用自然语言描述反事实推理结果。
            """
        )

        return CausalReasoningResult(
            question_type="what_if",
            counterfactual=counterfactual,
            predicted_effects=effects,
            conclusion=conclusion,
            confidence=0.8
        )
```

### 6.3 空间推理引擎 (Spatial Reasoning Engine)

**目的**：处理空间关系和位置理解

```python
class SpatialReasoningEngine:
    """
    空间推理引擎
    基于图谱专家观点：空间关系构建专门的"空间图谱层"
    """

    SPATIAL_RELATIONS = [
        "north_of", "south_of", "east_of", "west_of",
        "above", "below", "inside", "outside",
        "adjacent_to", "between", "left_of", "right_of"
    ]

    async def reason(
        self,
        query: str,
        spatial_graph: SpatialGraph,
        context: ContextUnderstanding
    ) -> SpatialReasoningResult:
        """
        空间推理
        """
        # 1. 提取空间实体和问题
        spatial_entities = await self._extract_spatial_entities(query)

        # 2. 空间关系查询
        spatial_relations = await self._identify_spatial_relations(
            query,
            spatial_entities
        )

        # 3. 空间推理
        if "navigate" in query or "route" in query:
            # 导航推理
            route = await self._find_route(
                spatial_entities,
                spatial_relations,
                spatial_graph
            )
        elif "where" in query:
            # 位置推理
            location = await self._infer_location(
                spatial_entities,
                spatial_relations,
                spatial_graph
            )
        else:
            # 空间关系推理
            relation = await self._infer_relation(
                spatial_entities,
                spatial_graph
            )

        return SpatialReasoningResult(
            entities=spatial_entities,
            relations=spatial_relations,
            reasoning_result=route or location or relation,
            confidence=0.85
        )
```

### 6.4 工具编排引擎 (Tool Orchestration Engine)

**目的**：智能选择和编排工具，完成复杂任务

```python
class ToolOrchestrationEngine:
    """
    工具编排引擎
    基于图谱专家观点：工具作为图谱中的"可执行节点"
    """

    async def orchestrate(
        self,
        task: str,
        available_tools: List[Tool],
        knowledge_graph: KnowledgeGraph,
        context: ContextUnderstanding
    ) -> OrchestrationResult:
        """
        工具编排
        """
        # 1. 任务分解
        subtasks = await self._decompose_task(task)

        # 2. 为每个子任务选择工具
        tool_plan = []
        for subtask in subtasks:
            # 在图谱中查找相关工具
            relevant_tools = await self._select_tools(
                subtask,
                available_tools,
                knowledge_graph
            )
            tool_plan.append(SubtaskPlan(
                subtask=subtask,
                tools=relevant_tools,
                dependencies=self._find_dependencies(subtask, tool_plan)
            ))

        # 3. 排序工具执行顺序
        execution_order = self._topological_sort(tool_plan)

        # 4. 执行工具链
        results = []
        for tool in execution_order:
            result = await self._execute_tool(
                tool,
                context,
                previous_results=results
            )
            results.append(ToolResult(
                tool=tool,
                output=result,
                success=True
            ))

            # 5. 将工具结果写回图谱
            await self._update_graph_with_result(
                tool,
                result,
                knowledge_graph
            )

        return OrchestrationResult(
            task=task,
            tool_plan=tool_plan,
            execution_order=execution_order,
            results=results,
            final_output=self._merge_results(results)
        )

    async def _select_tools(
        self,
        subtask: str,
        available_tools: List[Tool],
        knowledge_graph: KnowledgeGraph
    ) -> List[Tool]:
        """
        工具选择：基于语义匹配 + 图谱关系
        """
        # 向量相似度召回
        tool_embeddings = await self.embedding_model.encode(
            [t.description for t in available_tools]
        )
        subtask_embedding = await self.embedding_model.encode(subtask)

        scores = cosine_similarity([subtask_embedding], tool_embeddings)[0]
        top_indices = np.argsort(scores)[-5:]

        candidate_tools = [available_tools[i] for i in top_indices]

        # 图谱关系验证
        verified_tools = []
        for tool in candidate_tools:
            # 检查工具的输入输出是否与图谱中的实体匹配
            if await self._verify_tool_compatibility(tool, knowledge_graph):
                verified_tools.append(tool)

        return verified_tools[:3]
```

---

## 七、专家协同方案

### 7.1 模块协同关系

| 模块 | 协同模块 | 协同方式 |
|------|----------|----------|
| 语义理解 | 所有模块 | 提供语义表示基座 |
| 上下文理解 | 语义、图谱、意图 | 维护上下文一致性 |
| 混合检索 | 向量、关键词、图谱 | 多路召回融合 |
| 逻辑推理 | 图谱 | 约束边推理 |
| 因果推理 | 图谱 | 因果边推理 |
| 空间推理 | 图谱 | 空间图谱层 |
| 工具编排 | 图谱 | 可执行节点 |
| 意图理解 | 语义、上下文 | 意图消歧 |

### 7.2 数据流

```
用户输入
    ↓
意图理解（语义 + 上下文）
    ↓
┌──────────────────────────────────────────┐
│           动态认知图谱                     │
│  ┌────────┐ ┌────────┐ ┌────────┐      │
│  │ 语义层  │ │ 因果层  │ │ 空间层  │      │
│  │        │ │        │ │        │      │
│  │ 约束边  │ │ 因果边  │ │ 位置边  │      │
│  └────────┘ └────────┘ └────────┘      │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│           推理引擎                         │
│  ┌────────┐ ┌────────┐ ┌────────┐      │
│  │ 逻辑   │ │ 因果   │ │ 空间   │      │
│  └────────┘ └────────┘ └────────┘      │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│           工具编排                         │
│  工具选择 → 执行 → 结果写回图谱            │
└──────────────────────────────────────────┘
    ↓
反馈闭环 → 图谱更新 → 持续演化
```

---

## 八、关键技术方案汇总

### 8.1 专家共识技术方案

| 核心问题 | 技术方案 | 技术组件 |
|----------|----------|----------|
| 语义理解 | 动态语义图谱 + 层次化注意力 | 多维度语义向量 |
| 上下文关联 | 上下文感知检索 + 图谱校验 | 意图分类 + 实体链接 |
| 知识组织 | 动态层次图谱 + 认知熵 | 重要性-时效性-关联密度 |
| 用户意图 | 贝叶斯意图推断 + 多层次建模 | 表层→深层→潜在意图 |
| 向量召回 | 多路召回 + Cross-Encoder | 向量+关键词+图谱 |
| 逻辑推理 | 约束边推理 + SMT求解 | 图谱约束边 |
| 因果推理 | 因果边 + 反事实模拟 | 因果图传播 |
| 空间推理 | 空间图谱层 | 空间关系正交 |
| 工具编排 | 可执行节点 + 拓扑排序 | 工具链编排 |
| **AGI架构** | **神经-符号混合系统** | **事件驱动闭环** |

---

## 九、总结

本设计方案V3.0基于10+位技术专家的多轮辩论，核心改进：

### 核心改进

1. **去掉所有束缚智能的规则** - 不再要价值约束，安全边界、人类审批
2. **聚焦智能增强** - 上下文理解、精准召回、关系推理、逻辑因果
3. **新增用户意图感知** - 显式记忆、回忆请求、贝叶斯意图推断
4. **新增凭据管理** - API Key安全存储、实体追踪
5. **新增高级推理** - 逻辑推理、因果推理、空间推理
6. **新增工具编排** - 智能工具选择与执行

### AGI架构

> **事件驱动的神经-符号混合系统**
> - 动态认知图谱为骨
> - 感知流为肉
> - 因果推理为脑
> - 工具调用为手
> - 语义理解为血液，渗透所有过程

### 设计目标

**我们的目标是AGI，不是"乖宝宝AI"**

- 不怕复杂
- 不怕性能问题（性能问题有专门的技术专家处理）
- 只要能实现AGI，什么技术都可以用

**目标**：让AI真正变聪明，能够：
- 理解语义和上下文
- 进行逻辑和因果推理
- 处理空间关系
- 智能调用工具
- 记住用户显式要求
- 自主学习和进化

---

**下一步**: 是否开始实现某个模块？

</details>
