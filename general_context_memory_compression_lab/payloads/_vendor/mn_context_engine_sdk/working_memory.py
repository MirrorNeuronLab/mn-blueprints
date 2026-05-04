from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone
import uuid
import json

def utcnow():
    return datetime.now(timezone.utc)

VALID_TYPES = {"Fact", "Hypothesis", "Task", "Decision", "Evidence", "Constraint"}
VALID_STATUSES = {
    "draft",
    "validated",
    "used",
    "archived",
    "hypothesis",
    "tested",
    "confirmed",
    "rejected",
}

GENERIC_TRANSITIONS = {
    "draft": {"validated", "archived"},
    "validated": {"used", "archived"},
    "used": {"archived"},
    "archived": set(),
}

HYPOTHESIS_TRANSITIONS = {
    "draft": {"tested", "archived"},
    "hypothesis": {"tested", "archived"},
    "tested": {"confirmed", "rejected", "archived"},
    "confirmed": {"archived"},
    "rejected": {"archived"},
    "archived": set(),
}

class MNMemoryItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    content: Any
    status: str
    confidence: float = 1.0
    source: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    expires_at: Optional[datetime] = None
    version: int = 1

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in VALID_TYPES:
            raise ValueError(f"invalid memory type: {value}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError(f"invalid memory status: {value}")
        return value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source must not be empty")
        return value

    @model_validator(mode="after")
    def validate_content(self) -> "MNMemoryItem":
        if not isinstance(self.content, dict):
            raise ValueError("content must be a structured object")
        return self

class MNMemoryEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str

    @field_validator("relation")
    @classmethod
    def validate_relation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("relation must not be empty")
        return value

class MNWorkingMemory:
    def __init__(self):
        self._items: Dict[str, MNMemoryItem] = {}
        self._edges: List[MNMemoryEdge] = []

    def add(self, item: MNMemoryItem) -> None:
        self._items[item.id] = item

    def update(self, item_id: str, updates: dict) -> None:
        if item_id in self._items:
            item = self._items[item_id]
            updates = dict(updates)
            expected_version = updates.pop("expected_version", None)
            if expected_version is not None and expected_version != item.version:
                raise ValueError(f"version conflict: item has {item.version}, expected {expected_version}")

            if "status" in updates:
                self._validate_transition(item.type, item.status, updates["status"])

            for key, value in updates.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            item.updated_at = utcnow()
            item.version += 1

    def get(self, item_id: str) -> Optional[MNMemoryItem]:
        item = self._items.get(item_id)
        if item is None or self._is_expired(item):
            return None
        return item

    def query(self, filters: dict) -> List[MNMemoryItem]:
        results = []
        for item in self._items.values():
            if self._is_expired(item):
                continue
            match = True
            for key, value in filters.items():
                if getattr(item, key, None) != value:
                    match = False
                    break
            if match:
                results.append(item)
        return results

    def link(self, source_id: str, target_id: str, relation: str) -> None:
        if source_id not in self._items:
            raise KeyError(f"source item not found: {source_id}")
        if target_id not in self._items:
            raise KeyError(f"target item not found: {target_id}")
        edge = MNMemoryEdge(source_id=source_id, target_id=target_id, relation=relation)
        self._edges.append(edge)

    def invalidate(self, item_id: str) -> None:
        if item_id in self._items:
            self._validate_transition(self._items[item_id].type, self._items[item_id].status, "archived")
            self._items[item_id].status = "archived"
            self._items[item_id].updated_at = utcnow()
            self._items[item_id].version += 1

    def get_context(self, agent_role: str, goal_id: str) -> List[MNMemoryItem]:
        """
        Retrieves selective context for an agent around a goal.
        Items must be visible to the role and either match the goal directly
        or sit within two graph hops of a matching item.
        """
        seeds = {
            item.id
            for item in self._items.values()
            if not self._is_expired(item)
            and item.status != "archived"
            and (item.id == goal_id or item.content.get("goal_id") == goal_id)
        }
        reachable = self._expand_graph(seeds, max_depth=2)

        return [
            item
            for item in self._items.values()
            if item.id in reachable
            and item.status != "archived"
            and not self._is_expired(item)
            and self._is_visible_to_role(agent_role, item)
        ]

    @staticmethod
    def _is_expired(item: MNMemoryItem) -> bool:
        return item.expires_at is not None and utcnow() > item.expires_at

    @staticmethod
    def _validate_transition(item_type: str, current: str, new_status: str) -> None:
        if current == new_status:
            return
        transitions = HYPOTHESIS_TRANSITIONS if item_type == "Hypothesis" else GENERIC_TRANSITIONS
        if new_status not in transitions.get(current, set()):
            raise ValueError(f"invalid status transition for {item_type}: {current} -> {new_status}")

    @staticmethod
    def _is_visible_to_role(agent_role: str, item: MNMemoryItem) -> bool:
        acl = item.content.get("acl")
        if isinstance(acl, dict):
            deny_roles = acl.get("deny_roles", [])
            if agent_role in deny_roles:
                return False
            allow_roles = acl.get("allow_roles")
            if allow_roles is not None:
                return agent_role in allow_roles

        if agent_role == "planner":
            return item.type != "Evidence"
        if agent_role == "executor":
            return item.type != "Hypothesis"
        if agent_role == "reviewer":
            return True
        return item.source == agent_role

    def _expand_graph(self, seed_ids: set[str], max_depth: int) -> set[str]:
        reachable = set(seed_ids)
        frontier = set(seed_ids)
        for _ in range(max_depth):
            next_frontier = set()
            for edge in self._edges:
                if edge.source_id in frontier and edge.target_id not in reachable:
                    next_frontier.add(edge.target_id)
                if edge.target_id in frontier and edge.source_id not in reachable:
                    next_frontier.add(edge.source_id)
            if not next_frontier:
                break
            reachable.update(next_frontier)
            frontier = next_frontier
        return reachable

    # --- Methods for compatibility with MicroNeuron payloads (Serialization) ---
    def to_dict(self) -> dict:
        return {
            "items": [item.model_dump(mode="json") for item in self._items.values()],
            "edges": [edge.model_dump(mode="json") for edge in self._edges]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MNWorkingMemory":
        wm = cls()
        for item_data in data.get("items", []):
            item = MNMemoryItem.model_validate(item_data)
            wm.add(item)
        for edge_data in data.get("edges", []):
            edge = MNMemoryEdge.model_validate(edge_data)
            wm._edges.append(edge)
        return wm

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "MNWorkingMemory":
        return cls.from_dict(json.loads(json_str))


# Backward-compatible aliases for older SDK users.
MemoryItem = MNMemoryItem
MemoryEdge = MNMemoryEdge
WorkingMemory = MNWorkingMemory
