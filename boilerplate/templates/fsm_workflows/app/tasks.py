"""FSM Workflow background tasks using Procrastinate."""

from __future__ import annotations

import structlog

from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="fsm_workflows.execute_workflow_action")
def execute_workflow_action(
    workflow_name: str,
    trigger: str,
    from_state: str,
    to_state: str,
    entity_id: str,
    entity_type: str,
) -> None:
    """Execute async side effects after a workflow transition.

    This task runs after a successful state transition. Override or extend
    this function to trigger notifications, webhooks, or other actions
    based on the workflow, trigger, and state change.
    """
    logger.info(
        "workflow_action_executed",
        workflow=workflow_name,
        trigger=trigger,
        from_state=from_state,
        to_state=to_state,
        entity_id=entity_id,
        entity_type=entity_type,
    )
