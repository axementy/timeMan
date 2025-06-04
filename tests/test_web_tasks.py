import pytest
import os
from datetime import datetime, date, timedelta
from uuid import uuid4
from flask import session

# Assuming create_app is the entry point for your Flask app
from timetracker.web.app import create_app
from timetracker.core.task import Task
from timetracker.core.logger import TaskLogger # For direct interaction if needed for setup

# --- Fixtures ---

@pytest.fixture(scope="module")
def app():
    """Create and configure a new app instance for each test module."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SECRET_KEY": "pytest_secret_key",
        "WTF_CSRF_ENABLED": False, # Disable CSRF for simpler form posts in tests
    })
    yield app

@pytest.fixture
def temp_data_dir_web(tmp_path_factory):
    """Create a temporary data directory unique to each test function using this."""
    # Using tmp_path_factory to ensure a unique dir if tests run in parallel (though usually not for web tests like this)
    # Or just tmp_path if simple sequential execution is assumed.
    # This will be base for `timetracker/data`
    return tmp_path_factory.mktemp("web_test_data_root")


@pytest.fixture
def client(app, temp_data_dir_web, monkeypatch):
    """A test client for the app, with LOG_FILE_PATH patched."""

    # Define the path where the app will write its data, inside the temp dir
    # LOG_FILE_PATH in routes.py is os.path.join("timetracker", "data", "tasks.csv")
    # So, we need temp_data_dir_web / "timetracker" / "data" / "tasks.csv"

    # The routes.py module will be imported when create_app() is called or when routes are used.
    # We need to patch LOG_FILE_PATH where it's defined in timetracker.web.routes

    # For reports file
    test_reports_md_path = temp_data_dir_web / "timetracker_data_tests" / "task_reports.md"

    # For CSV log file
    # This path needs to match what TaskLogger will use when routes.py's LOG_FILE_PATH is patched.
    # The `TaskLogger` instances created in routes.py will use the patched path.
    # The `PomodoroTimer` might create its own logger if not passed one; ensure its default path
    # is also managed or it's passed a configured logger.
    # In PomodoroTimer, if task_logger_instance is None, it creates one with default path.
    # This default path construction (os.path.join("timetracker", "data", "tasks.csv"))
    # also needs to be relative to a controlled CWD for tests, or be patched.

    # Let's ensure the directory for the CSV exists within the temp structure
    # The CLI tests relied on CWD being the temp_data_dir. Web tests are different.
    # We will patch the LOG_FILE_PATH in routes.py module.

    # Define the test CSV file path within the temp directory structure
    # This structure should mirror what the app expects, e.g., timetracker/data/tasks.csv
    # but rooted in temp_data_dir_web.

    # Actual path for CSV tasks.csv
    # When routes.py runs `os.path.join("timetracker", "data", "tasks.csv")`,
    # if CWD is project root, it's `project_root/timetracker/data/tasks.csv`.
    # We need to ensure this path is redirected into `temp_data_dir_web`.

    # The patch in test_web_legacy.py is a good example:
    # @patch('timetracker.web.routes.LOG_FILE_PATH', TEST_WEB_LOG_FILE)
    # We need a similar patch but for pytest.

    # Path for tasks.csv inside the temp directory
    # This is where the patched LOG_FILE_PATH in routes.py should point.
    csv_log_dir = temp_data_dir_web / "timetracker" / "data"
    csv_log_dir.mkdir(parents=True, exist_ok=True)
    test_csv_log_file = csv_log_dir / "tasks.csv"

    # Path for task_reports.md inside the temp directory
    reports_md_dir = temp_data_dir_web / "timetracker" / "data" # Same dir for simplicity
    reports_md_dir.mkdir(parents=True, exist_ok=True)
    test_reports_md_file = reports_md_dir / "task_reports.md"

    monkeypatch.setattr("timetracker.web.routes.LOG_FILE_PATH", str(test_csv_log_file))

    # For TaskLogger's save_task_completion_report, it constructs path internally.
    # We need to patch os.path.join or the path within that specific function if it's not configurable.
    # Let's mock os.path.join specifically for the reports file creation:
    original_os_path_join = os.path.join
    def mock_os_path_join(*args):
        if args == ("timetracker", "data", "task_reports.md"):
            return str(test_reports_md_file)
        return original_os_path_join(*args)
    monkeypatch.setattr("timetracker.core.logger.os.path.join", mock_os_path_join)


    # Clean up files before test
    if os.path.exists(test_csv_log_file): os.remove(test_csv_log_file)
    if os.path.exists(test_reports_md_file): os.remove(test_reports_md_file)

    with app.test_client() as client:
        yield client

    # Clean up files after test (optional, as tmp_path_factory handles base dir)
    # if os.path.exists(test_csv_log_file): os.remove(test_csv_log_file)
    # if os.path.exists(test_reports_md_file): os.remove(test_reports_md_file)


def get_web_csv_rows(temp_data_dir_web):
    """Helper to read CSV rows from the web test's temporary log file."""
    # Path constructed as per the monkeypatching in `client` fixture
    log_file = temp_data_dir_web / "timetracker" / "data" / "tasks.csv"
    if not log_file.exists():
        return []
    with open(log_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)

