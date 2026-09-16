"""
BandFlow — database helper functions

This is the ONLY file that should contain raw SQL. Everything else
(Flask routes, BLE callbacks) should call these functions instead of
writing SQL directly — keeps things easy to change later.

Add more functions here as you need them.
"""

import sqlite3

DB_PATH = "bandflow.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, e.g. row["description"]
    return conn


def create_task(description):
    """Create a new task. Returns the new task's id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (description) VALUES (?)", (description,))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def add_subtask(task_id, description, order_index, depends_on=None):
    """Add a subtask to a task. depends_on is another subtask's id, or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO subtasks (task_id, description, order_index, depends_on)
        VALUES (?, ?, ?, ?)
        """,
        (task_id, description, order_index, depends_on),
    )
    subtask_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return subtask_id


def get_subtasks_for_task(task_id):
    """Return all subtasks for a task, in order."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM subtasks WHERE task_id = ? ORDER BY order_index",
        (task_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_next_pending_subtask(task_id):
    """
    Return the next subtask that's ready to be shown on the band:
    status is 'pending' AND (no dependency, OR its dependency is 'done').
    Returns None if nothing is ready yet.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT subtasks.* FROM subtasks
        LEFT JOIN subtasks AS dependency ON subtasks.depends_on = dependency.id
        WHERE subtasks.task_id = ?
          AND subtasks.status = 'pending'
          AND (subtasks.depends_on IS NULL OR dependency.status = 'done')
        ORDER BY subtasks.order_index
        LIMIT 1
        """,
        (task_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def mark_subtask_done(subtask_id):
    """Mark a subtask as done."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subtasks SET status = 'done' WHERE id = ?",
        (subtask_id,),
    )
    conn.commit()
    conn.close()


def mark_subtask_active(subtask_id):
    """Mark a subtask as active (currently being shown on the band)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subtasks SET status = 'active' WHERE id = ?",
        (subtask_id,),
    )
    conn.commit()
    conn.close()
