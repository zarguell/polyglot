# FSM Workflows Component — Activation Guide

## What This Component Adds

- `POST /api/workflows` — create a new workflow definition
- `GET /api/workflows` — list all workflow definitions
- `GET /api/workflows/{id}` — get a single workflow definition
- `POST /api/workflows/{id}/transition` — trigger a state transition on a workflow instance
- `WorkflowEngine` — wraps the `transitions` library for state machine execution
- `WorkflowDefinition` model — reusable state machine template (name, states JSONB, transitions JSONB)
- `WorkflowInstance` model — active workflow tracking an entity through states
- `execute_workflow_action` Procrastinate task — async side effects on transition

## Prerequisites

Install additional dependencies:

```bash
uv add transitions
```

## Environment Variables

None required. The FSM engine runs entirely in-process.

## Migration

This component adds tables: `workflow_definitions`, `workflow_instances`.
After activation:

```bash
make new-migration  # enter "add fsm workflows tables"
make migrate
```

## Verification

```bash
# Run tests
pytest tests/unit/test_fsm_workflows.py -v
```

## Quick Start

```python
from app.components.fsm_workflows.service import WorkflowEngine

engine = WorkflowEngine()
engine.register_definition(
    "approval",
    states=["draft", "review", "approved", "published"],
    transitions=[
        {"trigger": "submit", "source": "draft", "dest": "review"},
        {"trigger": "approve", "source": "review", "dest": "approved"},
        {"trigger": "publish", "source": "approved", "dest": "published"},
    ],
)

# Advance an entity through the workflow
new_state = engine.transition("approval", "submit", "draft")
print(new_state)  # "review"
```

## File Layout After Activation

```
app/components/fsm_workflows/
├── __init__.py          # register() — wires router and tasks
├── api.py               # CRUD endpoints + transition endpoint
├── service.py           # WorkflowEngine wrapping the transitions library
├── models.py            # WorkflowDefinition, WorkflowInstance
├── schemas.py           # WorkflowCreate, TransitionRequest
└── tasks.py             # execute_workflow_action
```
