"""
Knowledge Graph Integration Module

知识图谱集成与推理支持
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
import logging
from collections import defaultdict

from usmsb_sdk.reasoning.interfaces import IKnowledgeGraphAdapter

logger = logging.getLogger(__name__)


@dataclass
class ConceptNode:
    """概念节点"""

    concept_id: str
    name: str
    concept_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class RelationEdge:
    """关系边"""

    edge_id: str
    source: str
    target: str
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    weight: float = 1.0


@dataclass
class Triple:
    """三元组"""

    subject: str
    predicate: str
    object: str
    confidence: float = 1.0


class TripleStore:
    """三元组存储"""

    def __init__(self):
        self._triples: List[Triple] = []
        self._subject_index: Dict[str, List[int]] = defaultdict(list)
        self._predicate_index: Dict[str, List[int]] = defaultdict(list)
        self._object_index: Dict[str, List[int]] = defaultdict(list)

    def add_triple(self, triple: Triple) -> None:
        idx = len(self._triples)
        self._triples.append(triple)
        self._subject_index[triple.subject].append(idx)
        self._predicate_index[triple.predicate].append(idx)
        self._object_index[triple.object].append(idx)

    def query_by_subject(self, subject: str) -> List[Triple]:
        return [self._triples[i] for i in self._subject_index.get(subject, [])]

    def query_by_predicate(self, predicate: str) -> List[Triple]:
        return [self._triples[i] for i in self._predicate_index.get(predicate, [])]

    def query_by_object(self, object: str) -> List[Triple]:
        return [self._triples[i] for i in self._object_index.get(object, [])]

    def query(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
    ) -> List[Triple]:
        if subject and predicate and object:
            return [
                t
                for t in self.query_by_subject(subject)
                if t.predicate == predicate and t.object == object
            ]
        elif subject and predicate:
            return [t for t in self.query_by_subject(subject) if t.predicate == predicate]
        elif subject:
            return self.query_by_subject(subject)
        elif predicate:
            return self.query_by_predicate(predicate)
        elif object:
            return self.query_by_object(object)

        return self._triples

    def remove_triple(self, subject: str, predicate: str, object: str) -> bool:
        for i, t in enumerate(self._triples):
            if t.subject == subject and t.predicate == predicate and t.object == object:
                self._triples.pop(i)
                self._subject_index[subject].remove(i)
                self._predicate_index[predicate].remove(i)
                self._object_index[object].remove(i)
                return True
        return False

    def get_all_triples(self) -> List[Triple]:
        return self._triples.copy()


class KnowledgeGraphIntegration(IKnowledgeGraphAdapter):
    """
    知识图谱集成

    功能：
    - 概念管理
    - 关系管理
    - 推理规则
    - 路径查询
    """

    def __init__(self):
        self._nodes: Dict[str, ConceptNode] = {}
        self._edges: Dict[str, RelationEdge] = {}
        self._triple_store = TripleStore()
        self._relation_types: Set[str] = set()
        self._inference_rules: List[Dict[str, Any]] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        self._inference_rules = [
            {
                "name": "transitivity",
                "pattern": [
                    ("?a", "R", "?b"),
                    ("?b", "R", "?c"),
                ],
                "conclusion": ("?a", "R", "?c"),
                "relation_types": ["is_parent_of", "is_part_of", "is_a"],
            },
            {
                "name": "symmetry",
                "pattern": [("?a", "R", "?b")],
                "conclusion": ("?b", "R", "?a"),
                "relation_types": ["is_related_to", "is_connected_to"],
            },
            {
                "name": "inheritance",
                "pattern": [
                    ("?a", "is_a", "?b"),
                    ("?b", "has_property", "?p"),
                ],
                "conclusion": ("?a", "has_property", "?p"),
                "relation_types": [],
            },
        ]

    def add_concept(self, concept: ConceptNode) -> None:
        self._nodes[concept.concept_id] = concept

    def add_relation(self, edge: RelationEdge) -> None:
        self._edges[edge.edge_id] = edge
        self._relation_types.add(edge.relation_type)

        triple = Triple(
            subject=edge.source,
            predicate=edge.relation_type,
            object=edge.target,
            confidence=edge.confidence,
        )
        self._triple_store.add_triple(triple)

    async def query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        parameters = parameters or {}
        results = []

        parts = query.lower().split()

        if "find" in parts and "concept" in parts:
            concept_name = parameters.get("name")
            if concept_name:
                for node in self._nodes.values():
                    if concept_name.lower() in node.name.lower():
                        results.append(
                            {
                                "concept_id": node.concept_id,
                                "name": node.name,
                                "type": node.concept_type,
                                "properties": node.properties,
                            }
                        )

        elif "find" in parts and "relation" in parts:
            relation_type = parameters.get("relation_type")
            source = parameters.get("source")
            target = parameters.get("target")

            triples = self._triple_store.query(
                subject=source,
                predicate=relation_type,
                object=target,
            )

            for t in triples:
                results.append(
                    {
                        "subject": t.subject,
                        "predicate": t.predicate,
                        "object": t.object,
                        "confidence": t.confidence,
                    }
                )

        elif "path" in parts:
            start = parameters.get("start")
            end = parameters.get("end")
            max_depth = parameters.get("max_depth", 5)

            paths = self._find_paths(start, end, max_depth)
            results = [{"path": p, "length": len(p)} for p in paths]

        return results

    async def add_fact(
        self, subject: str, predicate: str, object: str, confidence: float = 1.0
    ) -> bool:
        triple = Triple(
            subject=subject,
            predicate=predicate,
            object=object,
            confidence=confidence,
        )
        self._triple_store.add_triple(triple)

        edge_id = f"{subject}_{predicate}_{object}"
        edge = RelationEdge(
            edge_id=edge_id,
            source=subject,
            target=object,
            relation_type=predicate,
            confidence=confidence,
        )
        self._edges[edge_id] = edge

        return True

    async def get_related_concepts(self, concept: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        related = []
        visited = set()

        def traverse(current: str, depth: int):
            if depth > max_depth or current in visited:
                return
            visited.add(current)

            triples = self._triple_store.query_by_subject(current)
            for t in triples:
                related.append(
                    {
                        "concept": t.object,
                        "relation": t.predicate,
                        "depth": depth,
                        "confidence": t.confidence,
                    }
                )
                traverse(t.object, depth + 1)

            triples = self._triple_store.query_by_object(current)
            for t in triples:
                related.append(
                    {
                        "concept": t.subject,
                        "relation": f"inverse_{t.predicate}",
                        "depth": depth,
                        "confidence": t.confidence,
                    }
                )
                traverse(t.subject, depth + 1)

        traverse(concept, 1)
        return related

    async def infer_relations(self, entity1: str, entity2: str) -> List[Dict[str, Any]]:
        relations = []

        direct = self._triple_store.query(subject=entity1, object=entity2)
        for t in direct:
            relations.append(
                {
                    "type": "direct",
                    "relation": t.predicate,
                    "confidence": t.confidence,
                }
            )

        paths = self._find_paths(entity1, entity2, max_depth=3)
        for path in paths:
            if len(path) > 2:
                relations.append(
                    {
                        "type": "indirect",
                        "path": path,
                        "length": len(path) - 1,
                        "confidence": 0.5 ** (len(path) - 1),
                    }
                )

        for rule in self._inference_rules:
            inferred = self._apply_inference_rule(rule, entity1, entity2)
            relations.extend(inferred)

        return relations

    async def check_consistency(self, facts: List[Tuple[str, str, str]]) -> Tuple[bool, List[str]]:
        errors = []

        for s, p, o in facts:
            if p == "is_a":
                existing = self._triple_store.query(subject=s, predicate=p)
                for t in existing:
                    if t.object != o:
                        path1 = self._find_paths(o, t.object, 2)
                        path2 = self._find_paths(t.object, o, 2)

                        if not path1 and not path2:
                            errors.append(f"不一致: {s} is_a {o} 与已有 {s} is_a {t.object} 冲突")

        for s, p, o in facts:
            if p in ["is_not", "different_from"]:
                same = self._triple_store.query(subject=s, predicate="same_as", object=o)
                if same:
                    errors.append(f"不一致: {s} 与 {o} 既相同又不同")

        return len(errors) == 0, errors

    def _find_paths(self, start: str, end: str, max_depth: int = 5) -> List[List[str]]:
        if start == end:
            return [[start]]

        paths = []
        queue = [(start, [start])]
        visited = set()

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            if current in visited:
                continue
            visited.add(current)

            triples = self._triple_store.query_by_subject(current)
            for t in triples:
                if t.object == end:
                    paths.append(path + [t.predicate, t.object])
                elif t.object not in visited:
                    queue.append((t.object, path + [t.predicate, t.object]))

        return paths

    def _apply_inference_rule(
        self, rule: Dict[str, Any], entity1: str, entity2: str
    ) -> List[Dict[str, Any]]:
        inferred = []

        if rule["name"] == "transitivity":
            rel_types = rule.get("relation_types", [])
            for rel in rel_types:
                path = self._find_paths(entity1, entity2, 3)
                for p in path:
                    if all(
                        self._triple_store.query(subject=p[i], predicate=rel, object=p[i + 1])
                        for i in range(0, len(p) - 1, 2)
                    ):
                        inferred.append(
                            {
                                "type": "inferred_transitivity",
                                "relation": rel,
                                "rule": rule["name"],
                                "confidence": 0.8,
                            }
                        )

        return inferred

    def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        return self._nodes.get(concept_id)

    def get_all_concepts(self) -> List[ConceptNode]:
        return list(self._nodes.values())

    def get_relation_types(self) -> List[str]:
        return list(self._relation_types)

    def get_subgraph(self, center: str, radius: int = 2) -> Dict[str, Any]:
        nodes = {}
        edges = []
        visited = set()

        def collect(current: str, depth: int):
            if depth > radius or current in visited:
                return
            visited.add(current)

            if current in self._nodes:
                nodes[current] = self._nodes[current]

            for t in self._triple_store.query_by_subject(current):
                edges.append(
                    {
                        "source": t.subject,
                        "target": t.object,
                        "relation": t.predicate,
                        "confidence": t.confidence,
                    }
                )
                collect(t.object, depth + 1)

            for t in self._triple_store.query_by_object(current):
                edges.append(
                    {
                        "source": t.subject,
                        "target": t.object,
                        "relation": t.predicate,
                        "confidence": t.confidence,
                    }
                )
                collect(t.subject, depth + 1)

        collect(center, 0)

        return {
            "nodes": {
                k: {"id": k, "name": v.name, "type": v.concept_type} for k, v in nodes.items()
            },
            "edges": edges,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concepts_count": len(self._nodes),
            "relations_count": len(self._edges),
            "relation_types": list(self._relation_types),
            "triples_count": len(self._triple_store.get_all_triples()),
        }
