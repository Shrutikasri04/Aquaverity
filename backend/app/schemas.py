"""
Canonical data models for the ORCA-X agentic flow.

These mirror docs/agent-contract.md exactly. If you change a field here,
update that doc in the same commit.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Intent = Literal["safety_advisory", "fishing_suitability", "route_advice"]
DecisionLabel = Literal["SAFE", "CAUTION", "AVOID"]
AgentName = Literal["ocean", "weather", "geospatial"]
AgentStatus = Literal["success", "partial", "error"]


class Location(BaseModel):
    name: str
    lat: float
    lon: float
    radius_km: Optional[float] = None


class TimeWindow(BaseModel):
    start: datetime
    end: datetime


class SessionState(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_location: Optional[Location] = None
    last_time_window: Optional[TimeWindow] = None
    last_intent: Optional[Intent] = None
    language: str = "en"


class UserQuery(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    text: str
    language: str = "en"
    context: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    agent: AgentName
    operation: str
    params: dict[str, Any]


class Plan(BaseModel):
    plan_id: str
    session_id: str
    intent: Intent
    location: Location
    time_window: TimeWindow
    required_agents: list[AgentName]
    tasks: list[Task]


class Evidence(BaseModel):
    source: str
    retrieved_at: datetime
    url: Optional[str] = None


class AgentResponse(BaseModel):
    agent: AgentName
    task_id: str
    status: AgentStatus
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = 0.0
    limitations: list[str] = Field(default_factory=list)


class DecisionFactor(BaseModel):
    name: str
    value: str
    impact: Literal["favourable", "neutral", "moderate", "severe"]
    source: AgentName


class Decision(BaseModel):
    type: Intent
    label: DecisionLabel
    summary: str
    factors: list[DecisionFactor]
    suitability_score: Optional[float] = None
    recommended_actions: list[str]
    confidence: float
    limitations: list[str]


class FinalDecision(BaseModel):
    session_id: str
    plan_id: str
    decision: Decision
    evidence_trail: list[dict[str, Any]]
