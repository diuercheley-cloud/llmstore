# Owner: agent-platform
from pydantic import BaseModel, Field


class FlowNodeSchema(BaseModel):
    id: str
    node_type: str
    label: str | None = None
    config: dict = Field(default_factory=dict)


class FlowEdgeSchema(BaseModel):
    source: str
    target: str


class FlowSchema(BaseModel):
    nodes: list[FlowNodeSchema] = Field(default_factory=list)
    edges: list[FlowEdgeSchema] = Field(default_factory=list)
