"""FSM Workflow API routes — CRUD for workflows and transition execution."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser
from app.components.fsm_workflows.models import WorkflowDefinition, WorkflowInstance
from app.components.fsm_workflows.schemas import TransitionRequest, WorkflowCreate
from app.components.fsm_workflows.service import WorkflowEngine
from app.core.db import async_session_factory

logger = structlog.get_logger()

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

_engine: WorkflowEngine | None = None


def _get_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine


@router.post("")
async def create_workflow(payload: WorkflowCreate, current_user: CurrentUser) -> dict:
    """Create a new workflow definition."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.name == payload.name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Workflow with this name already exists")

        definition = WorkflowDefinition(
            id=uuid.uuid4(),
            name=payload.name,
            states=payload.states,
            transitions=payload.transitions,
        )
        db.add(definition)
        await db.commit()

    logger.info("workflow_definition_created", name=payload.name)
    return {"status": "ok", "id": str(definition.id)}


@router.get("")
async def list_workflows(current_user: CurrentUser) -> list[dict]:
    """List all workflow definitions."""
    async with async_session_factory() as db:
        result = await db.execute(select(WorkflowDefinition).order_by(WorkflowDefinition.name))
        definitions = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "name": d.name,
            "states": d.states or [],
            "transitions": d.transitions or [],
        }
        for d in definitions
    ]


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, current_user: CurrentUser) -> dict:
    """Get a single workflow definition by ID."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == uuid.UUID(workflow_id))
        )
        definition = result.scalar_one_or_none()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "id": str(definition.id),
        "name": definition.name,
        "states": definition.states or [],
        "transitions": definition.transitions or [],
    }


@router.post("/{workflow_id}/transition")
async def execute_transition(
    workflow_id: str, payload: TransitionRequest, current_user: CurrentUser
) -> dict:
    """Trigger a transition on a workflow instance.

    Creates or advances a workflow instance for the given entity.
    """
    async with async_session_factory() as db:
        result = await db.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.id == uuid.UUID(workflow_id))
        )
        definition = result.scalar_one_or_none()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

    engine = _get_engine()
    states = definition.states or []
    transitions_data = definition.transitions or []

    engine.register_definition(definition.name, states, transitions_data)

    new_state = engine.transition(
        definition.name,
        payload.trigger,
        payload.context.get("current_state", states[0]) if payload.context else states[0],
    )

    if new_state is None:
        raise HTTPException(status_code=400, detail="Invalid transition")

    async with async_session_factory() as db:
        instance = WorkflowInstance(
            id=uuid.uuid4(),
            definition_id=definition.id,
            entity_type=payload.context.get("entity_type", "generic")
            if payload.context
            else "generic",
            entity_id=payload.context.get("entity_id", str(uuid.uuid4()))
            if payload.context
            else str(uuid.uuid4()),
            state=new_state,
        )
        db.add(instance)
        await db.commit()

    from app.components.fsm_workflows.tasks import execute_workflow_action

    execute_workflow_action.defer(
        workflow_name=definition.name,
        trigger=payload.trigger,
        from_state=states[0],
        to_state=new_state,
        entity_id=str(instance.entity_id),
        entity_type=instance.entity_type,
    )

    logger.info(
        "workflow_transition_completed",
        workflow=definition.name,
        trigger=payload.trigger,
        new_state=new_state,
    )
    return {"status": "ok", "state": new_state}
