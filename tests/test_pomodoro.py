import pytest
from unittest.mock import MagicMock, call # For mocking TaskLogger
from datetime import datetime, timedelta
import time # To mock time.sleep

from timetracker.core.pomodoro import PomodoroTimer
from timetracker.core.task import Task
from timetracker.core.logger import TaskLogger # Required for type hint and potentially for mock spec

# --- Fixtures ---

@pytest.fixture
def mock_task_logger(mocker):
    """Creates a MagicMock instance for TaskLogger."""
    # We can spec it if TaskLogger is complex, to ensure methods exist.
    # For now, a simple MagicMock is fine.
    # If TaskLogger methods called by PomodoroTimer are not present in MagicMock,
    # tests will fail or misbehave. Using spec=TaskLogger helps catch this.
    # However, spec=TaskLogger requires TaskLogger to be fully importable and defined.
    logger = MagicMock(spec=TaskLogger)
    logger.get_task_by_id.return_value = None # Default mock behavior
    logger.check_if_big_task_completed.return_value = False # Default
    return logger

@pytest.fixture
def pomodoro_timer(mock_task_logger):
    """Returns a PomodoroTimer instance with a mocked TaskLogger."""
    # Ensure PomodoroTimer's default logger creation is bypassed by providing one
    return PomodoroTimer(work_duration=25, short_break_duration=5, long_break_duration=15,
                         task_logger_instance=mock_task_logger)

@pytest.fixture
def sample_task_for_pomodoro():
    """A sample task object to be 'retrieved' by the mocked logger."""
    task = Task(description="Pomodoro Task", priority=1, due_time=None, type="work")
    # task.id should be a UUID, str(task.id) will be used as current_task_id string
    return task

# --- Test Cases ---

def test_pomodoro_initialization(pomodoro_timer: PomodoroTimer, mock_task_logger: MagicMock):
    assert pomodoro_timer.work_duration == 25 * 60
    assert not pomodoro_timer.is_running
    assert pomodoro_timer._current_interval_type == 'work'
    assert pomodoro_timer.current_task_id is None
    assert pomodoro_timer.task_logger == mock_task_logger # Ensure mock is used

def test_start_associates_task_id(pomodoro_timer: PomodoroTimer, mocker):
    mocker.patch('time.sleep') # Mock time.sleep to prevent actual sleeping
    test_task_id = "test-task-123"

    # Mock get_task_by_id to return None initially for status update part
    pomodoro_timer.task_logger.get_task_by_id.return_value = None

    pomodoro_timer.start(task_id=test_task_id)

    assert pomodoro_timer.current_task_id == test_task_id
    # is_running becomes False after one interval completes if not paused/interrupted
    # The start method runs one full interval.
    assert not pomodoro_timer.is_running


def test_start_work_interval_logs_status_in_progress(pomodoro_timer: PomodoroTimer, sample_task_for_pomodoro: Task, mocker):
    mocker.patch('time.sleep')
    task_id_str = str(sample_task_for_pomodoro.id)

    # Simulate task is initially 'pending'
    sample_task_for_pomodoro.status = 'pending'
    pomodoro_timer.task_logger.get_task_by_id.return_value = sample_task_for_pomodoro

    pomodoro_timer.start(task_id=task_id_str)

    # Verify task status update and logging
    # Check that get_task_by_id was called to fetch the task
    pomodoro_timer.task_logger.get_task_by_id.assert_any_call(task_id_str)

    # Check that log_task was called to log 'in-progress' status update
    # The first call to log_task for a new task in a work interval is the status update.
    args_list = pomodoro_timer.task_logger.log_task.call_args_list
    assert len(args_list) >= 1 # Could be more if also completed in this short test

    # Check the first log_task call (status update to in-progress)
    # Call: log_task(task_object, start_time, end_time, tags=[...])
    # The task object passed should have status 'in-progress'
    logged_task_for_status_update = args_list[0][0][0] # First arg of first call
    assert logged_task_for_status_update.status == 'in-progress'
    assert "status_update" in args_list[0][0][3] # Check tags in the fourth argument
    assert "start" in args_list[0][0][3]

def test_work_interval_completion_logs_task_completed(pomodoro_timer: PomodoroTimer, sample_task_for_pomodoro: Task, mocker):
    mocker.patch('time.sleep') # Make timer run instantly
    task_id_str = str(sample_task_for_pomodoro.id)

    # Simulate task is 'in-progress' when interval starts
    sample_task_for_pomodoro.status = 'in-progress'
    pomodoro_timer.task_logger.get_task_by_id.return_value = sample_task_for_pomodoro
    # Ensure check_if_big_task_completed returns False to not trigger that path yet
    pomodoro_timer.task_logger.check_if_big_task_completed.return_value = False

    pomodoro_timer.start(task_id=task_id_str) # This runs one full work interval

    # Verify log_task for work session completion
    # The call related to marking task 'completed' and logging work session
    # args_list[0] might be in-progress if task was pending
    # args_list[1] would be the completion log
    # For this test, we assume it was already in-progress, so only one get_task_by_id for start, then one for completion.

    # Find the log_task call that corresponds to the work session completion
    completion_log_call = None
    for call_item in pomodoro_timer.task_logger.log_task.call_args_list:
        tags = call_item[0][3] # tags is the 4th argument of log_task
        if "work_session" in tags and "completed" in tags:
            completion_log_call = call_item
            break

    assert completion_log_call is not None, "Work session completion log not found"
    logged_task_object = completion_log_call[0][0] # task object is the first argument
    assert logged_task_object.status == 'completed'


