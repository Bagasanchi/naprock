"""
BandFlow — database test script

Run this AFTER setup_db.py, with no Flask or BLE involved, to prove
the schema and helper functions actually work:
    python3 test_db.py

It creates a fake "onboard new employee" task with 3 subtasks where
subtask 2 depends on subtask 1, and subtask 3 depends on subtask 2.
Then it walks through marking them done one at a time, printing what
the "next subtask" logic picks at each step.
"""

from db import create_task, add_subtask, get_next_pending_subtask, mark_subtask_done

print("Creating a fake task...")
task_id = create_task("Onboard new employee")
print(f"Created task id={task_id}")

subtask_1_id = add_subtask(task_id, "Prepare workstation", order_index=1)
subtask_2_id = add_subtask(task_id, "Create accounts", order_index=2, depends_on=subtask_1_id)
subtask_3_id = add_subtask(task_id, "Assign orientation", order_index=3, depends_on=subtask_2_id)

print(f"Added subtasks: {subtask_1_id}, {subtask_2_id}, {subtask_3_id}")
print()

for step in range(1, 5):
    next_subtask = get_next_pending_subtask(task_id)
    if next_subtask is None:
        print(f"Step {step}: nothing left to do — all subtasks are done!")
        break

    print(f"Step {step}: next subtask to show on the band -> \"{next_subtask['description']}\" (id={next_subtask['id']})")
    print(f"  Marking it done...")
    mark_subtask_done(next_subtask["id"])
    print()

print("Test complete. If subtask order above was 1 -> 2 -> 3, the dependency logic works correctly.")
