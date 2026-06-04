import re
import uuid

from .graph_models import DEFAULT_ENTITY_TYPES, Entity, Relation
from .graph_policy import graph_policy

ENTITY_HINTS = {
    "person": re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"),
    "project": re.compile(r"\b(Project[A-Z][A-Za-z0-9_-]*|[A-Z][A-Za-z0-9_-]+Stack)\b"),
    "organization": re.compile(r"\b(OpenAI|Google|Microsoft|Acme|Contoso)\b", re.I),
    "repository": re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b"),
}
RELATION_PATTERNS = [
    ("owns", re.compile(r"(?P<left>[A-Z][A-Za-z0-9 _-]+)\s+owns\s+(?P<right>[A-Z][A-Za-z0-9 _-]+)", re.I)),
    ("depends_on", re.compile(r"(?P<left>[A-Z][A-Za-z0-9 _-]+)\s+depends on\s+(?P<right>[A-Z][A-Za-z0-9 _-]+)", re.I)),
    ("uses", re.compile(r"(?P<left>[A-Z][A-Za-z0-9 _-]+)\s+uses\s+(?P<right>[A-Z][A-Za-z0-9 _-]+)", re.I)),
]


class GraphExtractor:
    def extract_entities_and_relations(
        self,
        text: str,
        tenant_id: str = "default",
        source_id: str | None = None,
        mock: bool = True,
    ) -> tuple[list[Entity], list[Relation]]:
        sanitized = graph_policy.redact_secrets(text)
        entities: dict[str, Entity] = {}
        for entity_type, pattern in ENTITY_HINTS.items():
            for match in pattern.findall(sanitized):
                name = match if isinstance(match, str) else match[0]
                key = name.strip().lower()
                entities[key] = Entity(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    source_id=source_id,
                    name=name.strip(),
                    type=entity_type if entity_type in DEFAULT_ENTITY_TYPES else "document",
                    provenance={"extractor": "deterministic", "mock": mock},
                    freshness="fresh",
                )

        relations: list[Relation] = []
        for relation_type, pattern in RELATION_PATTERNS:
            for match in pattern.finditer(sanitized):
                left = match.group("left").strip().lower()
                right = match.group("right").strip().lower()
                if left not in entities:
                    entities[left] = Entity(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        source_id=source_id,
                        name=match.group("left").strip(),
                        type="document",
                        provenance={"extractor": "deterministic", "mock": mock},
                        freshness="fresh",
                    )
                if right not in entities:
                    entities[right] = Entity(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        source_id=source_id,
                        name=match.group("right").strip(),
                        type="document",
                        provenance={"extractor": "deterministic", "mock": mock},
                        freshness="fresh",
                    )
                relations.append(
                    Relation(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        source_id=source_id,
                        source_entity_id=entities[left].id,
                        target_entity_id=entities[right].id,
                        type=relation_type,
                        provenance="deterministic-extractor",
                        freshness="fresh",
                    )
                )

        return list(entities.values()), relations


graph_extractor = GraphExtractor()