def test_big_task_completion_signal(pomodoro_timer: PomodoroTimer, sample_task_for_pomodoro: Task, mocker):
    mocker.patch('time.sleep')
    task_id_str = str(sample_task_for_pomodoro.id)

    sample_task_for_pomodoro.status = 'in-progress'
    pomodoro_timer.task_logger.get_task_by_id.return_value = sample_task_for_pomodoro
    # Simulate that this IS a big task
    pomodoro_timer.task_logger.check_if_big_task_completed.return_value = True

    returned_task_id = pomodoro_timer.start(task_id=task_id_str)

    assert returned_task_id == task_id_str
    # Verify check_if_big_task_completed was called with the correct ID
    pomodoro_timer.task_logger.check_if_big_task_completed.assert_called_with(task_id_str)

def test_no_big_task_signal_if_not_big(pomodoro_timer: PomodoroTimer, sample_task_for_pomodoro: Task, mocker):
    mocker.patch('time.sleep')
    task_id_str = str(sample_task_for_pomodoro.id)

    sample_task_for_pomodoro.status = 'in-progress'
    pomodoro_timer.task_logger.get_task_by_id.return_value = sample_task_for_pomodoro
    # Simulate that this is NOT a big task
    pomodoro_timer.task_logger.check_if_big_task_completed.return_value = False

    returned_task_id = pomodoro_timer.start(task_id=task_id_str)

    assert returned_task_id is None

def test_stop_clears_task_id(pomodoro_timer: PomodoroTimer):
    pomodoro_timer.current_task_id = "some-task-id"
    pomodoro_timer.stop()
    assert pomodoro_timer.current_task_id is None

def test_reset_clears_task_id(pomodoro_timer: PomodoroTimer):
    pomodoro_timer.current_task_id = "some-task-id"
    pomodoro_timer.reset()
    assert pomodoro_timer.current_task_id is None

def test_pause_preserves_task_id(pomodoro_timer: PomodoroTimer):
    """ Test that pause preserves current_task_id and related _current_work_interval_start_time """
    task_id = "task-for-pause-test"
    pomodoro_timer.current_task_id = task_id
    # Simulate that work interval had started
    pomodoro_timer._current_work_interval_start_time = datetime.now()

    pomodoro_timer.is_running = True # Simulate timer is running before pause
    pomodoro_timer.pause()

    assert pomodoro_timer.current_task_id == task_id
    assert pomodoro_timer._current_work_interval_start_time is not None
    assert not pomodoro_timer.is_running

def test_timer_transitions_after_work_session(pomodoro_timer: PomodoroTimer, mocker):
    mocker.patch('time.sleep')
    pomodoro_timer.task_logger.get_task_by_id.return_value = None # No task for this test

    # Work -> Short Break
    pomodoro_timer.start() # Completes 1st work interval
    assert pomodoro_timer._current_interval_type == 'short_break'
    assert pomodoro_timer._completed_work_intervals == 1

    # Short Break -> Work
    pomodoro_timer.start() # Completes 1st short break
    assert pomodoro_timer._current_interval_type == 'work'

    # Work -> Short Break
    pomodoro_timer.start() # Completes 2nd work interval
    assert pomodoro_timer._current_interval_type == 'short_break'
    assert pomodoro_timer._completed_work_intervals == 2

    pomodoro_timer.start() # Completes 2nd short break
    pomodoro_timer.start() # Completes 3rd work interval
    assert pomodoro_timer._completed_work_intervals == 3

    pomodoro_timer.start() # Completes 3rd short break
    pomodoro_timer.start() # Completes 4th work interval
    assert pomodoro_timer._current_interval_type == 'long_break' # Should be long break
    assert pomodoro_timer._completed_work_intervals == 4

    # Long Break -> Work
    pomodoro_timer.start() # Completes long break
    assert pomodoro_timer._current_interval_type == 'work'
    # _completed_work_intervals remains 4, it resets implicitly when a new cycle of 4 work starts
    # or it could be explicitly reset after long break. Current code doesn't reset it, it just uses % 4.
    # This is fine for cycle logic.

# Note: The PomodoroTimer's `start` method prints to console. In tests, this output
# can be suppressed using `mocker.patch('builtins.print')` if it becomes noisy.
# For these tests, we are not asserting print statements, so it's okay.
