"""WorkflowEngine — wraps the transitions library for state machine execution."""

from __future__ import annotations

from typing import Any

import structlog
from transitions import Machine

logger = structlog.get_logger()


class WorkflowEngine:
    """Manages finite-state machines using the transitions library.

    Each workflow definition is materialized as a Machine instance,
    and entity instances track their current state.
    """

    def __init__(self) -> None:
        self._machines: dict[str, Machine] = {}

    def register_definition(
        self,
        name: str,
        states: list[str],
        transitions: list[dict[str, Any]],
    ) -> None:
        """Register a workflow definition and build its state machine."""
        if name in self._machines:
            logger.warning("workflow_already_registered", name=name)
            return

        model = _WorkflowModel(name)

        try:
            machine = Machine(
                model=model,
                states=states if states else [],
                transitions=transitions if transitions else [],
                initial=states[0] if states else "initial",
            )
        except Exception:
            logger.exception("workflow_machine_creation_failed", name=name)
            raise

        self._machines[name] = machine
        logger.info("workflow_registered", name=name)

    def transition(self, name: str, trigger: str, current_state: str) -> str | None:
        """Attempt a transition on a registered workflow and return the new state."""
        if name not in self._machines:
            logger.warning("workflow_not_found", name=name)
            return None

        machine = self._machines[name]
        model = machine.model
        model.state = current_state

        try:
            model.trigger(trigger)
        except AttributeError:
            logger.warning(
                "invalid_transition", workflow=name, trigger=trigger, state=current_state
            )
            return None

        return model.state

    def get_available_triggers(self, name: str, current_state: str) -> list[str]:
        """Return available trigger names from a given state."""
        if name not in self._machines:
            return []

        machine = self._machines[name]
        model = machine.model
        model.state = current_state

        triggers = machine.get_triggers(current_state)
        return [t for t in triggers if t != "to_initial"]


class _WorkflowModel:
    """Lightweight model used as the state machine carrier."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.state = "initial"
