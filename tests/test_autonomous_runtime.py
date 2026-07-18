import pytest
import asyncio
from shadow.core.database import init_db, get_db_connection
from shadow.core.runtime.intent_router import IntentRouter, IntentClass
from shadow.core.runtime.workflow_selector import WorkflowSelector, WorkflowType
from shadow.core.runtime.state_machine import StateMachine, RuntimeState
from shadow.core.runtime.execution_context import ExecutionContext
from shadow.core.runtime.progress_manager import ProgressManager
from shadow.core.runtime.validator import Validator
from shadow.core.runtime.executor_registry import executor_registry, BaseExecutor
from shadow.core.runtime.tool_selector import ToolSelector
from shadow.core.runtime.retry_manager import RetryManager
from shadow.core.runtime.task_executor import TaskExecutor
from shadow.core.runtime.result_builder import ResultBuilder
from shadow.core.runtime.execution_engine import ExecutionEngine
from shadow.core.runtime.runtime import ShadowRuntime
from shadow.cli.main import app as cli_app
from shadow.core.telegram import telegram_companion

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

@pytest.mark.asyncio
async def test_intent_router_classification():
    router = IntentRouter(provider_name="mock")

    # 1. Direct conversation
    res_conv = await router.classify_intent("Hello Ghost, how are you?")
    assert res_conv["intent"] in (IntentClass.CONVERSATION, IntentClass.QUESTION)
    assert res_conv["confidence"] > 0.0

    # 2. Heuristics fallback / explicit keyword check
    res_code = await router.classify_intent("generate html page")
    assert res_code["intent"] == IntentClass.CODING

@pytest.mark.asyncio
async def test_workflow_selector():
    selector = WorkflowSelector()

    # Simple Request
    wf_simple = selector.select_workflow("generate html", {"intent": IntentClass.CODING, "confidence": 0.95})
    assert wf_simple == WorkflowType.DIRECT_EXECUTION

    # Large project
    wf_large = selector.select_workflow("build a complex trading platform", {"intent": IntentClass.AUTONOMOUS_PROJECT, "confidence": 0.95})
    assert wf_large == WorkflowType.PROJECT_TASK_QUEUE

@pytest.mark.asyncio
async def test_state_machine_transitions():
    sm = StateMachine()
    assert sm.current_state == RuntimeState.IDLE
    assert sm.is_active() is False

    sm.transition_to(RuntimeState.REASONING)
    assert sm.current_state == RuntimeState.REASONING
    assert sm.is_active() is True

    sm.transition_to(RuntimeState.IDLE)
    assert sm.current_state == RuntimeState.IDLE

@pytest.mark.asyncio
async def test_execution_context():
    ctx = ExecutionContext("Build HTML page", "test_session")
    assert ctx.original_request == "Build HTML page"
    assert ctx.session_id == "test_session"

    data = ctx.to_dict()
    assert data["original_request"] == "Build HTML page"

    ctx2 = ExecutionContext.from_dict(data)
    assert ctx2.context_id == ctx.context_id

@pytest.mark.asyncio
async def test_progress_manager():
    pm = ProgressManager()
    assert pm.get_current_status() == "Idle"

    pm.start_step("Executing", "Running the initial code block")
    assert "Executing..." in pm.get_current_status()

    pm.complete_step("Executing", "Task finished")
    assert pm.get_current_status() == "Idle"

@pytest.mark.asyncio
async def test_validator():
    # HTML
    ok, msg = Validator.validate_html("<!DOCTYPE html><html><body><h1>test</h1></body></html>")
    assert ok is True

    ok_fail, msg_fail = Validator.validate_html("no html tags")
    assert ok_fail is False

    # Python syntax
    ok_py, msg_py = Validator.validate_python("def add(a, b):\n    return a + b")
    assert ok_py is True

    ok_py_fail, msg_py_fail = Validator.validate_python("def add(a, b)\n  return a")
    assert ok_py_fail is False

    # JSON
    ok_js, msg_js = Validator.validate_json('{"key": "value"}')
    assert ok_js is True

    ok_js_fail, msg_js_fail = Validator.validate_json('{"key": value}')
    assert ok_js_fail is False

    # Markdown
    ok_md, msg_md = Validator.validate_markdown("# Header\nContent")
    assert ok_md is True

@pytest.mark.asyncio
async def test_executor_registry_and_tool_selector():
    class DummyExecutor(BaseExecutor):
        async def execute(self, title, description, parameters):
            return {"success": True, "result": "dummy_output"}

    executor_registry.register_executor("dummy", DummyExecutor())
    assert executor_registry.get_executor("dummy") is not None

    selector = ToolSelector()
    tool_name = await selector.select_tool_for_task("Write code script", "Write a python file")
    assert tool_name in ("code_executor", "filesystem_executor")

@pytest.mark.asyncio
async def test_retry_manager_and_failure_recovery():
    retry_mgr = RetryManager(max_retries=2)
    counter = 0

    async def faulty_action():
        nonlocal counter
        counter += 1
        if counter < 2:
            return {"success": False, "error": "transient failure"}
        return {"success": True, "result": "recovered"}

    res = await retry_mgr.execute_with_recovery("Test task", "", faulty_action)
    assert res["success"] is True
    assert res["result"] == "recovered"
    assert counter == 2

@pytest.mark.asyncio
async def test_execution_engine_orchestration():
    engine = ExecutionEngine(provider_name="mock")

    # Direct execution workflow
    final_resp = await engine.execute_direct_workflow("generate simple html")
    assert "Completed Execution Report" in final_resp
    assert "Process request: generate simple html" in final_resp

    # Project workflow
    final_proj_resp = await engine.execute_project_workflow("Build an expense tracker application")
    assert "Completed Execution Report" in final_proj_resp

@pytest.mark.asyncio
async def test_shadow_runtime_process():
    runtime = ShadowRuntime(provider_name="mock")
    reply = await runtime.process_user_request("Hi there")
    # Natural conversation fallback
    assert len(reply) > 0

    reply_exec = await runtime.process_user_request("generate HTML table about books")
    assert "Completed Execution Report" in reply_exec

@pytest.mark.asyncio
async def test_telegram_companion_routes():
    # Test text message routes in telegram poller companion
    rep_help = await telegram_companion.handle_text_message("/help", "123456")
    assert "Welcome to PROJECT SHADOW" in rep_help

    rep_state = await telegram_companion.handle_text_message("/state", "123456")
    assert "Current State Machine State" in rep_state

    rep_progress = await telegram_companion.handle_text_message("/progress", "123456")
    assert "Active Status" in rep_progress

    rep_runtime = await telegram_companion.handle_text_message("/runtime", "123456")
    assert "Autonomous Runtime Metrics" in rep_runtime
