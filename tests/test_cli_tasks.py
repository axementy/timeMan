import pytest
import os
import csv
from click.testing import CliRunner
from datetime import datetime, date, timedelta
from uuid import uuid4

# Assuming your CLI's main entry point is cli_main_func from timetracker.cli.main
# Adjust this import based on your actual CLI structure
from timetracker.cli.main import cli as cli_main_func
from timetracker.core.task import Task # For creating expected task objects if needed
from timetracker.core.logger import TaskLogger # For direct inspection/setup of CSV if needed

# --- Fixtures ---

@pytest.fixture(scope="module") # Use module scope if app context can be shared
def runner():
    return CliRunner()

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for CLI tests."""
    data_dir = tmp_path / "cli_test_data"
    data_dir.mkdir()
    # Ensure 'timetracker' sub-directory also exists as per LOG_FILE_PATH structure
    # LOG_FILE_PATH = os.path.join("timetracker", "data", LOG_FILE_NAME)
    # The CLI will create timetracker/data if it doesn't exist relative to CWD.
    # For tests, we want it inside tmp_path.
    # So, we can set current working directory for tests or mock the path construction.
    # Easiest is to let CLI create it in tmp_path by running CLI from tmp_path.
    return data_dir


@pytest.fixture
def isolated_cli_runner(runner: CliRunner, temp_data_dir, monkeypatch):
    """
    Provides a CliRunner that operates in an isolated filesystem created by tmp_path.
    It changes the current working directory to temp_data_dir for the duration of the test.
    This ensures that the 'timetracker/data/' path used by the CLI is created inside temp_data_dir.
    """
    # The CLI uses LOG_FILE_PATH = os.path.join("timetracker", "data", "tasks.csv")
    # It creates timetracker/data relative to its CWD.
    # To isolate, we run the CLI as if CWD is temp_data_dir.
    # The CLI will then create temp_data_dir/timetracker/data/tasks.csv

    # Path to where the CLI will create its data folder
    cli_actual_data_path = temp_data_dir / "timetracker" / "data"

    with runner.isolated_filesystem(temp_dir=temp_data_dir):
        # Current CWD is now inside temp_data_dir for the runner.invoke
        # The CLI will create timetracker/data/tasks.csv from here.
        yield runner

    # Cleanup: Handled by tmp_path fixture removing temp_data_dir


def get_csv_rows(data_dir_path, relative_log_path="timetracker/data/tasks.csv"):
    """Helper to read all data rows from the CSV log file."""
    full_log_path = os.path.join(data_dir_path, relative_log_path)
    if not os.path.exists(full_log_path):
        return []
    with open(full_log_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)

# --- Task CRUD Tests ---

def test_cli_task_create(isolated_cli_runner: CliRunner, temp_data_dir):
    runner = isolated_cli_runner
    result = runner.invoke(cli_main_func, [
        "task", "create",
        "--description", "CLI Test Task",
        "--priority", "1",
        "--due-time", "2024-12-31 10:00",
        "--type", "cli-work"
    ])
    assert result.exit_code == 0
    assert "Task 'CLI Test Task' (ID: " in result.output

    rows = get_csv_rows(temp_data_dir)
    assert len(rows) == 1
    assert rows[0]['description'] == "CLI Test Task"
    assert rows[0]['priority'] == "1"
    assert rows[0]['type'] == "cli-work"
    assert rows[0]['status'] == "pending" # Default
    assert "task_snapshot" in rows[0]['log_tags']

def test_cli_task_view_empty(isolated_cli_runner: CliRunner, temp_data_dir):
    runner = isolated_cli_runner
    result = runner.invoke(cli_main_func, ["task", "view"])
    assert result.exit_code == 0
    assert "No tasks found matching your criteria." in result.output # Updated msg

def test_cli_task_view_with_tasks(isolated_cli_runner: CliRunner, temp_data_dir):
    runner = isolated_cli_runner
    # Create a task first
    runner.invoke(cli_main_func, ["task", "create", "--description", "View Me"])

    result = runner.invoke(cli_main_func, ["task", "view"])
    assert result.exit_code == 0
    assert "View Me" in result.output
    assert "Sorted By: created_at, Order: ASC" in result.output # Default sort

def test_cli_task_view_sorting_and_filtering(isolated_cli_runner: CliRunner, temp_data_dir):
    runner = isolated_cli_runner
    runner.invoke(cli_main_func, ["task", "create", "-d", "Task A", "-p", "1", "-t", "TypeX"])
    runner.invoke(cli_main_func, ["task", "create", "-d", "Task B", "-p", "2", "-t", "TypeY"])
    runner.invoke(cli_main_func, ["task", "create", "-d", "Task C", "-p", "1", "-t", "TypeX", "--status", "completed"])

    # Test filtering
    result = runner.invoke(cli_main_func, ["task", "view", "--priority", "1"])
    assert "Task A" in result.output
    assert "Task C" in result.output
    assert "Task B" not in result.output
    assert "Applied Filters: Priority: 1" in result.output

    # Test sorting (e.g., by description descending)
    result = runner.invoke(cli_main_func, ["task", "view", "--sort-by", "description", "--sort-order", "desc"])
    assert result.output.find("Task C") < result.output.find("Task B") < result.output.find("Task A")
    assert "Sorted By: description, Order: DESC" in result.output

def test_cli_task_update(isolated_cli_runner: CliRunner, temp_data_dir):
    runner = isolated_cli_runner
    # Create a task
    create_result = runner.invoke(cli_main_func, ["task", "create", "-d", "Original Desc"])
    task_id = ""
    for line in create_result.output.splitlines():
        if "Task 'Original Desc' (ID: " in line:
            task_id = line.split("(ID: ")[1].split(")")[0]
            break
    assert task_id, "Could not extract task ID from create output"

    # Update the task
    result = runner.invoke(cli_main_func, [
        "task", "update", task_id,
        "--description", "Updated CLI Desc",
        "--priority", "3"
    ])
    assert result.exit_code == 0
    assert f"Task 'Updated CLI Desc' (ID: {task_id}) updated successfully." in result.output

    rows = get_csv_rows(temp_data_dir)
    updated_row = None
    # Snapshots are appended. Find the latest for this ID.
    for row in reversed(rows): # Check from end to get latest snapshot
        if row['id'] == task_id and row['log_tags'] == 'task_snapshot':
            updated_row = row
            break

    assert updated_row is not None
    assert updated_row['description'] == "Updated CLI Desc"
    assert updated_row['priority'] == "3"

def test_cli_task_delete(isolated_cli_runner: CliRunner, temp_data_dir):
    runner = isolated_cli_runner
    create_result = runner.invoke(cli_main_func, ["task", "create", "-d", "To Be Deleted"])
    task_id = create_result.output.split("(ID: ")[1].split(")")[0]

    result = runner.invoke(cli_main_func, ["task", "delete", task_id])
    assert result.exit_code == 0
    assert f"Task 'To Be Deleted' (ID: {task_id}) marked as deleted." in result.output

    rows = get_csv_rows(temp_data_dir)
    deleted_row_snapshot = None
    for row in reversed(rows):
         if row['id'] == task_id and row['log_tags'] == 'task_snapshot':
            deleted_row_snapshot = row
            break
    assert deleted_row_snapshot is not None
    assert deleted_row_snapshot['status'] == "deleted"

    # View should not show it by default
    view_result = runner.invoke(cli_main_func, ["task", "view"])
    assert "To Be Deleted" not in view_result.output

    # View with status deleted should show it
    view_deleted_result = runner.invoke(cli_main_func, ["task", "view", "--status", "deleted"])
    assert "To Be Deleted" in view_deleted_result.output


# --- Pomodoro and Report Integration Tests ---

@pytest.mark.slow # Mark as slow if time.sleep is not mocked effectively for Pomodoro
def test_cli_pomodoro_with_task_and_big_task_report(isolated_cli_runner: CliRunner, temp_data_dir, mocker):
    runner = isolated_cli_runner

    # Mock time.sleep for faster execution of Pomodoro timer intervals
    # This mock needs to be active when PomodoroTimer.start() is called by the CLI.
    # It's tricky to mock it globally for just the CLI subprocess via CliRunner.
    # An alternative: make PomodoroTimer durations very short for tests.
    # Or, the PomodoroTimer could accept a "tick_interval" for faster testing.
    # For now, this test might run slowly or assume very short default durations if they were changed.
    # Assuming PomodoroTimer can be made to run fast for tests (e.g., by env var or test mode).
    # Let's mock it at the source for the test.
    mocker.patch('timetracker.core.pomodoro.time.sleep', side_effect=lambda x: None) # No sleep

    # Create a task
    desc = "Big Pomodoro Task"
    create_result = runner.invoke(cli_main_func, ["task", "create", "-d", desc, "-p", "1"])
    task_id = create_result.output.split("(ID: ")[1].split(")")[0]

    # To make it a "big task", we need to log >120 minutes.
    # The Pomodoro command itself logs time. We need enough pomodoros.
    # 1 work interval (25 min default) is not enough.
    # Let's assume PomodoroTimer has test-friendly short durations or we log time manually.
    # For this test, we'll manually log time to make it a big task *before* the pomodoro.
    # This is not ideal, as pomodoro itself should make it big.
    # Better: PomodoroTimer uses a test_mode with 1-minute durations.
    # For now, let's assume it's a big task by mocking check_if_big_task_completed.
    # This is simpler than simulating many pomodoros.

    # We need to mock TaskLogger.check_if_big_task_completed called by PomodoroTimer
    # This means the TaskLogger instance used by PomodoroTimer (created in CLI command)
    # needs to have this method mocked.
    mocker.patch('timetracker.core.logger.TaskLogger.check_if_big_task_completed', return_value=True)
    mocker.patch('timetracker.core.logger.TaskLogger.get_total_logged_time_for_task', return_value=150) # For report

    # Run one pomodoro work interval for this task.
    # The CLI pomodoro loop will ask to start next interval, we'll say no.
    report_input = "This is my detailed report.\nIt has multiple lines.\nENDREPORT\nno\n" # Input for report, then 'no' to next interval
    result = runner.invoke(cli_main_func, [
        "pomodoro", "start",
        "--work", "1", # Short work interval for test speed (1 min)
        "--short-break", "1",
        "--task-id", task_id
    ], input=report_input) # Say 'no' to starting the break to exit loop

    assert result.exit_code == 0
    assert f"Task '{desc}' status updated to 'in-progress'." in result.output
    assert f"Work interval started for 1 minutes (Task ID: {task_id})." in result.output
    assert f"Task '{desc}' logged as 'completed'." in result.output
    assert f"Congratulations on completing a major task: '{desc}'!" in result.output
    assert "Would you like to write a brief report/summary for it?" in result.output
    assert "Report saved." in result.output # From _handle_big_task_completion_prompt

    # Verify report file content (simplified check)
    report_file_path = os.path.join(temp_data_dir, "timetracker", "data", "task_reports.md")
    assert os.path.exists(report_file_path)
    with open(report_file_path, "r") as f:
        content = f.read()
        assert f"## Task Report: {task_id} - {desc}" in content
        assert "This is my detailed report." in content
        assert "It has multiple lines." in content
        assert "Total Logged Time: 2 hours 30 minutes" in content # From the mocked 150 mins

def test_cli_report_daily_and_weekly(isolated_cli_runner: CliRunner, temp_data_dir):
    runner = isolated_cli_runner
    # Create some tasks and log work to have data for reports
    # Task 1: created today, worked on today, completed today
    today_str = date.today().strftime("%Y-%m-%d")
    task1_desc = "Daily Report Task 1"
    runner.invoke(cli_main_func, ["task", "create", "-d", task1_desc, "--due-time", today_str])
    task1_id = get_csv_rows(temp_data_dir)[-1]['id'] # Get last created task ID

    # Simulate pomodoro session for task1 (manually for this test, as pomodoro CLI is complex to script fully)
    # We'll create log entries directly for simplicity in report testing
    logger = TaskLogger(log_file_path=os.path.join(temp_data_dir, "timetracker/data/tasks.csv"))
    task1_obj = logger.get_task_by_id(task1_id)
    task1_obj.status = 'in-progress'; logger.save_task_snapshot(task1_obj)
    logger.log_task(task1_obj, datetime.now().replace(hour=10), datetime.now().replace(hour=11), tags=["work"]) # 60 min
    task1_obj.status = 'completed'; task1_obj.updated_at = datetime.now(); logger.save_task_snapshot(task1_obj)


    # Daily report for today
    result_daily = runner.invoke(cli_main_func, ["report", "daily", "--date", today_str])
    assert result_daily.exit_code == 0
    assert f"Daily Report for {today_str}" in result_daily.output
    assert "Total Tasks Completed: 1" in result_daily.output
    assert "Total Time Spent: 60 minutes" in result_daily.output
    assert task1_desc in result_daily.output

    # Weekly report for current week
    result_weekly = runner.invoke(cli_main_func, ["report", "weekly"]) # Uses defaults for current week
    assert result_weekly.exit_code == 0
    assert "Weekly Report" in result_weekly.output
    assert "Total Tasks Completed: 1" in result_weekly.output # Assuming only this task completed this week
    assert "Total Time Spent: 60 minutes" in result_weekly.output
    assert task1_desc in result_weekly.output
    assert "Avg Time Spent/Day:" in result_weekly.output
