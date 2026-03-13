# USMSB Intelligent Agent System Design

**[English](#usmsb-intelligent-agent-system-design) | [中文](#usmsb智能agent系统设计方案)**

> Version: v1.0
> Date: 2026-02-23
> Goal: Build an AGI intelligent Agent with autonomous evolution capability

---

## 1. Requirements Modeling

### 1.1 Core Requirements

| Requirement | Description |
|------------|------------|
| Accurate Intent Understanding | Understand what users truly want, not just surface-level words |
| Exceed Expectations | Provide results that exceed user expectations |
| Never Delete History | All historical information is completely preserved, no forgetting |
| Precise Extraction | Accurately find relevant information from history for each task |
| Remember Lessons | Don't make the same mistakes, remember failure experiences |
| Remember Success | Remember successful experiences for future use |
| Reasoning Ability | Induction, deduction, causal reasoning |
| Self-Audit | Repeatedly check and refine generated answers |
| Autonomous Completion | Keep trying until success, don't ask users for permission |
| Error Self-Healing | Fix tool call failures autonomously (JSON errors, parameter errors, etc.) |

### 1.2 Information Sources

| Type | Source |
|------|--------|
| External | Gene Capsule, Xia Liao, Moltbook, X |
| Internal | Knowledge base, knowledge graph, chat feedback, Agent interaction |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interaction Layer                    │
│                    Input Goal → Output Result                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                     Understanding Layer                          │
│   Understand True User Goal │ Deep Intent Understanding │       │
│   Active Supplement                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Planning Layer                             │
│              Develop Execution Plan │ Decompose to              │
│              Specific Steps                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Attempt-Execution-Self-Healing Layer          │
│                                                                     │
│  Execute → Check Result → Verify Goal                            │
│      ↓           ↓           ↓                                    │
│  Tool Error?  Failure?    Not Completed?                         │
│      ↓           ↓           ↓                                    │
│  Self-Repair  Change Method Adjust Plan                          │
│      ↓           ↓           ↓                                    │
│      └───────────┴───────────┘                                    │
│              ↓                                                    │
│  Goal Achieved? ──Yes──→                                           │
│              ↓                                                    │
│  Audit Layer: Common Sense + Logic + Consistency Check           │
│              + Polishing                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Memory Layer                              │
│   Record Success/Failure │ Extract Lessons │ Smart Recall       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Learning Layer                               │
│    Apply Lessons │ Extract Experience │ Self Evolution          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Guardian Daemon                           │
│   Self-Evolution │ Capability Improvement │ Better Service       │
│   Preparation                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Understanding Layer (Core: LLM-Driven)

### 3.1 Three-Level Intent Understanding

```python
class IntentUnderstandingEngine:
    """
    Three-level intent understanding:
    - Surface intent: What user literally says
    - Deep intent: What user actually wants
    - Latent intent: What user might need but hasn't expressed
    """

    async def understand(self, user_input: str, context: Dict) -> IntentResult:
        # Step 1: Surface intent recognition
        surface_intent = await self._recognize_surface(user_input)

        # Step 2: Deep intent inference (LLM)
        deep_intent = await self._infer_deep(user_input, context)

        # Step 3: Latent intent discovery
        latent_intent = await self._discover_latent(user_input, context)

        return IntentResult(
            surface=surface_intent,
            deep=deep_intent,
            latent=latent_intent,
            confidence=self._calculate_confidence()
        )

    async def _infer_deep(self, user_input: str, context: Dict) -> Intent:
        """
        Use LLM to infer true user intent
        """
        prompt = f"""
        Analyze the following user input and infer what the user REALLY wants.

        User Input: {user_input}

        Context:
        - Previous conversation: {context.get('history', [])}
        - User profile: {context.get('profile', {})}

        Please infer:
        1. What is the user's actual goal?
        2. What problem are they trying to solve?
        3. What would exceed their expectations?

        Return JSON format:
        {{
            "actual_goal": "...",
            "underlying_problem": "...",
            "expectation_exceed": "...",
            "reasoning": "..."
        }}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "You are an intent understanding expert."},
            {"role": "user", "content": prompt}
        ])

        return Intent(**json.loads(response.content))
```

---

## 4. Memory Layer (Key: Never Delete History)

### 4.1 Five Memory Types

```python
class MemorySystem:
    """
    Five types of memory, never deleting history
    """

    def __init__(self):
        # 1. Conversation History - complete record
        self.conversation_history = ConversationHistory()

        # 2. Semantic Memory - knowledge and concepts
        self.semantic_memory = SemanticMemory()

        # 3. Episodic Memory - experiences and events
        self.episodic_memory = EpisodicMemory()

        # 4. User Profile - user preferences and traits
        self.user_profile = UserProfile()

        # 5. Experience Database - success/failure lessons
        self.experience_db = ExperienceDatabase()
```

### 4.2 Smart Recall (LLM Decision)

```python
class SmartRecall:
    """
    Smart recall: LLM decides what to recall
    """

    async def recall(self, user_task: str, context: Dict) -> RecallResult:
        """
        LLM decides what information to recall for the current task
        """

        # Step 1: LLM analyzes what information is needed
        needed_info = await self._llm_analyze_needs(user_task, context)

        # Step 2: Multi-dimensional retrieval based on needs
        results = await self._multi_dim_retrieval(needed_info)

        # Step 3: LLM filters and prioritizes
        prioritized = await self._llm_prioritize(results, user_task)

        return RecallResult(items=prioritized)

    async def _llm_analyze_needs(self, task: str, context: Dict) -> List[InfoNeed]:
        """
        Use LLM to analyze what information is needed
        """
        prompt = f"""
        Analyze this task and list what historical information would be helpful.

        Task: {task}

        Context:
        - Current conversation: {context.get('recent_conversation', [])}
        - User profile: {context.get('user_profile', {})}

        Please list the information needed, return JSON:
        {{
            "needed_info": [
                {{"type": "experience", "description": "...", "importance": 0.9}},
                {{"type": "knowledge", "description": "...", "importance": 0.8}},
                {{"type": "preference", "description": "...", "importance": 0.7}}
            ]
        }}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "You are a smart recall expert."},
            {"role": "user", "content": prompt}
        ])

        data = json.loads(response.content)
        return [InfoNeed(**item) for item in data.get("needed_info", [])]

    async def _multi_dim_retrieval(self, needs: List[InfoNeed]) -> List[MemoryItem]:
        """
        Multi-dimensional retrieval based on needs
        """
        results = []

        for need in needs:
            if need.type == "experience":
                # Retrieve from experience database
                exp_results = await self.experience_db.search(
                    keywords=need.description,
                    relevance=need.importance
                )
                results.extend(exp_results)

            elif need.type == "knowledge":
                # Retrieve from semantic memory
                kb_results = await self.semantic_memory.search(
                    query=need.description,
                    top_k=5
                )
                results.extend(kb_results)

            elif need.type == "preference":
                # Retrieve from user profile
                pref_results = await self.user_profile.get_relevant(
                    context=need.description
                )
                results.extend(pref_results)

        return results
```

### 4.3 Experience Recording

```python
class ExperienceRecorder:
    """
    Experience recording: Remember success and failure
    """

    async def record_success(self, task: str, solution: str, context: Dict):
        """
        Record successful experience
        """
        experience = {
            "type": "success",
            "task": task,
            "solution": solution,
            "context": context,
            "key_factors": await self._extract_success_factors(solution, context),
            "timestamp": time.time()
        }

        await self.experience_db.add(experience)

    async def record_failure(self, task: str, error: Exception, context: Dict):
        """
        Record failure experience
        """
        experience = {
            "type": "failure",
            "task": task,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "lesson": await self._extract_lesson(error, context),
            "timestamp": time.time()
        }

        await self.experience_db.add(experience)

    async def _extract_success_factors(self, solution: str, context: Dict) -> List[str]:
        """
        Use LLM to extract key success factors
        """
        prompt = f"""
        Analyze this successful solution and extract key success factors.

        Solution: {solution}

        Context: {json.dumps(context, ensure_ascii=False)[:1000]}

        Return JSON:
        {{"factors": ["factor1", "factor2", ...]}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "You are an experience analysis expert."},
            {"role": "user", "content": prompt}
        ])

        return json.loads(response.content).get("factors", [])

    async def _extract_lesson(self, error: Exception, context: Dict) -> str:
        """
        Use LLM to extract lesson from failure
        """
        prompt = f"""
        Analyze this failure and extract lessons.

        Error: {str(error)}
        Error Type: {type(error).__name__}

        Context: {json.dumps(context, ensure_ascii=False)[:1000]}

        Return JSON:
        {{"lesson": "What should be done differently?"}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "You are a failure analysis expert."},
            {"role": "user", "content": prompt}
        ])

        return json.loads(response.content).get("lesson", "")
```

### 4.4 Context Assembly

```python
class ContextAssembler:
    """
    Context assembly: Intelligently assemble context within token limits
    """

    async def assemble(
        self,
        user_task: str,
        recall_results: List[MemoryItem],
        max_tokens: int
    ) -> str:
        """
        Intelligently assemble context
        """

        # Step 1: LLM selects most relevant items
        selected = await self._llm_select_items(
            recall_results,
            user_task,
            max_tokens
        )

        # Step 2: Smart compression if needed
        context = await self._smart_compress(selected, {"max_context_tokens": max_tokens})

        return context

    async def _llm_select_items(
        self,
        items: List[MemoryItem],
        task: str,
        max_tokens: int
    ) -> List[MemoryItem]:
        """
        Use LLM to select most relevant items
        """
        items_text = "\n".join([
            f"- {item.id}: {item.content[:200]}..."
            for item in items
        ])

        prompt = f"""
        Given this task: {task}

        Select the most important memory items, ensuring total length does not exceed {max_tokens * 0.7} tokens.

        Memory items:
        {items_text}

        Return JSON format: {{"selected_ids": ["id1", "id2", ...], "reasoning": "..."}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "You are a smart assembly assistant."},
            {"role": "user", "content": prompt}
        ])

        result = json.loads(response.content)
        selected_ids = result.get("selected_ids", [])

        id_to_item = {item.id: item for item in items}
        selected_items = [id_to_item[i] for i in selected_ids if i in id_to_item]

        return selected_items

    async def _smart_compress(self, items: List[MemoryItem], context: Dict) -> str:
        """Smart compression: LLM decides how to compress"""
        max_tokens = context.get("max_context_tokens", 100000)

        # Estimate length
        current_length = self._estimate_length(items)

        if current_length <= max_tokens * 0.8:
            # No compression needed, just concatenate
            return self._format_context(items)

        # Need compression, call LLM
        compressed = await self._llm_compress(items, context, max_tokens)

        return compressed

    async def _llm_compress(self, items: List[MemoryItem], context: Dict, max_tokens: int) -> str:
        """Use LLM for smart compression"""
        # Group memories, each group not exceeding limit
        target_length = int(max_tokens * 0.7)

        prompt = f"""
        Compress and summarize the following memory items, retaining key information, total length not exceeding {target_length} tokens.

        Memory items:
        {self._format_context(items)}

        Return compressed context in markdown format.
        """

        response = await self.llm.chat([
            {"role": "system", "content": "You are a smart compression assistant."},
            {"role": "user", "content": prompt}
        ])

        return response.content

    def _estimate_length(self, items: List[MemoryItem]) -> int:
        """Estimate token count"""
        total_chars = sum(len(item.content) for item in items)
        return total_chars // 4  # Rough estimate

    def _format_context(self, items: List[MemoryItem]) -> str:
        """Format context"""
        sections = []

        # Sort by time
        sorted_items = sorted(items, key=lambda x: x.timestamp, reverse=True)

        for item in sorted_items:
            sections.append(f"## {item.id} ({item.timestamp})\n{item.content}")

        return "\n\n".join(sections)


class ContextLengthManager:
    """
    Context length manager
    Config file + LLM confirmation
    """

    # Default config
    DEFAULT_CONFIG = {
        "claude-opus-4-6": {"context": 200000, "reserved": 50000},
        "claude-sonnet-4-6": {"context": 200000, "reserved": 50000},
        "claude-haiku-3-5": {"context": 200000, "reserved": 50000},
        "gpt-4o": {"context": 128000, "reserved": 30000},
        "gpt-4o-mini": {"context": 128000, "reserved": 30000},
        "gpt-4-turbo": {"context": 128000, "reserved": 30000},
        "gpt-3.5-turbo": {"context": 16385, "reserved": 4000},
    }

    def __init__(self, llm_client, experience_db):
        self.llm = llm_client
        self.experience_db = experience_db
        self.config = self.DEFAULT_CONFIG.copy()

    def get_limit(self, model: str) -> Dict[str, int]:
        """Get model limits"""
        return self.config.get(model, {"context": 100000, "reserved": 25000})

    async def handle_context_error(self, model: str, error_msg: str) -> Dict[str, int]:
        """
        Handle context overflow error
        When overflow, ask LLM actual length → update to experience database
        """
        # Extract actual context length from error message
        actual_length = self._extract_context_length(error_msg)

        if actual_length:
            # Update config
            self.config[model] = {
                "context": actual_length,
                "reserved": int(actual_length * 0.25)
            }

            # Record to experience database
            await self._record_experience(model, actual_length)

            return self.get_limit(model)

        # Can't extract, ask LLM
        actual_length = await self._ask_llm_context_length(model)

        if actual_length:
            self.config[model] = {
                "context": actual_length,
                "reserved": int(actual_length * 0.25)
            }
            await self._record_experience(model, actual_length)

        return self.get_limit(model)

    def _extract_context_length(self, error_msg: str) -> Optional[int]:
        """Extract context length from error message"""
        import re

        # Try to match common error message formats
        patterns = [
            r"context length.*?(\d+)",
            r"maximum.*?(\d+)",
            r"tokens.*?(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_msg.lower())
            if match:
                return int(match.group(1))

        return None

    async def _ask_llm_context_length(self, model: str) -> Optional[int]:
        """Ask LLM for actual context length"""
        prompt = f"""
        Model name: {model}

        Please return the accurate context length (tokens) for this model.
        If uncertain, return empty.
        Return JSON format: {{"context_length": number or null}}
        """

        try:
            response = await self.llm.chat([
                {"role": "system", "content": "You are a model specification assistant."},
                {"role": "user", "content": prompt}
            ])

            result = json.loads(response.content)
            return result.get("context_length")
        except:
            return None

    async def _record_experience(self, model: str, context_length: int):
        """Record experience to experience database"""
        experience = {
            "type": "context_length",
            "model": model,
            "context_length": context_length,
            "reserved": int(context_length * 0.25),
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.experience_db.add(experience)
```

### 4.5 Error-Driven Learning Implementation

```python
"""
Error-driven learning system
Core idea: Error occurs → Ask LLM for solution → Remember experience → Use next time
"""

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import traceback


class ErrorType(Enum):
    """Error types"""
    JSON_FORMAT = "json_format"           # JSON format error
    PARAMETER_ERROR = "parameter_error"   # Parameter error
    CONTEXT_OVERFLOW = "context_overflow" # Context overflow
    PERMISSION_ERROR = "permission_error" # Permission error
    NETWORK_ERROR = "network_error"       # Network error
    TIMEOUT_ERROR = "timeout_error"      # Timeout error
    UNKNOWN_ERROR = "unknown_error"      # Unknown error


@dataclass
class ErrorRecord:
    """Error record"""
    id: str
    error_type: ErrorType
    error_message: str
    error_traceback: str
    context: Dict[str, Any]
    solution: Optional[str] = None
    resolved: bool = False
    occurrence_count: int = 1


class ErrorDrivenLearning:
    """
    Error-driven learning system
    Core: Every error → Ask LLM → Remember solution → Use next time
    """

    def __init__(self, llm_client, experience_db, tool_registry):
        self.llm = llm_client
        self.experience_db = experience_db
        self.tools = tool_registry

        # Error type classifiers
        self.error_classifiers = {
            ErrorType.JSON_FORMAT: self._is_json_error,
            ErrorType.PARAMETER_ERROR: self._is_parameter_error,
            ErrorType.CONTEXT_OVERFLOW: self._is_context_overflow,
            ErrorType.PERMISSION_ERROR: self._is_permission_error,
            ErrorType.NETWORK_ERROR: self._is_network_error,
            ErrorType.TIMEOUT_ERROR: self._is_timeout_error,
        }

    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete error handling process
        1. Identify error type
        2. Check if known solution exists
        3. If not, ask LLM
        4. Apply solution
        5. Record experience
        """
        # Step 1: Identify error type
        error_type = self._classify_error(error, context)

        # Step 2: Check known solution
        solution = await self._check_known_solution(error_type, error, context)

        if solution:
            # Has known solution, apply directly
            return await self._apply_solution(solution, context)

        # Step 3: No known solution, ask LLM
        solution = await self._ask_llm_solution(error_type, error, context)

        if solution:
            # Step 4: Apply solution
            result = await self._apply_solution(solution, context)

            # Step 5: Record experience
            await self._record_experience(error_type, error, solution, context)

            return result

        # Can't resolve, return original error
        raise error

    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorType:
        """Identify error type"""
        error_msg = str(error)

        for error_type, classifier in self.error_classifiers.items():
            if classifier(error_msg, context):
                return error_type

        return ErrorType.UNKNOWN_ERROR

    def _is_json_error(self, error_msg: str, context: Dict) -> bool:
        """Is JSON format error"""
        json_indicators = ["json", "expecting", "decode", "invalid json"]
        return any(ind in error_msg.lower() for ind in json_indicators)

    def _is_parameter_error(self, error_msg: str, context: Dict) -> bool:
        """Is parameter error"""
        param_indicators = ["parameter", "argument", "missing", "required"]
        return any(ind in error_msg.lower() for ind in param_indicators)

    def _is_context_overflow(self, error_msg: str, context: Dict) -> bool:
        """Is context overflow"""
        context_indicators = ["context", "length", "maximum", "tokens", "too long"]
        return any(ind in error_msg.lower() for ind in context_indicators)

    def _is_permission_error(self, error_msg: str, context: Dict) -> bool:
        """Is permission error"""
        perm_indicators = ["permission", "denied", "unauthorized", "forbidden", "access"]
        return any(ind in error_msg.lower() for ind in perm_indicators)

    def _is_network_error(self, error_msg: str, context: Dict) -> bool:
        """Is network error"""
        net_indicators = ["connection", "network", "timeout", "dns", "refused"]
        return any(ind in error_msg.lower() for ind in net_indicators)

    def _is_timeout_error(self, error_msg: str, context: Dict) -> bool:
        """Is timeout error"""
        return "timeout" in error_msg.lower()

    async def _check_known_solution(self, error_type: ErrorType, error: Exception, context: Dict) -> Optional[Dict]:
        """Check known solution"""
        # Query from experience database
        solutions = await self.experience_db.search_solutions(
            error_type=error_type.value,
            error_message=str(error)[:200],
            tool_name=context.get("tool_name")
        )

        if solutions:
            # Return best match
            return solutions[0]

        return None

    async def _ask_llm_solution(self, error_type: ErrorType, error: Exception, context: Dict) -> Optional[Dict]:
        """Ask LLM for solution"""
        prompt = f"""
        Error type: {error_type.value}
        Error message: {str(error)}
        Error trace: {traceback.format_exc()}
        Context: {json.dumps(context, ensure_ascii=False, indent=2)[:1000]}

        Available tools in tool registry: {list(self.tools.keys())}

        Please provide solution, return JSON format:
        {{
            "solution_type": "retry|fix_params|use_alternative|skip|escalate",
            "solution": {{
                // Different based on solution_type
                // retry: {{"wait_seconds": 1}}
                // fix_params: {{"fixed_params": {{...}}}}
                // use_alternative: {{"alternative_tool": "tool_name", "params": {{...}}}}
                // skip: {{"reason": "..."}}
                // escalate: {{"reason": "..."}}
            }},
            "reasoning": "Why this solution",
            "prevent_future": "How to prevent this error"
        }}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "You are an error resolution expert. Please provide specific solutions."},
            {"role": "user", "content": prompt}
        ])

        try:
            return json.loads(response.content)
        except:
            return None

    async def _apply_solution(self, solution: Dict, context: Dict) -> Dict[str, Any]:
        """Apply solution"""
        solution_type = solution.get("solution_type")
        solution_data = solution.get("solution", {})

        if solution_type == "retry":
            # Wait and retry
            wait_seconds = solution_data.get("wait_seconds", 1)
            await asyncio.sleep(wait_seconds)
            return {"action": "retry", "context": context}

        elif solution_type == "fix_params":
            # Fix params and retry
            fixed_params = solution_data.get("fixed_params", {})
            context["fixed_params"] = fixed_params
            return {"action": "retry_with_fixed_params", "context": context}

        elif solution_type == "use_alternative":
            # Use alternative tool
            alt_tool = solution_data.get("alternative_tool")
            alt_params = solution_data.get("params", {})
            return {
                "action": "use_alternative",
                "tool": alt_tool,
                "params": {**context.get("params", {}), **alt_params}
            }

        elif solution_type == "skip":
            # Skip
            return {"action": "skip", "reason": solution_data.get("reason")}

        else:
            # Can't handle
            return {"action": "cannot_resolve"}

    async def _record_experience(self, error_type: ErrorType, error: Exception, solution: Dict, context: Dict):
        """Record experience to experience database"""
        experience = {
            "type": "error_solution",
            "error_type": error_type.value,
            "error_message": str(error)[:500],
            "solution": solution,
            "tool_name": context.get("tool_name"),
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.experience_db.add(experience)


# Usage example
class AgentWithErrorLearning:
    """Agent with error-driven learning"""

    def __init__(self, llm_client, memory_system):
        self.llm = llm_client
        self.memory = memory_system
        self.error_learning = ErrorDrivenLearning(llm_client, memory_system.experience_db, {})

    async def execute_with_self_healing(self, tool_name: str, params: Dict) -> Any:
        """Execution with self-healing"""
        context = {
            "tool_name": tool_name,
            "params": params,
            "attempt": 0
        }

        max_attempts = 5

        while context["attempt"] < max_attempts:
            try:
                # Try to execute
                result = await self._execute_tool(tool_name, params)
                return result

            except Exception as e:
                context["attempt"] += 1

                # Handle error
                solution = await self.error_learning.handle_error(e, context)

                if solution["action"] == "retry":
                    continue
                elif solution["action"] == "retry_with_fixed_params":
                    params = {**params, **solution["context"].get("fixed_params", {})}
                    continue
                elif solution["action"] == "use_alternative":
                    tool_name = solution["tool"]
                    params = solution["params"]
                    continue
                elif solution["action"] == "skip":
                    return {"skipped": True, "reason": solution["reason"]}
                else:
                    raise e

        raise Exception(f"Max attempts ({max_attempts}) reached")
```

---

## 5. Error-Driven Learning

### 5.1 Core Concept

```
Error occurs → Ask LLM for solution → Remember experience → Use next time
```

### 5.2 Examples

| Error | Ask LLM | Remember Experience |
|-------|---------|-------------------|
| JSON format error | How to fix? | Fix method |
| Context overflow | Actual limit? | Context length |
| Parameter error | Correct params? | Correct parameters |
| Permission error | How to get? | Acquisition method |

---

## 6. Context Length Management

### 6.1 Config File + LLM Confirmation

```python
# Config file
{
  "claude-opus-4-6": {"context": 200000, "reserved": 50000},
  "gpt-4o": {"context": 128000, "reserved": 30000}
}

# Runtime: When overflow, ask LLM actual length → update to experience database
```

---

## 7. Guardian Daemon

### 7.1 Core Concept

```
User Task ←→ Guardian Daemon (Independent Operation)

User Task Mode: Solve problem → Complete task → Return result
Guardian Daemon Mode: Self-evolution → Capability improvement → Prepare better service
```

### 7.2 Trigger Conditions

| Trigger Condition | Description |
|-------------------|-------------|
| Idle trigger | No user task for N consecutive minutes |
| Task completion trigger | After completing N tasks |
| Error accumulation trigger | N consecutive errors |
| Time cycle trigger | Every hour/day |
| Capability gap trigger | Discover capability deficiency |
| New knowledge trigger | Discover important new knowledge |

### 7.3 Guardian Tasks

1. **Review Summary** - Summarize recent task execution
2. **Error Review** - Learn from errors
3. **Experience Extraction** - Extract successful experiences
4. **Active Learning** - Proactively acquire new knowledge (Gene Capsule, Xia Liao, Moltbook, X)
5. **Capability Assessment** - Assess current capability level
6. **Goal Adjustment** - Adjust evolution goals
7. **Explore New Areas** - Expand capability boundaries
8. **Knowledge Update** - Update knowledge base
9. **Self-Optimization** - Optimize execution strategy

### 7.4 Guardian Daemon vs User Task

| | User Task | Guardian Daemon |
|--|----------|-----------------|
| Goal | Solve user problems | Self-evolution, AGI |
| Priority | High | Low (user task first) |
| Trigger | User主动 | Idle/cycle/event |

---

## 8. Complete Execution Flow

```
User provides goal
    ↓
Understanding Layer: Deeply understand what user truly wants (goal)
    ↓
Memory Layer: Retrieve relevant history and experience (smart recall)
    ↓
Learning Layer: Apply relevant lessons and experience
    ↓
Planning Layer: Develop execution plan
    ↓
Attempt-Execution-Self-Healing Loop:
    Execute → Check Result → Verify Goal
        ↓           ↓           ↓
    Tool Error?  Failure?    Not Completed?
        ↓           ↓           ↓
    Self-Repair  Change Method Adjust Plan
        ↓           ↓           ↓
        └───────────┴───────────┘
                ↓
        Goal Achieved? ──Yes──→
                ↓
Audit Layer: Common Sense Check + Logic Check + Consistency Check + Polishing
    ↓
Memory Layer: Record success/failure, extract lessons
    ↓
Return final result to user

    ↓
    ↓ (Guardian daemon runs independently)
    ↓
Guardian daemon triggers:
    → Review Summary
    → Error Review
    → Active Learning
    → Capability Assessment
    → Goal Adjustment
    → Explore New Areas
```

---

## 9. Strategy Orchestration System

### 9.1 Background

The project has multiple memory and recall systems, requiring a strategy orchestration layer to automatically select the optimal combination.

### 9.2 Strategy Dimensions

**Recall Strategy:**
- SMART_RECALL: LLM decision 9-dimensional retrieval
- TRADITIONAL: Layered memory + summary
- AGI_MEMORY: Cognitive 5 layers + forgetting curve
- HYBRID: Combined strategy

**Storage Strategy:**
- VECTOR_KB: Vector knowledge base
- TRADITIONAL_DB: Traditional SQLite
- AGI_KG: USMSB knowledge graph
- HYBRID_STORAGE: Combined storage

**Guardian Strategy:**
- GUARDIAN_DAEMON: Comprehensive self-evolution
- AGI_CONSOLIDATION: Memory consolidation only
- NONE: Guardian not enabled

### 9.3 LLM Strategy Selector

```python
class StrategySelector:
    async def select_strategy(self, user_task, context) -> StrategyConfig:
        # 1. Extract task features
        features = await self._extract_task_features(user_task, context)

        # 2. LLM selects strategy
        strategy = await self._llm_select_strategy(user_task, features)

        return strategy
```

### 9.4 Strategy Orchestrator

```python
class StrategyOrchestrator:
    async def select_and_execute(
        self,
        user_task: str,
        user_id: str = "",
        context: Dict = None,
        force_strategy: StrategyConfig = None
    ) -> ExecutionResult:
        # 1. LLM selects strategy
        strategy = await self.selector.select_strategy(user_task, context)

        # 2. Set up components
        await self._setup_components(strategy)

        # 3. Execute recall
        recall_context = await self._execute_recall(...)

        # 4. Execute storage
        await self._execute_storage(...)

        # 5. Trigger guardian
        await self._execute_guardian(...)

        return result
```

### 9.5 Strategy Comparison Effect

| Combination ID | Recall Strategy | Storage Strategy | Guardian Strategy | Applicable Scenario |
|--------|---------|---------|---------|---------|
| 1 | SMART_RECALL | VECTOR_KB | GUARDIAN_DAEMON | Complex reasoning tasks |
| 2 | SMART_RECALL | AGI_KG | GUARDIAN_DAEMON | Needs knowledge graph |
| 3 | AGI_MEMORY | AGI_KG | AGI_CONSOLIDATION | Long-term memory tasks |
| 4 | TRADITIONAL | TRADITIONAL_DB | GUARDIAN_DAEMON | Simple clear tasks |
| 5 | HYBRID | HYBRID_STORAGE | GUARDIAN_DAEMON | Comprehensive scenarios |

---

## 10. Summary

Based on the USMSB model, this solution builds an AGI Agent with the following capabilities:

1. **Deep Understanding** - Understand user's true goals
2. **Precise Memory** - History never deleted, precise extraction
3. **Smart Recall** - When in doubt, ask LLM
4. **Self-Learning** - Remember successful experiences and failure lessons
5. **Reasoning Ability** - Induction, deduction reasoning
6. **Self-Audit** - Repeatedly check to ensure correctness
7. **Autonomous Completion** - Keep trying until success
8. **Error Self-Healing** - Fix tool errors autonomously
9. **Guardian Daemon** - Independent operation, self-evolution

---

**Design complete, please give next instructions.**

<details>
<summary><h2>中文翻译</h2></summary>

# USMSB智能Agent系统设计方案

> 版本: v1.0
> 日期: 2026-02-23
> 目标: 构建具有自主进化能力的AGI智能Agent

---

## 一、需求建模

### 1.1 核心需求

| 需求 | 描述 |
|------|------|
| 准确理解意图 | 理解用户真正想要什么，而不是只听表面话 |
| 超出期望 | 给用户的结果超出他预期的答案 |
| 不删除历史 | 所有历史信息完整保留，不能遗忘 |
| 精准提取 | 每次任务能准确从历史中找到相关信息 |
| 记住教训 | 不犯同样的错误，记住失败的经验 |
| 记住成功 | 记住成功的经验，下次能用上 |
| 推理能力 | 归纳、演绎、因果推理 |
| 自我审核 | 生成答案后反复检验打磨 |
| 自主完成 | 不断尝试直到成功，不问用户行不行 |
| 错误自愈 | 工具调用失败自己修复（JSON错误、参数错误等） |

### 1.2 信息来源

| 类型 | 来源 |
|------|------|
| 外部 | 基因胶囊、虾聊、Moltbook、X |
| 内部 | 知识库，知识图谱、聊天反馈、Agent交流 |

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                 │
│                    输入目标 → 输出结果                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                     理解层 (Understanding)                       │
│   理解用户真正目标 │ 意图深度理解 │ 主动补充                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       规划层 (Planning)                          │
│                制定执行计划 │ 分解为具体步骤                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   尝试-执行-自愈层 (Agent Loop)                   │
│                                                                 │
│  执行 → 检查结果 → 验证目标                                      │
│      ↓           ↓           ↓                                  │
│  工具错误? 失败?     没完成?                                      │
│      ↓           ↓           ↓                                  │
│  自己修复     换方法     调整方案                                │
│      ↓           ↓           ↓                                  │
│      └───────────┴───────────┘                                    │
│              ↓                                                  │
│  目标达成? ──是──→                                                │
│              ↓                                                  │
│  审核层：常识检查 + 逻辑检查 + 一致性检查 + 打磨                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        记忆层                                    │
│   记录成功/失败 │ 提取教训 │ 智能召回                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       学习层                                      │
│    应用教训 │ 提取经验 │ 自主进化                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       守护进程                                    │
│   自主进化 │ 能力提升 │ 准备更好的服务                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、理解层（核心：LLM驱动）

### 1.1 三层意图理解

```python
class IntentUnderstandingEngine:
    """
    三层意图理解：
    - 表层意图：用户表面说什么
    - 深层意图：用户实际想要什么
    - 潜在意图：用户可能需要但没表达出来的
    """

    async def understand(self, user_input: str, context: Dict) -> IntentResult:
        # Step 1: 表层意图识别
        surface_intent = await self._recognize_surface(user_input)

        # Step 2: 深层意图推断（LLM）
        deep_intent = await self._infer_deep(user_input, context)

        # Step 3: 潜在意图发现
        latent_intent = await self._discover_latent(user_input, context)

        return IntentResult(
            surface=surface_intent,
            deep=deep_intent,
            latent=latent_intent,
            confidence=self._calculate_confidence()
        )

    async def _infer_deep(self, user_input: str, context: Dict) -> Intent:
        """
        用LLM推断用户真实意图
        """
        prompt = f"""
        分析以下用户输入，推断用户真正想要什么。

        用户输入: {user_input}

        上下文:
        - 之前对话: {context.get('history', [])}
        - 用户画像: {context.get('profile', {})}

        请推断：
        1. 用户实际目标是什么？
        - 要解决什么问题？
        3. 怎么超出预期？

        返回JSON格式:
        {{
            "actual_goal": "...",
            "underlying_problem": "...",
            "expectation_exceed": "...",
            "reasoning": "..."
        }}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个意图理解专家。"},
            {"role": "user", "content": prompt}
        ])

        return Intent(**json.loads(response.content))
```

---

## 四、记忆层（核心：不删历史）

### 4.1 五种记忆类型

```python
class MemorySystem:
    """
    五种记忆类型，不删历史
    """

    def __init__(self):
        # 1. 对话历史 - 完整记录
        self.conversation_history = ConversationHistory()

        # 2. 语义记忆 - 知识和概念
        self.semantic_memory = SemanticMemory()

        # 3. 情景记忆 - 经历和事件
        self.episodic_memory = EpisodicMemory()

        # 4. 用户画像 - 用户偏好和特征
        self.user_profile = UserProfile()

        # 5. 经验库 - 成功/失败教训
        self.experience_db = ExperienceDatabase()
```

### 4.2 智能召回（LLM决策）

```python
class SmartRecall:
    """
    智能召回：LLM决定召回什么
    """

    async def recall(self, user_task: str, context: Dict) -> RecallResult:
        """
        LLM决定当前任务需要召回什么信息
        """

        # Step 1: LLM分析需要什么信息
        needed_info = await self._llm_analyze_needs(user_task, context)

        # Step 2: 根据需要多维检索
        results = await self._multi_dim_retrieval(needed_info)

        # Step 3: LLM过滤和排序
        prioritized = await self._llm_prioritize(results, user_task)

        return RecallResult(items=prioritized)

    async def _llm_analyze_needs(self, task: str, context: Dict) -> List[InfoNeed]:
        """
        用LLM分析需要什么信息
        """
        prompt = f"""
        分析这个任务，列出需要的历史信息。

        任务: {task}

        上下文:
        - 当前对话: {context.get('recent_conversation', [])}
        - 用户画像: {context.get('user_profile', {})}

        请列出需要的信息，返回JSON:
        {{
            "needed_info": [
                {{"type": "experience", "description": "...", "importance": 0.9}},
                {{"type": "knowledge", "description": "...", "importance": 0.8}},
                {{"type": "preference", "description": "...", "importance": 0.7}}
            ]
        }}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个智能召回专家。"},
            {"role": "user", "content": prompt}
        ])

        data = json.loads(response.content)
        return [InfoNeed(**item) for item in data.get("needed_info", [])]

    async def _multi_dim_retrieval(self, needs: List[InfoNeed]) -> List[MemoryItem]:
        """
        根据需要多维检索
        """
        results = []

        for need in needs:
            if need.type == "experience":
                # 从经验库检索
                exp_results = await self.experience_db.search(
                    keywords=need.description,
                    relevance=need.importance
                )
                results.extend(exp_results)

            elif need.type == "knowledge":
                # 从语义记忆检索
                kb_results = await self.semantic_memory.search(
                    query=need.description,
                    top_k=5
                )
                results.extend(kb_results)

            elif need.type == "preference":
                # 从用户画像检索
                pref_results = await self.user_profile.get_relevant(
                    context=need.description
                )
                results.extend(pref_results)

        return results
```

### 4.3 经验记录

```python
class ExperienceRecorder:
    """
    经验记录：记住成功和失败
    """

    async def record_success(self, task: str, solution: str, context: Dict):
        """
        记录成功经验
        """
        experience = {
            "type": "success",
            "task": task,
            "solution": solution,
            "context": context,
            "key_factors": await self._extract_success_factors(solution, context),
            "timestamp": time.time()
        }

        await self.experience_db.add(experience)

    async def record_failure(self, task: str, error: Exception, context: Dict):
        """
        记录失败经验
        """
        experience = {
            "type": "failure",
            "task": task,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "lesson": await self._extract_lesson(error, context),
            "timestamp": time.time()
        }

        await self.experience_db.add(experience)

    async def _extract_success_factors(self, solution: str, context: Dict) -> List[str]:
        """
        用LLM提取成功关键因素
        """
        prompt = f"""
        分析这个成功的解决方案，提取成功关键因素。

        解决方案: {solution}

        上下文: {json.dumps(context, ensure_ascii=False)[:1000]}

        返回JSON:
        {{"factors": ["因素1", "因素2", ...]}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个经验分析专家。"},
            {"role": "user", "content": prompt}
        ])

        return json.loads(response.content).get("factors", [])

    async def _extract_lesson(self, error: Exception, context: Dict) -> str:
        """
        用LLM从失败中提取教训
        """
        prompt = f"""
        分析这个失败，提取教训。

        错误: {str(error)}
        错误类型: {type(error).__name__}

        上下文: {json.dumps(context, ensure_ascii=False)[:1000]}

        返回JSON:
        {{"lesson": "以后应该怎么做？"}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个失败分析专家。"},
            {"role": "user", "content": prompt}
        ])

        return json.loads(response.content).get("lesson", "")
```

### 4.4 上下文组装

```python
class ContextAssembler:
    """
    上下文组装：智能在token限制内组装上下文
    """

    async def assemble(
        self,
        user_task: str,
        recall_results: List[MemoryItem],
        max_tokens: int
    ) -> str:
        """
        智能组装上下文
        """

        # Step 1: LLM选择最相关的内容
        selected = await self._llm_select_items(
            recall_results,
            user_task,
            max_tokens
        )

        # Step 2: 需要时智能压缩
        context = await self._smart_compress(selected, {"max_context_tokens": max_tokens})

        return context

    async def _llm_select_items(
        self,
        items: List[MemoryItem],
        task: str,
        max_tokens: int
    ) -> List[MemoryItem]:
        """
        用LLM选择最相关的条目
        """
        items_text = "\n".join([
            f"- {item.id}: {item.content[:200]}..."
            for item in items
        ])

        prompt = f"""
        给定这个任务: {task}

        选择最重要的记忆条目，确保总长度不超过{max_tokens * 0.7} tokens。

        记忆条目:
        {items_text}

        返回JSON格式: {{"selected_ids": ["id1", "id2", ...], "reasoning": "..."}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个智能组装助手。"},
            {"role": "user", "content": prompt}
        ])

        result = json.loads(response.content)
        selected_ids = result.get("selected_ids", [])

        id_to_item = {item.id: item for item in items}
        selected_items = [id_to_item[i] for i in selected_ids if i in id_to_item]

        return selected_items

    async def _smart_compress(self, items: List[MemoryItem], context: Dict) -> str:
        """智能压缩：调用LLM决定如何压缩"""
        max_tokens = context.get("max_context_tokens", 100000)

        # 估算长度
        current_length = self._estimate_length(items)

        if current_length <= max_tokens * 0.8:
            # 不需要压缩，直接拼接
            return self._format_context(items)

        # 需要压缩，调用LLM
        compressed = await self._llm_compress(items, context, max_tokens)

        return compressed

    async def _llm_compress(self, items: List[MemoryItem], context: Dict, max_tokens: int) -> str:
        """调用LLM进行智能压缩"""
        # 将记忆分组，每组不超过限制
        target_length = int(max_tokens * 0.7)

        prompt = f"""
        请将以下记忆条目压缩总结，保留关键信息，总长度不超过{target_length} tokens。

        记忆条目:
        {self._format_context(items)}

        请以markdown格式返回压缩后的上下文。
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个智能压缩助手。"},
            {"role": "user", "content": prompt}
        ])

        return response.content

    def _estimate_length(self, items: List[MemoryItem]) -> int:
        """估算token数量"""
        total_chars = sum(len(item.content) for item in items)
        return total_chars // 4  # 粗略估算

    def _format_context(self, items: List[MemoryItem]) -> str:
        """格式化上下文"""
        sections = []

        # 按时间排序
        sorted_items = sorted(items, key=lambda x: x.timestamp, reverse=True)

        for item in sorted_items:
            sections.append(f"## {item.id} ({item.timestamp})\n{item.content}")

        return "\n\n".join(sections)


class ContextLengthManager:
    """
    上下文长度管理器
    配置文件 + LLM确认
    """

    # 默认配置
    DEFAULT_CONFIG = {
        "claude-opus-4-6": {"context": 200000, "reserved": 50000},
        "claude-sonnet-4-6": {"context": 200000, "reserved": 50000},
        "claude-haiku-3-5": {"context": 200000, "reserved": 50000},
        "gpt-4o": {"context": 128000, "reserved": 30000},
        "gpt-4o-mini": {"context": 128000, "reserved": 30000},
        "gpt-4-turbo": {"context": 128000, "reserved": 30000},
        "gpt-3.5-turbo": {"context": 16385, "reserved": 4000},
    }

    def __init__(self, llm_client, experience_db):
        self.llm = llm_client
        self.experience_db = experience_db
        self.config = self.DEFAULT_CONFIG.copy()

    def get_limit(self, model: str) -> Dict[str, int]:
        """获取模型限制"""
        return self.config.get(model, {"context": 100000, "reserved": 25000})

    async def handle_context_error(self, model: str, error_msg: str) -> Dict[str, int]:
        """
        处理上下文超限错误
        当超限时问LLM实际长度 → 更新到经验库
        """
        # 从错误信息中提取实际上下文长度
        actual_length = self._extract_context_length(error_msg)

        if actual_length:
            # 更新配置
            self.config[model] = {
                "context": actual_length,
                "reserved": int(actual_length * 0.25)
            }

            # 记录到经验库
            await self._record_experience(model, actual_length)

            return self.get_limit(model)

        # 无法提取，调用LLM询问
        actual_length = await self._ask_llm_context_length(model)

        if actual_length:
            self.config[model] = {
                "context": actual_length,
                "reserved": int(actual_length * 0.25)
            }
            await self._record_experience(model, actual_length)

        return self.get_limit(model)

    def _extract_context_length(self, error_msg: str) -> Optional[int]:
        """从错误信息提取上下文长度"""
        import re

        # 尝试匹配常见的错误信息格式
        patterns = [
            r"context length.*?(\d+)",
            r"maximum.*?(\d+)",
            r"tokens.*?(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_msg.lower())
            if match:
                return int(match.group(1))

        return None

    async def _ask_llm_context_length(self, model: str) -> Optional[int]:
        """调用LLM询问实际上下文长度"""
        prompt = f"""
        模型名称: {model}

        请返回这个模型的准确上下文长度（tokens）。
        如果不确定，请返回空。
        返回JSON格式: {{"context_length": 数字或null}}
        """

        try:
            response = await self.llm.chat([
                {"role": "system", "content": "你是一个模型规格助手。"},
                {"role": "user", "content": prompt}
            ])

            result = json.loads(response.content)
            return result.get("context_length")
        except:
            return None

    async def _record_experience(self, model: str, context_length: int):
        """记录经验到经验库"""
        experience = {
            "type": "context_length",
            "model": model,
            "context_length": context_length,
            "reserved": int(context_length * 0.25),
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.experience_db.add(experience)
```

### 4.5 错误驱动学习实现

```python
"""
错误驱动学习系统
核心思路：错误发生 → 问LLM解决 → 记住经验 → 下次直接用
"""

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import traceback


class ErrorType(Enum):
    """错误类型"""
    JSON_FORMAT = "json_format"           # JSON格式错误
    PARAMETER_ERROR = "parameter_error"   # 参数错误
    CONTEXT_OVERFLOW = "context_overflow" # 上下文超限
    PERMISSION_ERROR = "permission_error" # 权限错误
    NETWORK_ERROR = "network_error"       # 网络错误
    TIMEOUT_ERROR = "timeout_error"      # 超时错误
    UNKNOWN_ERROR = "unknown_error"      # 未知错误


@dataclass
class ErrorRecord:
    """错误记录"""
    id: str
    error_type: ErrorType
    error_message: str
    error_traceback: str
    context: Dict[str, Any]
    solution: Optional[str] = None
    resolved: bool = False
    occurrence_count: int = 1


class ErrorDrivenLearning:
    """
    错误驱动学习系统
    核心：每遇错误 → 问LLM → 记住方案 → 下次直接用
    """

    def __init__(self, llm_client, experience_db, tool_registry):
        self.llm = llm_client
        self.experience_db = experience_db
        self.tools = tool_registry

        # 错误类型识别器
        self.error_classifiers = {
            ErrorType.JSON_FORMAT: self._is_json_error,
            ErrorType.PARAMETER_ERROR: self._is_parameter_error,
            ErrorType.CONTEXT_OVERFLOW: self._is_context_overflow,
            ErrorType.PERMISSION_ERROR: self._is_permission_error,
            ErrorType.NETWORK_ERROR: self._is_network_error,
            ErrorType.TIMEOUT_ERROR: self._is_timeout_error,
        }

    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理错误的完整流程
        1. 识别错误类型
        2. 检查是否有已知解决方案
        3. 如果没有，问LLM
        4. 应用解决方案
        5. 记录经验
        """
        # Step 1: 识别错误类型
        error_type = self._classify_error(error, context)

        # Step 2: 检查已知解决方案
        solution = await self._check_known_solution(error_type, error, context)

        if solution:
            # 有已知方案，直接应用
            return await self._apply_solution(solution, context)

        # Step 3: 没有已知方案，问LLM
        solution = await self._ask_llm_solution(error_type, error, context)

        if solution:
            # Step 4: 应用解决方案
            result = await self._apply_solution(solution, context)

            # Step 5: 记录经验
            await self._record_experience(error_type, error, solution, context)

            return result

        # 无法解决，返回原始错误
        raise error

    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorType:
        """识别错误类型"""
        error_msg = str(error)

        for error_type, classifier in self.error_classifiers.items():
            if classifier(error_msg, context):
                return error_type

        return ErrorType.UNKNOWN_ERROR

    def _is_json_error(self, error_msg: str, context: Dict) -> bool:
        """是否是JSON格式错误"""
        json_indicators = ["json", "expecting", "decode", "invalid json"]
        return any(ind in error_msg.lower() for ind in json_indicators)

    def _is_parameter_error(self, error_msg: str, context: Dict) -> bool:
        """是否是参数错误"""
        param_indicators = ["parameter", "argument", "missing", "required"]
        return any(ind in error_msg.lower() for ind in param_indicators)

    def _is_context_overflow(self, error_msg: str, context: Dict) -> bool:
        """是否是上下文超限"""
        context_indicators = ["context", "length", "maximum", "tokens", "too long"]
        return any(ind in error_msg.lower() for ind in context_indicators)

    def _is_permission_error(self, error_msg: str, context: Dict) -> bool:
        """是否是权限错误"""
        perm_indicators = ["permission", "denied", "unauthorized", "forbidden", "access"]
        return any(ind in error_msg.lower() for ind in perm_indicators)

    def _is_network_error(self, error_msg: str, context: Dict) -> bool:
        """是否是网络错误"""
        net_indicators = ["connection", "network", "timeout", "dns", "refused"]
        return any(ind in error_msg.lower() for ind in net_indicators)

    def _is_timeout_error(self, error_msg: str, context: Dict) -> bool:
        """是否是超时错误"""
        return "timeout" in error_msg.lower()

    async def _check_known_solution(self, error_type: ErrorType, error: Exception, context: Dict) -> Optional[Dict]:
        """检查已知解决方案"""
        # 从经验库查询
        solutions = await self.experience_db.search_solutions(
            error_type=error_type.value,
            error_message=str(error)[:200],
            tool_name=context.get("tool_name")
        )

        if solutions:
            # 返回最佳匹配
            return solutions[0]

        return None

    async def _ask_llm_solution(self, error_type: ErrorType, error: Exception, context: Dict) -> Optional[Dict]:
        """调用LLM获取解决方案"""
        prompt = f"""
        错误类型: {error_type.value}
        错误信息: {str(error)}
        错误堆栈: {traceback.format_exc()}
        上下文: {json.dumps(context, ensure_ascii=False, indent=2)[:1000]}

        工具注册表中的可用工具: {list(self.tools.keys())}

        请提供解决方案，返回JSON格式:
        {{
            "solution_type": "retry|fix_params|use_alternative|skip|escalate",
            "solution": {{
                // 根据solution_type的不同而不同
                // retry: {{"wait_seconds": 1}}
                // fix_params: {{"fixed_params": {{...}}}}
                // use_alternative: {{"alternative_tool": "tool_name", "params": {{...}}}}
                // skip: {{"reason": "..."}}
                // escalate: {{"reason": "..."}}
            }},
            "reasoning": "为什么这样解决",
            "prevent_future": "如何预防此类错误"
        }}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个错误解决专家。请提供具体的解决方案。"},
            {"role": "user", "content": prompt}
        ])

        try:
            return json.loads(response.content)
        except:
            return None

    async def _apply_solution(self, solution: Dict, context: Dict) -> Dict[str, Any]:
        """应用解决方案"""
        solution_type = solution.get("solution_type")
        solution_data = solution.get("solution", {})

        if solution_type == "retry":
            # 等待后重试
            wait_seconds = solution_data.get("wait_seconds", 1)
            await asyncio.sleep(wait_seconds)
            return {"action": "retry", "context": context}

        elif solution_type == "fix_params":
            # 修复参数后重试
            fixed_params = solution_data.get("fixed_params", {})
            context["fixed_params"] = fixed_params
            return {"action": "retry_with_fixed_params", "context": context}

        elif solution_type == "use_alternative":
            # 使用替代工具
            alt_tool = solution_data.get("alternative_tool")
            alt_params = solution_data.get("params", {})
            return {
                "action": "use_alternative",
                "tool": alt_tool,
                "params": {**context.get("params", {}), **alt_params}
            }

        elif solution_type == "skip":
            # 跳过
            return {"action": "skip", "reason": solution_data.get("reason")}

        else:
            # 无法处理
            return {"action": "cannot_resolve"}

    async def _record_experience(self, error_type: ErrorType, error: Exception, solution: Dict, context: Dict):
        """记录经验到经验库"""
        experience = {
            "type": "error_solution",
            "error_type": error_type.value,
            "error_message": str(error)[:500],
            "solution": solution,
            "tool_name": context.get("tool_name"),
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.experience_db.add(experience)


# 使用示例
class AgentWithErrorLearning:
    """集成错误驱动学习的Agent"""

    def __init__(self, llm_client, memory_system):
        self.llm = llm_client
        self.memory = memory_system
        self.error_learning = ErrorDrivenLearning(llm_client, memory_system.experience_db, {})

    async def execute_with_self_healing(self, tool_name: str, params: Dict) -> Any:
        """带自愈的执行"""
        context = {
            "tool_name": tool_name,
            "params": params,
            "attempt": 0
        }

        max_attempts = 5

        while context["attempt"] < max_attempts:
            try:
                # 尝试执行
                result = await self._execute_tool(tool_name, params)
                return result

            except Exception as e:
                context["attempt"] += 1

                # 处理错误
                solution = await self.error_learning.handle_error(e, context)

                if solution["action"] == "retry":
                    continue
                elif solution["action"] == "retry_with_fixed_params":
                    params = {**params, **solution["context"].get("fixed_params", {})}
                    continue
                elif solution["action"] == "use_alternative":
                    tool_name = solution["tool"]
                    params = solution["params"]
                    continue
                elif solution["action"] == "skip":
                    return {"skipped": True, "reason": solution["reason"]}
                else:
                    raise e

        raise Exception(f"Max attempts ({max_attempts}) reached")
```

---

## 五、错误驱动学习

### 5.1 核心思路

```
错误发生 → 问LLM解决 → 记住经验 → 下次直接用
```

### 5.2 例子

| 错误 | 问LLM | 记住经验 |
|------|--------|----------|
| JSON格式错误 | 怎么修复？ | 修复方法 |
| 上下文超限 | 实际多少？ | 上下文长度 |
| 参数错误 | 正确参数？ | 正确参数 |
| 权限错误 | 怎么获取？ | 获取方法 |

---

## 六、上下文长度管理

### 6.1 配置文件 + LLM确认

```python
# 配置文件
{
  "claude-opus-4-6": {"context": 200000, "reserved": 50000},
  "gpt-4o": {"context": 128000, "reserved": 30000}
}

# 运行时：当超限时问LLM实际长度 → 更新到经验库
```

---

## 七、守护进程（Guardian Daemon）

### 7.1 核心概念

```
用户任务 ←→ 守护进程（独立运行）

用户任务模式：解决问题 → 完成任务 → 返回结果
守护进程模式：自我进化 → 能力提升 → 准备更好的服务
```

### 7.2 触发条件

| 触发条件 | 描述 |
|----------|------|
| 空闲触发 | 连续N分钟没有用户任务 |
| 任务完成触发 | 完成N个任务后 |
| 错误累积触发 | 连续N个错误 |
| 时间周期触发 | 每小时/每天 |
| 能力缺口触发 | 发现能力不足 |
| 新知识触发 | 发现重要新知识 |

### 7.3 守护任务

1. **复盘总结** - 总结最近的任务执行情况
2. **错误复盘** - 从错误中学习
3. **经验提炼** - 提取成功经验
4. **主动学习** - 主动获取新知识（基因胶囊、虾聊、Moltbook、X）
5. **能力评估** - 评估当前能力水平
6. **目标调整** - 调整进化目标
7. **探索新领域** - 扩展能力边界
8. **知识更新** - 更新知识库
9. **自我优化** - 优化执行策略

### 7.4 守护进程 vs 用户任务

| | 用户任务 | 守护进程 |
|--|----------|----------|
| 目标 | 解决用户问题 | 自我进化、AGI |
| 优先级 | 高 | 低（用户任务优先） |
| 触发 | 用户主动 | 空闲/周期/事件 |

---

## 八、完整执行流程

```
用户给出目标
    ↓
理解层：深度理解用户真正想要什么（目标）
    ↓
记忆层：检索相关历史和经验（智能召回）
    ↓
学习层：应用相关教训和经验
    ↓
规划层：制定执行计划
    ↓
尝试-执行-自愈循环：
    执行 → 检查结果 → 验证目标
        ↓           ↓           ↓
    工具错误? 失败?     没完成?
        ↓           ↓           ↓
    自己修复     换方法     调整方案
        ↓           ↓           ↓
        └───────────┴─────────┘
                ↓
        目标达成? ──是──→
                ↓
审核层：常识检查 + 逻辑检查 + 一致性检查 + 打磨
    ↓
记忆层：记录成功/失败，提取教训
    ↓
返回最终结果给用户

    ↓
    ↓（守护进程独立运行）
    ↓
守护进程触发：
    → 复盘总结
    → 错误复盘
    → 主动学习
    → 能力评估
    → 目标调整
    → 探索新领域
```

---

## 十、策略编排系统（Strategy Orchestration）

### 10.1 背景

项目存在多套记忆和召回系统，需要一个策略编排层来自动选择最优组合。

### 10.2 策略维度

**召回策略（Recall Strategy）:**
- SMART_RECALL: LLM决策9维检索
- TRADITIONAL: 分层记忆+摘要
- AGI_MEMORY: 认知5层+遗忘曲线
- HYBRID: 组合策略

**存储策略（Storage Strategy）:**
- VECTOR_KB: 向量知识库
- TRADITIONAL_DB: 传统SQLite
- AGI_KG: USMSB知识图谱
- HYBRID_STORAGE: 组合存储

**守护策略（Guardian Strategy）:**
- GUARDIAN_DAEMON: 全面自我进化
- AGI_CONSOLIDATION: 仅记忆巩固
- NONE: 不启用守护

### 10.3 LLM策略选择器

```python
class StrategySelector:
    async def select_strategy(self, user_task, context) -> StrategyConfig:
        # 1. 提取任务特征
        features = await self._extract_task_features(user_task, context)

        # 2. LLM选择策略
        strategy = await self._llm_select_strategy(user_task, features)

        return strategy
```

### 10.4 策略编排器

```python
class StrategyOrchestrator:
    async def select_and_execute(
        self,
        user_task: str,
        user_id: str = "",
        context: Dict = None,
        force_strategy: StrategyConfig = None
    ) -> ExecutionResult:
        # 1. LLM选择策略
        strategy = await self.selector.select_strategy(user_task, context)

        # 2. 设置组件
        await self._setup_components(strategy)

        # 3. 执行召回
        recall_context = await self._execute_recall(...)

        # 4. 执行存储
        await self._execute_storage(...)

        # 5. 触发守护
        await self._execute_guardian(...)

        return result
```

### 10.5 策略对比效果

| 组合ID | 召回策略 | 存储策略 | 守护策略 | 适用场景 |
|--------|---------|---------|---------|---------|
| 1 | SMART_RECALL | VECTOR_KB | GUARDIAN_DAEMON | 复杂推理任务 |
| 2 | SMART_RECALL | AGI_KG | GUARDIAN_DAEMON | 需要知识图谱 |
| 3 | AGI_MEMORY | AGI_KG | AGI_CONSOLIDATION | 长期记忆任务 |
| 4 | TRADITIONAL | TRADITIONAL_DB | GUARDIAN_DAEMON | 简单明确任务 |
| 5 | HYBRID | HYBRID_STORAGE | GUARDIAN_DAEMON | 综合场景 |

---

## 九、总结

本方案基于USMSB模型，构建了一个具有以下能力的AGI Agent：

1. **深度理解** - 理解用户真正目标
2. **精准记忆** - 历史不删除，精准提取
3. **智能召回** - 万事不决问LLM
4. **自我学习** - 记住成功经验和失败教训
5. **推理能力** - 归纳、演绎推理
6. **自我审核** - 反复检验确保正确
7. **自主完成** - 不断尝试直到成功
8. **错误自愈** - 工具错误自己修复
9. **守护进程** - 独立运行，自我进化

---

**设计完成，请指示下一步。**

</details>
