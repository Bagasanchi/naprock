"""Plain-script tests for the BandFlow SQLite helpers."""

import os
import tempfile

import db
import setup_db


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def main():
    original_db_path = db.DB_PATH
    original_setup_path = setup_db.DB_PATH
    temporary_directory = tempfile.TemporaryDirectory()
    temporary_path = os.path.join(temporary_directory.name, "test.db")

    try:
        db.DB_PATH = temporary_path
        setup_db.DB_PATH = temporary_path
        setup_db.setup()

        task_id = db.create_task("Build API")
        first_id = db.add_subtask(task_id, "Create endpoint", 1)
        second_id = db.add_subtask(
            task_id, "Connect database", 2, depends_on=first_id
        )

        assert_equal(db.list_tasks()[0]["status"], "in_progress", "task status before completion")

        db.mark_subtask_active(first_id)
        first = db.get_subtasks_for_task(task_id)[0]
        assert_equal(first["status"], "active", "active subtask status")
        if first["started_at"] is None:
            raise AssertionError("mark_subtask_active did not set started_at")

        assert_equal(
            db.get_next_pending_subtask(task_id),
            None,
            "dependent subtask must wait for its dependency",
        )

        db.mark_subtask_done(first_id)
        next_subtask = db.get_next_pending_subtask(task_id)
        assert_equal(next_subtask["id"], second_id, "next dependency-ready subtask")

        db.mark_subtask_active(second_id)
        db.mark_subtask_done(second_id)
        assert_equal(db.list_tasks()[0]["status"], "complete", "completed task status")

        print("All database tests passed.")
    finally:
        db.DB_PATH = original_db_path
        setup_db.DB_PATH = original_setup_path
        temporary_directory.cleanup()


if __name__ == "__main__":
    main()
