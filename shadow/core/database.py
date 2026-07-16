import sqlite3
import os
from typing import List, Dict, Any, Optional
from shadow.core.config import get_config

def get_db_connection() -> sqlite3.Connection:
    config = get_config()
    db_path = config.db_path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable WAL mode for high performance and concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")

    # 1. Memory Table (conversation, preferences, working style, ideas, notes, lessons learned)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,          -- 'conversation', 'preference', 'insight', 'note', 'lesson_learned', 'skill'
        key TEXT,                        -- Optional key (e.g., 'user_working_style')
        content TEXT NOT NULL,
        tags TEXT,                       -- Comma-separated tags
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key);")

    # 2. Conversation History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,              -- 'user', 'assistant', 'system'
        content TEXT NOT NULL,
        provider TEXT,
        tokens INTEGER DEFAULT 0,
        cost REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation(session_id);")

    # 3. Goals Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT,                   -- 'Financial', 'Health', 'Skills', etc.
        priority TEXT,                   -- 'High', 'Medium', 'Low'
        dependencies TEXT,               -- Comma-separated dependencies/goals
        estimated_completion TEXT,
        confidence REAL DEFAULT 1.0,
        status TEXT DEFAULT 'pending',   -- 'pending', 'active', 'completed', 'failed'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);")

    # 4. Opportunities Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        url TEXT,
        category TEXT,                   -- 'Scholarship', 'Job', 'AI News', 'Hackathon'
        source TEXT,                     -- 'Web Search', 'GitHub', 'Research Paper'
        status TEXT DEFAULT 'new',       -- 'new', 'analyzed', 'converted', 'dismissed'
        confidence REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_opps_status ON opportunities(status);")

    # 5. Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        status TEXT DEFAULT 'pending',   -- 'pending', 'approved', 'running', 'completed', 'failed'
        safety_level INTEGER DEFAULT 0,  -- 0: Read-only, 1: Local writes, 2: Sensitive/Requires approval
        priority_score REAL DEFAULT 0.0,
        opportunity_id INTEGER,
        assigned_agent TEXT,
        result TEXT,
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority_score DESC);")

    # 6. Structured Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT NOT NULL,             -- 'INFO', 'WARNING', 'ERROR'
        reasoning TEXT,                  -- Thought process of why action was taken
        action TEXT NOT NULL,            -- Action executed
        duration REAL,                   -- In seconds
        result TEXT,                     -- Outcome summary or payload
        error TEXT,                      -- Exception traceback / error details
        provider TEXT,                   -- AI provider used
        tokens INTEGER DEFAULT 0,
        cost REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);")

    # 7. Approvals Table (for Safety Level 2 holds)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        parameters TEXT,                 -- JSON of parameters
        status TEXT DEFAULT 'pending',   -- 'pending', 'approved', 'rejected'
        reason TEXT,                     -- Reason for rejection or approval notes
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);")

    conn.commit()
    conn.close()
