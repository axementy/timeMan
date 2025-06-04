import pytest
from datetime import datetime, timedelta
from uuid import UUID
from timetracker.core.task import Task

def test_task_creation_defaults():
    """Test Task creation with minimal required arguments and default status."""
    now = datetime.now()
    # Allow a small delta for comparison due to execution time
    time_buffer = timedelta(seconds=1)

    task = Task(description="Test Task", priority=1, due_time=None, type="work")

    assert isinstance(task.id, UUID)
    assert task.description == "Test Task"
    assert task.priority == 1
    assert task.due_time is None
    assert task.type == "work"
    assert task.status == "pending" # Default status

    assert (now - time_buffer) <= task.created_at <= (now + time_buffer)
    assert (now - time_buffer) <= task.updated_at <= (now + time_buffer)
    assert task.created_at == task.updated_at

def test_task_creation_specific_values():
    """Test Task creation with all arguments specified."""
    due = datetime.now() + timedelta(days=5)
    created_before = datetime.now()
    task = Task(description="Specific Task", priority=3, due_time=due, type="personal", status="in-progress")
    created_after = datetime.now()

    assert task.description == "Specific Task"
    assert task.priority == 3
    assert task.due_time == due
    assert task.type == "personal"
    assert task.status == "in-progress"
    assert created_before <= task.created_at <= created_after
    assert task.created_at == task.updated_at

def test_task_update_method():
    """Test the Task.update() method."""
    task = Task(description="Initial Desc", priority=1, due_time=None, type="T1")
    original_created_at = task.created_at
    original_updated_at = task.updated_at

    # Make sure updated_at is slightly later for the test
    # This can be flaky, consider mocking datetime.now if precision is an issue
    # For this test, a small sleep or assuming execution time delta is usually enough
    # import time; time.sleep(0.001)

    new_due_time = datetime.now() + timedelta(days=10)
    update_data = {
        "description": "Updated Desc",
        "priority": 2,
        "due_time": new_due_time,
        "type": "T2",
        "status": "completed"
    }
    task.update(**update_data)

    assert task.description == "Updated Desc"
    assert task.priority == 2
    assert task.due_time == new_due_time
    assert task.type == "T2"
    assert task.status == "completed"
    assert task.created_at == original_created_at # Should not change
    assert task.updated_at > original_updated_at # Should change

def test_task_update_partial():
    """Test updating only a subset of fields."""
    task = Task(description="Partial Update", priority=1, due_time=None, type="test")
    original_updated_at = task.updated_at

    # import time; time.sleep(0.001) # ensure time difference
    task.update(status="in-progress", priority=3)

    assert task.description == "Partial Update" # Unchanged
    assert task.priority == 3 # Changed
    assert task.status == "in-progress" # Changed
    assert task.updated_at > original_updated_at

def test_task_update_due_time_to_none():
    """Test updating due_time to None."""
    initial_due_time = datetime.now() + timedelta(days=1)
    task = Task(description="Due Time Test", priority=1, due_time=initial_due_time, type="test")

    # import time; time.sleep(0.001)
    task.update(due_time=None)
    assert task.due_time is None
    assert task.updated_at > initial_due_time # Check updated_at was modified

def test_task_repr():
    """Test the __repr__ method of Task."""
    due = datetime(2023, 12, 31, 10, 0, 0) # Fixed datetime for reproducible repr
    task = Task(description="Repr Test", priority=1, due_time=due, type="repr_type", status="pending")

    # Manually set id, created_at, updated_at for a fully reproducible repr string
    # This is because these are auto-generated with current time / random UUID
    # For a unit test of repr, controlling these is better.
    task.id = UUID("12345678-1234-5678-1234-567812345678")
    fixed_creation_time = datetime(2023, 1, 1, 12, 0, 0)
    task.created_at = fixed_creation_time
    task.updated_at = fixed_creation_time # Assuming update hasn't happened yet for this specific repr check

    expected_repr = (
        f"Task(id={task.id!r}, description='Repr Test', "
        f"priority=1, due_time={due!r}, "
        f"type='repr_type', status='pending', "
        f"created_at={fixed_creation_time!r}, updated_at={fixed_creation_time!r})"
    )
    assert repr(task) == expected_repr

def test_task_update_no_args():
    """Test calling update with no arguments updates 'updated_at'."""
    task = Task(description="No Args Update", priority=1, due_time=None, type="test")
    old_updated_at = task.updated_at
    # import time; time.sleep(0.001) # Ensure time difference for updated_at
    task.update()
    assert task.updated_at > old_updated_at
    # Check other fields remain unchanged
    assert task.description == "No Args Update"
    assert task.priority == 1
    assert task.due_time is None
    assert task.type == "test"
    assert task.status == "pending"

# To make the time assertions more robust, consider using pytest-freezegun
# or mocking datetime.now() if sub-second precision becomes an issue.
# For now, the timedelta buffer or small sleeps (commented out) might suffice.
# The sleeps are generally bad practice in tests, so mocking is preferred for flakiness.
# For the repr test, explicitly setting datetimes is the best way.
# For created_at/updated_at in general tests, comparing with a small buffer is common.
# Or assert that updated_at >= created_at.