# --- Task CRUD Tests ---

def test_web_task_list_empty(client):
    response = client.get("/tasks/all")
    assert response.status_code == 200
    assert b"No tasks found." in response.data

def test_web_task_create(client, temp_data_dir_web):
    # GET the form
    response = client.get("/tasks/create")
    assert response.status_code == 200
    assert b"Create Task" in response.data

    # POST to create
    task_data = {
        "description": "Web Test Task",
        "priority": "1",
        "due_time": "2025-01-01 10:00",
        "type": "web-work"
    }
    response = client.post("/tasks/create", data=task_data, follow_redirects=True)
    assert response.status_code == 200 # After redirect to /tasks/all
    assert b"Task 'Web Test Task' created successfully!" in response.data
    assert b"Web Test Task" in response.data # Should be in the list now

    rows = get_web_csv_rows(temp_data_dir_web)
    assert len(rows) == 1
    assert rows[0]['description'] == "Web Test Task"
    assert rows[0]['priority'] == "1"
    assert rows[0]['type'] == "web-work"
    assert "task_snapshot" in rows[0]['log_tags']

def test_web_task_edit(client, temp_data_dir_web):
    # First, create a task to edit
    logger = TaskLogger(str(temp_data_dir_web / "timetracker" / "data" / "tasks.csv"))
    task_to_edit = Task("Edit Me Task", 2, None, "editing")
    logger.save_task_snapshot(task_to_edit)
    task_id = str(task_to_edit.id)

    # GET the edit form
    response = client.get(f"/tasks/edit/{task_id}")
    assert response.status_code == 200
    assert b"Edit Task: Edit Me Task" in response.data
    assert b'value="Edit Me Task"' in response.data # Check form pre-fill

    # POST to update
    update_data = {
        "description": "Edited Task via Web",
        "priority": "3",
        "status": "in-progress"
        # Type and due_time not provided, should retain old or default if logic implies
    }
    response = client.post(f"/tasks/edit/{task_id}", data=update_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Task 'Edited Task via Web' updated successfully!" in response.data
    assert b"Edited Task via Web" in response.data # In list
    assert b"Status: in-progress" in response.data # Check updated status in list

    rows = get_web_csv_rows(temp_data_dir_web)
    # Find the latest snapshot for this task
    latest_snapshot = None
    for row in reversed(rows):
        if row['id'] == task_id and "task_snapshot" in row['log_tags']:
            latest_snapshot = row
            break
    assert latest_snapshot is not None
    assert latest_snapshot['description'] == "Edited Task via Web"
    assert latest_snapshot['priority'] == "3"
    assert latest_snapshot['status'] == "in-progress"

def test_web_task_delete(client, temp_data_dir_web):
    logger = TaskLogger(str(temp_data_dir_web / "timetracker" / "data" / "tasks.csv"))
    task_to_delete = Task("Delete Me Task", 1, None, "deleting")
    logger.save_task_snapshot(task_to_delete)
    task_id = str(task_to_delete.id)

    response = client.post(f"/tasks/delete/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Task 'Delete Me Task' marked as deleted." in response.data
    assert b"Delete Me Task" not in response.data # Should not be in default list view

    # Verify status in CSV
    rows = get_web_csv_rows(temp_data_dir_web)
    latest_snapshot = None
    for row in reversed(rows):
        if row['id'] == task_id and "task_snapshot" in row['log_tags']:
            latest_snapshot = row
            break
    assert latest_snapshot is not None
    assert latest_snapshot['status'] == "deleted"

# --- Pomodoro Web Integration Tests ---

def test_web_pomodoro_page_loads_with_task_dropdown(client, temp_data_dir_web):
    # Create a pending task
    logger = TaskLogger(str(temp_data_dir_web / "timetracker" / "data" / "tasks.csv"))
    task = Task("Pending Task for Pomodoro", 1, None, "pomo-test")
    logger.save_task_snapshot(task)

    response = client.get("/pomodoro")
    assert response.status_code == 200
    assert b"Pomodoro Timer" in response.data
    assert b"Associate Task (Optional):" in response.data
    assert f'value="{str(task.id)}'.encode() in response.data # Check if task ID is in dropdown options
    assert b"Pending Task for Pomodoro" in response.data


def test_web_pomodoro_start_work_with_task_and_finish_prompts_for_big_task_report(client, temp_data_dir_web, monkeypatch):
    # Create a task
    log_file_path = str(temp_data_dir_web / "timetracker" / "data" / "tasks.csv")
    logger = TaskLogger(log_file_path)
    task_desc = "Web Big Pomo Task"
    task = Task(task_desc, 1, None, "pomo-big")
    task_id = str(task.id)
    logger.save_task_snapshot(task) # Initial save

    # Mock TaskLogger methods for this specific flow
    # This is tricky because the logger is instantiated in routes.py.
    # We need to ensure the instance used by the route has these mocked methods.
    # Patching the class methods globally for this test.
    monkeypatch.setattr(TaskLogger, 'get_total_logged_time_for_task', lambda self, tid: 150)
    monkeypatch.setattr(TaskLogger, 'check_if_big_task_completed', lambda self, tid, threshold=120: True)

    # 1. Start work with the task
    with client: # To maintain session
        response = client.post("/pomodoro/start_work", data={"task_id": task_id}, follow_redirects=True)
        assert response.status_code == 200
        assert f"Task '{task_desc}' status updated to in-progress.".encode() in response.data # Flash message

        with client.session_transaction() as sess:
            assert sess['pomodoro_state']['current_task_id'] == task_id
            assert sess['pomodoro_state']['interval_type'] == 'work'
            assert sess['pomodoro_state']['is_running'] is True

        # 2. Finish the work interval (JS would normally trigger this after timer ends)
        response = client.post("/pomodoro/finish_interval", follow_redirects=False) # Don't follow redirect yet
        assert response.status_code == 302 # Should redirect to prompt_task_report
        assert f"/tasks/prompt_report/{task_id}" in response.location

        # Check for flash message about big task (will be shown on next GET)
        # response_after_redirect = client.get(response.location)
        # assert b"Congratulations on completing a major task!" in response_after_redirect.data

        # 3. GET the prompt report page
        response_prompt_get = client.get(response.location) # Follow the redirect
        assert response_prompt_get.status_code == 200
        assert b"Task Completion Report" in response_prompt_get.data
        assert f"Congratulations on completing a major task: <strong>{task_desc}</strong>".encode() in response_prompt_get.data

        # 4. POST the report
        report_text_content = "This is the web report for the big task."
        response_report_post = client.post(f"/tasks/prompt_report/{task_id}", data={"report_text": report_text_content}, follow_redirects=True)
        assert response_report_post.status_code == 200 # Redirects to /pomodoro
        assert b"Task report saved successfully!" in response_report_post.data

        # Verify report file content
        report_file_path = temp_data_dir_web / "timetracker" / "data" / "task_reports.md" # As per mock_os_path_join
        assert report_file_path.exists()
        content = report_file_path.read_text()
        assert f"## Task Report: {task_id} - {task_desc}" in content
        assert report_text_content in content
        assert "Total Logged Time: 2 hours 30 minutes" in content # from mocked 150 mins


# --- Web Reporting Tests ---
def test_web_reports_index(client):
    response = client.get("/reports")
    assert response.status_code == 200
    assert b"Reports" in response.data
    assert b"Daily Report" in response.data
    assert b"Weekly Report" in response.data

def test_web_daily_report(client, temp_data_dir_web):
    # Setup some data for today
    logger = TaskLogger(str(temp_data_dir_web / "timetracker" / "data" / "tasks.csv"))
    today = date.today()
    task = Task("Daily Web Report Task", 1, None, "report-test")
    task.created_at = datetime.combine(today, datetime.min.time())
    task.updated_at = datetime.combine(today, datetime.min.time().replace(hour=1))
    task.status = "completed"
    logger.save_task_snapshot(task) # Completed snapshot for today
    logger.log_task(task, datetime.combine(today, datetime.min.time().replace(hour=2)),
                    datetime.combine(today, datetime.min.time().replace(hour=3)), tags=["work"]) # 60 min work

    response = client.get(f"/reports/daily?date={today.isoformat()}")
    assert response.status_code == 200
    assert f"Daily Report for {today.isoformat()}".encode() in response.data
    assert b"Total Tasks Completed Today:</strong> 1" in response.data
    assert b"Total Time Spent Today:</strong> 60 minutes" in response.data
    assert b"Daily Web Report Task" in response.data

# Add more tests for weekly report, edge cases, etc.
# Test forms validation for task create/edit if more complex rules are added.
# Test CSRF if it were enabled.
# Test different scenarios for Pomodoro task logging (e.g. task not found).
# Test pagination if task list grows very large (not implemented, but for future).
# Test error pages or specific error messages for robustness.
