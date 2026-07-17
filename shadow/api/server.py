import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from shadow.core.config import get_config
from shadow.core.database import get_db_connection, init_db
from shadow.goals.engine import goals_engine
from shadow.goals.scanner import OpportunityScanner
from shadow.goals.generator import TaskGenerator
from shadow.goals.priority import priority_engine
from shadow.goals.executor import execution_engine
from shadow.goals.reflection import reflection_engine
from shadow.core.scheduler import scheduler
from shadow.core.runtime import autonomous_runtime

app = FastAPI(title="Shadow OS Background Server", version="1.0.0")

class ApprovalRequest(BaseModel):
    approved: bool
    reason: Optional[str] = None

class QueryRequest(BaseModel):
    queries: List[str]

class MockTelegramMessageRequest(BaseModel):
    text: str
    chat_id: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    init_db()
    # Boot periodic background scheduler
    await scheduler.start()
    # Boot continuous reasoning loop
    await autonomous_runtime.start()

    # If Telegram companion has been configured, start bot listener task
    from shadow.core.telegram import telegram_companion
    await telegram_companion.start()

@app.on_event("shutdown")
async def shutdown_event():
    # Gracefully stop background scheduler
    await scheduler.stop()
    # Gracefully stop reasoning loop
    await autonomous_runtime.stop()

    from shadow.core.telegram import telegram_companion
    await telegram_companion.stop()

@app.get("/status")
def get_status():
    config = get_config()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'")
    pending_tasks = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) as count FROM opportunities WHERE status = 'new'")
    new_opportunities = cursor.fetchone()["count"]
    conn.close()

    return {
        "status": "online",
        "app_name": config.app_name,
        "database_path": config.db_path,
        "pending_tasks": pending_tasks,
        "new_opportunities": new_opportunities
    }

@app.get("/goals")
def get_goals():
    return {"success": True, "goals": goals_engine.get_active_goals()}

@app.post("/scan")
async def scan_opportunities(request: QueryRequest):
    scanner = OpportunityScanner()
    opps = await scanner.scan(request.queries)
    return {"success": True, "scanned_queries": request.queries, "opportunities_found": len(opps)}

@app.post("/convert/{opportunity_id}")
async def convert_opportunity(opportunity_id: int):
    generator = TaskGenerator()
    tasks = await generator.generate_tasks_for_opportunity(opportunity_id)
    priority_engine.reprioritize_all_tasks()
    return {"success": True, "tasks_generated": len(tasks)}

@app.post("/execute/{task_id}")
async def execute_task(task_id: int):
    res = await execution_engine.execute_task(task_id)
    return {"success": True, "result": res}

@app.get("/approvals")
def list_approvals():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM approvals WHERE status = 'pending'")
    approvals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"success": True, "pending_approvals": approvals}

@app.post("/approve/{approval_id}")
def process_approval_endpoint(approval_id: int, request: ApprovalRequest):
    try:
        execution_engine.process_approval(approval_id, request.approved, request.reason)
        return {"success": True, "message": f"Approval #{approval_id} processed."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/reflect")
async def trigger_reflection():
    reflection = await reflection_engine.perform_daily_reflection()
    return {"success": True, "reflection": reflection}

# --- Telegram Mock Endpoint ---
@app.post("/telegram/mock_message")
async def process_mock_telegram_message(request: MockTelegramMessageRequest):
    """
    Simulate a message sent to the Telegram companion bot.
    Returns the bot's natural response.
    """
    from shadow.core.telegram import telegram_companion
    reply = await telegram_companion.handle_text_message(request.text, request.chat_id or "test_chat_id")
    return {"success": True, "reply": reply}

def start_server(port: int = 8000, host: str = "127.0.0.1"):
    uvicorn.run(app, host=host, port=port)
