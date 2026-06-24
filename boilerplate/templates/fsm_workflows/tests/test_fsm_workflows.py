"""Unit tests for FSM Workflows component."""

from __future__ import annotations

import importlib


def test_import_fsm_workflows_component():
    """Smoke test: the component module imports cleanly."""
    mod = importlib.import_module("app.components.fsm_workflows")
    assert hasattr(mod, "register"), "FSM Workflows component must expose register()"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.fsm_workflows import register

    assert callable(register)
    assert register.__name__ == "register"


def test_engine_register_definition():
    """WorkflowEngine can register a definition and it becomes available."""
    from app.components.fsm_workflows.service import WorkflowEngine

    engine = WorkflowEngine()
    states = ["draft", "review", "approved", "published"]
    transitions = [
        {"trigger": "submit", "source": "draft", "dest": "review"},
        {"trigger": "approve", "source": "review", "dest": "approved"},
        {"trigger": "publish", "source": "approved", "dest": "published"},
    ]

    engine.register_definition("article_workflow", states, transitions)
    assert "article_workflow" in engine._machines


def test_engine_transition_success():
    """WorkflowEngine.transition advances state on valid trigger."""
    from app.components.fsm_workflows.service import WorkflowEngine

    engine = WorkflowEngine()
    states = ["draft", "review", "approved"]
    transitions = [
        {"trigger": "submit", "source": "draft", "dest": "review"},
        {"trigger": "approve", "source": "review", "dest": "approved"},
    ]

    engine.register_definition("test_wf", states, transitions)
    new_state = engine.transition("test_wf", "submit", "draft")
    assert new_state == "review"


def test_engine_invalid_transition_returns_none():
    """WorkflowEngine.transition returns None for invalid trigger."""
    from app.components.fsm_workflows.service import WorkflowEngine

    engine = WorkflowEngine()
    states = ["draft", "review"]
    transitions = [{"trigger": "submit", "source": "draft", "dest": "review"}]

    engine.register_definition("test_wf", states, transitions)
    result = engine.transition("test_wf", "approve", "draft")
    assert result is None


def test_engine_get_triggers():
    """get_available_triggers returns trigger names from current state."""
    from app.components.fsm_workflows.service import WorkflowEngine

    engine = WorkflowEngine()
    states = ["draft", "review", "approved"]
    transitions = [
        {"trigger": "submit", "source": "draft", "dest": "review"},
        {"trigger": "approve", "source": "review", "dest": "approved"},
    ]

    engine.register_definition("test_wf", states, transitions)
    triggers = engine.get_available_triggers("test_wf", "draft")
    assert "submit" in triggers


def test_workflow_create_schema():
    """WorkflowCreate schema accepts states and transitions."""
    from app.components.fsm_workflows.schemas import WorkflowCreate

    wf = WorkflowCreate(
        name="test",
        states=["a", "b"],
        transitions=["a->b"],
    )
    assert wf.name == "test"
    assert wf.states == ["a", "b"]


def test_transition_request_schema():
    """TransitionRequest schema accepts trigger and optional context."""
    from app.components.fsm_workflows.schemas import TransitionRequest

    req = TransitionRequest(trigger="submit")
    assert req.trigger == "submit"
    assert req.context is None

    req2 = TransitionRequest(trigger="approve", context={"note": "looks good"})
    assert req2.context == {"note": "looks good"}
