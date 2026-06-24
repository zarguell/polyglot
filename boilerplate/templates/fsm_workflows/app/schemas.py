"""FSM Workflow schemas."""

from __future__ import annotations

from pydantic import BaseModel


class WorkflowCreate(BaseModel):
    """Request to create a new workflow definition."""

    name: str
    states: list[str] = []
    transitions: list[str] = []


class TransitionRequest(BaseModel):
    """Request to trigger a state transition on a workflow instance."""

    trigger: str
    context: dict | None = None
