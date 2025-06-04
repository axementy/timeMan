"""
Timetracker CLI Application

This module provides a command-line interface for interacting with the timetracker
application, including task management, Pomodoro timer functionality, and report
generation.

It uses the `click` library to define commands and options. Core logic is delegated
to classes in `timetracker.core`.
"""
import click
import os
from datetime import datetime, date, timedelta
import uuid # For task view by ID, to validate UUID format if needed.
from typing import Optional # For type hints, though click often infers from defaults.

# --- Import Core Components ---
# This try-except block allows the CLI to be run directly (e.g., python timetracker/cli/main.py)
# from the project root during development, as well as when installed as a package.
try:
    from timetracker.core.pomodoro import PomodoroTimer
    from timetracker.core.logger import TaskLogger
    from timetracker.core.task import Task
except ImportError: # pragma: no cover
    # Fallback for direct script execution if project root is not in PYTHONPATH.
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from timetracker.core.pomodoro import PomodoroTimer
    from timetracker.core.logger import TaskLogger
    from timetracker.core.task import Task


# --- Configuration ---
# Default path for the CSV log file.
# Assumes execution from project root or that 'timetracker/data/' path is resolvable.
# For packaged applications, a user-specific data directory would be more robust.
LOG_FILE_PATH = os.path.join("timetracker", "data", "tasks.csv")


# --- Main CLI Group ---
@click.group()
def cli():
    """
    A simple command-line time tracker application.

    Provides tools for task management, Pomodoro timer sessions, and activity reporting.
    """
    pass

# --- Pomodoro Command Group ---
@cli.group()
def pomodoro():
    """Manage Pomodoro timers and work/break sessions."""
    pass

@pomodoro.command("start") # Explicitly naming command for clarity
@click.option('--work', 'work_duration', type=int, default=25,
              help='Duration of a work interval in minutes. Default: 25.')
@click.option('--short-break', 'short_break_duration', type=int, default=5,
              help='Duration of a short break in minutes. Default: 5.')
@click.option('--long-break', 'long_break_duration', type=int, default=15,
              help='Duration of a long break in minutes. Default: 15.')
@click.option('--task-id', 'task_id_str', type=str, default=None,
              help='ID of the task to associate with this Pomodoro session.')
def start_pomodoro_session(work_duration: int, short_break_duration: int, long_break_duration: int, task_id_str: Optional[str]):
    """
    Starts a Pomodoro timer with specified or default durations.

    A Pomodoro session consists of work intervals followed by short or long breaks.
    This command initiates the first interval (typically work). After each interval
    completes, it prompts to start the next one.

    If a --task-id is provided, the work intervals will be associated with that task,
    updating its status and logging work sessions. If a "big task" is completed,
    you may be prompted to write a brief report.

    Press Ctrl+C during an interval to pause it.
    """
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)
    timer = PomodoroTimer(
        work_duration=work_duration,
        short_break_duration=short_break_duration,
        long_break_duration=long_break_duration,
        task_logger_instance=logger # Pass logger to PomodoroTimer for its internal logging
    )
    
    task_info = f" (Task ID: {task_id_str})" if task_id_str else ""
    click.echo(f"Starting Pomodoro timer: Work: {work_duration}m, Short Break: {short_break_duration}m, Long Break: {long_break_duration}m{task_info}")
    click.echo("Press Ctrl+C to pause the timer at any time (during the countdown).")
    
    # Initial start of the first interval (usually work)
    completed_big_task_id_signal = timer.start(task_id=task_id_str)

    if completed_big_task_id_signal:
        _handle_big_task_completion_prompt(completed_big_task_id_signal, logger)

    # This loop manages the progression through Pomodoro intervals (work, break, work, etc.)
    # based on user confirmation after each interval completes.
    while True:
        if timer.is_running:
            # This state implies that timer.start() was non-blocking or finished unexpectedly early.
            # The current PomodoroTimer.start() is blocking for one interval.
            time.sleep(0.5)
            if not timer.is_running and timer.remaining_time == 0 :
                 pass # Interval completed, fall through
            elif not timer.is_running and timer.remaining_time > 0:
                 pass # Timer paused, fall through
            else:
                continue

        current_interval_display_name = timer.current_interval_type.replace('_', ' ')

        if timer.remaining_time == 0: # Interval naturally completed
            # PomodoroTimer.start() prints "Interval finished."
            # It then updates _current_interval_type to what the *next* interval should be.
            next_interval_type_display_name = timer.current_interval_type.replace('_', ' ')
            if click.confirm(f"Start the next interval ({next_interval_type_display_name})?", default=True):
                completed_big_task_id_signal = timer.start(task_id=timer.current_task_id)
                if completed_big_task_id_signal:
                    _handle_big_task_completion_prompt(completed_big_task_id_signal, logger)
            else:
                click.echo("Timer stopped.")
                break
        elif not timer.is_running and timer.remaining_time > 0: # Timer was paused
             click.echo(f"Timer paused. Remaining time: {timer.remaining_time // 60}m {timer.remaining_time % 60}s for {current_interval_display_name}.")
             if click.confirm(f"Resume {current_interval_display_name}?", default=True):
                 completed_big_task_id_signal = timer.start(task_id=timer.current_task_id)
                 if completed_big_task_id_signal:
                    _handle_big_task_completion_prompt(completed_big_task_id_signal, logger)
             else:
                click.echo("Timer stopped. Call reset or start again.")
                break
        elif not timer.is_running and timer.remaining_time == 0:
             click.echo("Timer is stopped/reset. Start again if needed.")
             break
        else:
            click.echo("Timer is in an unexpected state. Stopping.")
            break


# --- Helper for "Big Task" Report Prompt ---
def _handle_big_task_completion_prompt(task_id_str: str, logger: TaskLogger):
    """
    Handles prompting the user for a report if a "big task" was completed.

    Args:
        task_id_str (str): The ID of the task that was completed.
        logger (TaskLogger): The TaskLogger instance for saving the report.
    """
    task = logger.get_task_by_id(task_id_str)
    if not task:
        click.echo(f"Error: Could not retrieve details for completed task ID {task_id_str}.", err=True)
        return

    click.echo(click.style(f"\nCongratulations on completing a major task: '{task.description}'!", fg='green', bold=True))
    if click.confirm("Would you like to write a brief report/summary for it?", default=False):
        click.echo("Enter your report. Type 'ENDREPORT' on a new line and press Enter to finish.")
        report_lines = []
        while True:
            try:
                line = click.prompt("", prompt_suffix='> ')
                if line == 'ENDREPORT':
                    break
                report_lines.append(line)
            except click.exceptions.Abort:
                click.echo("\nReport input aborted.")
                return
        report_text = "\n".join(report_lines)
        total_time = logger.get_total_logged_time_for_task(task_id_str)
        logger.save_task_completion_report(task, report_text, total_time)
        click.echo("Report saved.")


# --- Task Management Command Group ---
@cli.group()
def task():
    """Manage tasks: create, view, update, and delete."""
    pass

def parse_datetime_string(datetime_str: str) -> Optional[datetime]:
    """
    Helper to parse datetime strings from CLI options into datetime objects.

    Supports "YYYY-MM-DD HH:MM:S", "YYYY-MM-DD HH:MM", and "YYYY-MM-DD" formats.
    If only date is provided, time defaults to 00:00:00.

    Args:
        datetime_str (str): The date/time string to parse.

    Returns:
        Optional[datetime]: A datetime object if parsing is successful.

    Raises:
        click.BadParameter: If the string cannot be parsed into any of the known formats.
    """
    if not datetime_str:
        return None
    formats_to_try = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(datetime_str, fmt)
            return dt
        except ValueError:
            continue
    raise click.BadParameter(f"Cannot parse date/time string: '{datetime_str}'. Use YYYY-MM-DD HH:MM:SS or YYYY-MM-DD.")

@task.command('create')
@click.option('--description', '-d', required=True, help="Task description.")
@click.option('--priority', '-p', type=int, default=2, help="Priority (e.g., 1-High, 2-Medium, 3-Low).")
@click.option('--due-time', '-dt', type=str, default=None, help="Due date/time (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD).")
@click.option('--type', '-t', 'task_type', default="work", help="Task type (e.g., work, personal).")
def create_task(description: str, priority: int, due_time: Optional[str], task_type: str):
    """
    Creates a new task with the provided details.

    A unique ID is automatically generated. The task's initial status is 'pending'.
    The task definition is saved as a snapshot in the log.
    """
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)
    parsed_due_time: Optional[datetime] = None
    if due_time:
        try:
            parsed_due_time = parse_datetime_string(due_time)
        except click.BadParameter as e:
            click.echo(e, err=True)
            return

    new_task = Task(
        description=description,
        priority=priority,
        due_time=parsed_due_time,
        type=task_type
    )
    try:
        logger.save_task_snapshot(new_task)
        click.echo(f"Task '{new_task.description}' (ID: {new_task.id}) created successfully.")
    except Exception as e: # pragma: no cover
        click.echo(f"Error creating task: {e}", err=True)

@task.command('view')
@click.option('--id', 'task_id_str', type=str, help="View a specific task by ID (UUID format).")
@click.option('--priority', 'filter_priority', type=int, help="Filter tasks by priority level.")
@click.option('--due-time', 'filter_due_time_str', type=str, help="Filter by due date (YYYY-MM-DD).")
@click.option('--type', 'filter_task_type', type=str, help="Filter tasks by type (case-insensitive).")
@click.option('--status', 'filter_status', type=str, help="Filter tasks by status (case-insensitive).")
@click.option('--sort-by', type=click.Choice(['priority', 'due_time', 'type', 'status', 'description', 'created_at', 'updated_at'], case_sensitive=False),
              default='created_at', help="Field to sort tasks by. Default: created_at.")
@click.option('--sort-order', type=click.Choice(['asc', 'desc'], case_sensitive=False),
              default='asc', help="Sort order (ascending or descending). Default: asc.")
def view_tasks(task_id_str: Optional[str], filter_priority: Optional[int],
               filter_due_time_str: Optional[str], filter_task_type: Optional[str],
               filter_status: Optional[str], sort_by: str, sort_order: str,
               view_all: Optional[bool]): # view_all retained from previous for compatibility, but unused
    """
    Displays tasks with various filtering and sorting options.

    By default, shows non-deleted tasks, sorted by creation date.
    Use options to filter by specific criteria and to control sorting order.
    When providing --id, other filters and sorting are generally ignored for that specific task lookup.
    """
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)

    # 1. Fetch all log entries and get the latest state for each unique task ID.
    all_tasks_from_log = logger.get_tasks() # Returns List[Task] from all log entries
    unique_tasks_dict: Dict[uuid.UUID, Task] = {}
    for t in all_tasks_from_log:
        if t.id not in unique_tasks_dict or t.updated_at > unique_tasks_dict[t.id].updated_at:
            unique_tasks_dict[t.id] = t

    processed_tasks: List[Task] = list(unique_tasks_dict.values())

    # If a specific task ID is requested, filter down to that task.
    if task_id_str:
        try:
            target_uuid = uuid.UUID(task_id_str)
            task_obj = unique_tasks_dict.get(target_uuid)
        except ValueError:
            click.echo(f"Error: Invalid format for task ID '{task_id_str}'. Must be a valid UUID.", err=True)
            return

        if task_obj:
            processed_tasks = [task_obj] # Show this task, regardless of its status for direct ID view
        else:
            click.echo(f"Task with ID '{task_id_str}' not found.")
            return

    # 2. Apply Filters (only if not viewing a single task by ID)
    active_filters = {}
    if not task_id_str:
        if filter_priority is not None:
            processed_tasks = [t for t in processed_tasks if t.priority == filter_priority]
            active_filters['Priority'] = str(filter_priority)
        if filter_due_time_str:
            try:
                filter_date = parse_datetime_string(filter_due_time_str)
                if not filter_date: raise click.BadParameter("Due time filter string not parsed to date object.")
                filter_date_actual = filter_date.date()
                processed_tasks = [t for t in processed_tasks if t.due_time and t.due_time.date() == filter_date_actual]
                active_filters['Due Date'] = filter_date_actual.strftime("%Y-%m-%d")
            except click.BadParameter as e:
                click.echo(f"Error parsing --due-time: {e}", err=True)
                return
        if filter_task_type:
            processed_tasks = [t for t in processed_tasks if t.type.lower() == filter_task_type.lower()]
            active_filters['Type'] = filter_task_type

        if filter_status:
            processed_tasks = [t for t in processed_tasks if t.status.lower() == filter_status.lower()]
            active_filters['Status'] = filter_status
        else: # Default: hide deleted tasks if no specific status filter is applied
            processed_tasks = [t for t in processed_tasks if t.status != 'deleted']

    # 3. Apply Sorting (only if not viewing a single task by ID, or if desired for single too)
    reverse_sort = (sort_order == 'desc')

    def get_sort_key(task_item: Task):
        """Key function for sorting tasks, handling None values and case-insensitivity."""
        val = getattr(task_item, sort_by)
        if val is None:
            if sort_by == 'due_time':
                return (datetime.max if not reverse_sort else datetime.min)
            # For other types, if None, use a value that sorts them consistently.
            # E.g., for numbers, float('inf') or float('-inf'). For strings, empty string.
            # This ensures Nones are grouped.
            if isinstance(getattr(task_item, sort_by, None), (int, float)): # Check original type for None num
                 return float('inf') if not reverse_sort else float('-inf')
            return ""
        if isinstance(val, str): # Case-insensitive sort for strings
            return val.lower()
        return val

    processed_tasks.sort(key=get_sort_key, reverse=reverse_sort)

    # 4. Display Tasks
    if not processed_tasks:
        click.echo("No tasks found matching your criteria.")
        return

    click.echo("\n--- Tasks ---")
    if active_filters:
        filters_str = ", ".join([f"{k}: {v}" for k,v in active_filters.items()])
        click.echo(f"Applied Filters: {filters_str}")
    if len(processed_tasks) > 1 or not task_id_str : # Show sort order if multiple tasks or general view
        click.echo(f"Sorted By: {sort_by}, Order: {sort_order.upper()}")

    for t in processed_tasks:
        due_str = t.due_time.strftime("%Y-%m-%d %H:%M") if t.due_time else "None"
        created_str = t.created_at.strftime('%Y-%m-%d %H:%M')
        updated_str = t.updated_at.strftime('%Y-%m-%d %H:%M')
        click.echo(
            f"  ID: {t.id}\n"
            f"    Desc: {t.description}\n"
            f"    Priority: {t.priority}, Due: {due_str}, Type: {t.type}, Status: {t.status}\n"
            f"    Created: {created_str}, Updated: {updated_str}"
        )
    click.echo(f"--- {len(processed_tasks)} Task(s) ---")


# --- Reporting Command Group ---
@cli.group()
def report():
    """Generate and display task activity reports."""
    pass

@report.command('daily')
@click.option('--date', 'report_date_str', type=str, default=None,
              help="Date for the report (YYYY-MM-DD). Defaults to today.")
def daily_report(report_date_str: Optional[str]):
    """Generates and displays a summary report for a specific day."""
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)
    report_date_obj: date = date.today()

    if report_date_str:
        try:
            parsed_dt = parse_datetime_string(report_date_str)
            if not parsed_dt: raise ValueError("Date string could not be parsed.") # Should be caught by parse_datetime_string
            report_date_obj = parsed_dt.date()
        except (ValueError, click.BadParameter) as e:
            click.echo(f"Error: Invalid date format for --date: {e}. Please use YYYY-MM-DD.", err=True)
            return

    try:
        daily_summary = logger.generate_daily_report(report_date_obj)
        click.echo(f"\n--- Daily Report for {daily_summary['report_date']} ---")
        click.echo(f"Total Tasks Completed: {daily_summary['total_tasks_completed_on_date']}")
        click.echo(f"Total Time Spent: {daily_summary['total_time_spent_minutes']} minutes")

        if daily_summary['time_spent_by_type']:
            click.echo("\nTime Spent by Task Type:")
            for task_type_item, minutes in daily_summary['time_spent_by_type'].items():
                click.echo(f"  - {task_type_item}: {minutes} minutes")

        if daily_summary['completed_tasks_details']:
            click.echo("\nTasks Marked Completed Today:")
            for task_info in daily_summary['completed_tasks_details']:
                click.echo(f"  - ID: {task_info['id']}, Desc: {task_info['description']}")

        if daily_summary['tasks_worked_on_details']:
            click.echo("\nOther Tasks Worked On Today (not marked completed today):")
            for task_info in daily_summary['tasks_worked_on_details']:
                 click.echo(f"  - ID: {task_info['id']}, Desc: {task_info['description']}, Status: {task_info['status']}")
        click.echo("--- End of Report ---")

    except Exception as e: # pragma: no cover
        click.echo(f"Error generating daily report: {e}", err=True)


@report.command('weekly')
@click.option('--start-date', 'start_date_str', type=str, default=None,
              help="Start date for the report (YYYY-MM-DD). Defaults to start of current week (Monday).")
@click.option('--end-date', 'end_date_str', type=str, default=None,
              help="End date for the report (YYYY-MM-DD). Defaults to end of current week (Sunday).")
def weekly_report(start_date_str: Optional[str], end_date_str: Optional[str]):
    """Generates and displays a summary report for a specified week."""
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)
    
    today = date.today()
    start_date_obj: date = today - timedelta(days=today.weekday()) # Default to current week's Monday
    end_date_obj: date = start_date_obj + timedelta(days=6) # Default to current week's Sunday

    if start_date_str:
        try:
            parsed_dt = parse_datetime_string(start_date_str)
            if not parsed_dt: raise ValueError("Start date string could not be parsed.")
            start_date_obj = parsed_dt.date()
        except (ValueError, click.BadParameter) as e:
            click.echo(f"Error: Invalid format for --start-date: {e}. Use YYYY-MM-DD.", err=True)
            return

    if end_date_str:
        try:
            parsed_dt = parse_datetime_string(end_date_str)
            if not parsed_dt: raise ValueError("End date string could not be parsed.")
            end_date_obj = parsed_dt.date()
        except (ValueError, click.BadParameter) as e:
            click.echo(f"Error: Invalid format for --end-date: {e}. Use YYYY-MM-DD.", err=True)
            return

    if start_date_obj > end_date_obj:
        click.echo("Error: Start date must be before or same as end date.", err=True)
        return

    try:
        weekly_summary = logger.generate_weekly_report(start_date_obj, end_date_obj)
        click.echo(f"\n--- Weekly Report ({weekly_summary['start_date']} to {weekly_summary['end_date']}) ---")
        click.echo(f"Total Days in Report: {weekly_summary['total_days']}")
        click.echo(f"Total Tasks Completed: {weekly_summary['total_tasks_completed_in_week']}")
        click.echo(f"Total Time Spent: {weekly_summary['total_time_spent_minutes']} minutes")

        if weekly_summary['time_spent_by_type']:
            click.echo("\nTime Spent by Task Type:")
            for task_type_item, minutes in weekly_summary['time_spent_by_type'].items():
                click.echo(f"  - {task_type_item}: {minutes} minutes")

        if weekly_summary['tasks_worked_on_or_completed_details']:
            click.echo("\nTasks Worked On or Completed This Week:")
            for task_info in weekly_summary['tasks_worked_on_or_completed_details']:
                click.echo(f"  - ID: {task_info['id']}, Desc: {task_info['description']}, Status: {task_info['status']}")

        if weekly_summary['daily_averages']:
            click.echo("\nDaily Averages:")
            click.echo(f"  - Avg Tasks Completed/Day: {weekly_summary['daily_averages']['avg_tasks_completed_per_day']:.2f}")
            click.echo(f"  - Avg Time Spent/Day: {weekly_summary['daily_averages']['avg_time_spent_minutes_per_day']:.2f} minutes")
        click.echo("--- End of Report ---")

    except Exception as e: # pragma: no cover
        click.echo(f"Error generating weekly report: {e}", err=True)


@task.command('update')
@click.argument('task_id_str', type=str)
@click.option('--description', '-d', help="New task description.")
@click.option('--priority', '-p', type=int, help="New priority.")
@click.option('--due-time', '-dt', type=str, help="New due date/time (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD). To clear, pass empty string for some systems or specific keyword if supported (not standard).")
@click.option('--type', '-t', 'new_task_type', help="New task type.")
@click.option('--status', '-s', help="New task status (e.g., pending, in-progress, completed).")
def update_task(task_id_str: str, description: Optional[str], priority: Optional[int],
                due_time: Optional[str], new_task_type: Optional[str], status: Optional[str]):
    """
    Updates an existing task identified by its ID.

    Only the provided options will be updated. For example, to change only
    the priority, provide `--priority <value>`. The task's `updated_at`
    timestamp will be set to the current time upon any successful update.
    """
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)
    task_to_update = logger.get_task_by_id(task_id_str)

    if not task_to_update:
        click.echo(f"Task with ID '{task_id_str}' not found.", err=True)
        return

    updated_fields = {}
    if description is not None:
        updated_fields['description'] = description
    if priority is not None:
        updated_fields['priority'] = priority
    if due_time is not None: # If due_time option is given
        try:
            # If user provides an empty string for due_time, parse_datetime_string returns None
            updated_fields['due_time'] = parse_datetime_string(due_time)
        except click.BadParameter as e:
            click.echo(e, err=True)
            return
    if new_task_type is not None:
        updated_fields['type'] = new_task_type
    if status is not None:
        updated_fields['status'] = status

    if not updated_fields:
        click.echo("No update parameters provided.")
        return

    try:
        task_to_update.update(**updated_fields)
        logger.save_task_snapshot(task_to_update)
        click.echo(f"Task '{task_to_update.description}' (ID: {task_id_str}) updated successfully.")
    except Exception as e: # pragma: no cover
        click.echo(f"Error updating task: {e}", err=True)


@task.command('delete')
@click.argument('task_id_str', type=str)
def delete_task(task_id_str: str):
    """
    Marks a task as 'deleted'.

    This does not remove the task from the log file but changes its status
    to 'deleted'. Deleted tasks are typically hidden from default views.
    """
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)
    task_to_delete = logger.get_task_by_id(task_id_str)

    if not task_to_delete:
        click.echo(f"Task with ID '{task_id_str}' not found.", err=True)
        return

    if task_to_delete.status == 'deleted':
        click.echo(f"Task (ID: {task_id_str}) is already marked as deleted.")
        return

    try:
        task_to_delete.update(status='deleted')
        logger.save_task_snapshot(task_to_delete)
        click.echo(f"Task '{task_to_delete.description}' (ID: {task_id_str}) marked as deleted.")
    except Exception as e: # pragma: no cover
        click.echo(f"Error deleting task: {e}", err=True)


# --- Legacy Log Entry Group ---
@cli.group(name="logentry")
def log_entry_group():
    """
    Log generic timed entries (legacy functionality).

    These commands are for logging arbitrary timed events that may or may not
    be associated with a structured Task object. This differs from the main
    task management which uses `timetracker task ...` commands.
    """
    pass

def parse_tags(ctx, param, value: Optional[str]) -> List[str]:
    """Click callback to parse comma-separated tags into a list."""
    if value:
        return [tag.strip() for tag in value.split(',') if tag.strip()]
    return []

@log_entry_group.command('add')
@click.argument('description', type=str)
@click.option('--start', 'start_time', type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]),
              required=True, help='Start time (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS).')
@click.option('--end', 'end_time', type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]),
              required=True, help='End time (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS).')
@click.option('--tags', callback=parse_tags, default="", help='Comma-separated tags (e.g., "dev,projectX").')
@click.option('--task-id', 'task_id_for_log', type=str, default=None,
              help="Optional Task ID to associate this log entry with an existing structured task.")
def add_log_entry(description: str, start_time: datetime, end_time: datetime, tags: List[str], task_id_for_log: Optional[str]):
    """
    Logs a new timed event or work session.

    If a --task-id is provided, this log entry is associated with an existing
    Task. The TaskLogger's `log_task` method will then record the state of that
    Task along with this timed activity. The `description` argument to this CLI
    command is currently ignored by `log_task` if a task_id is found (it uses the task's own description).

    Important: Current version requires --task-id for logging as `TaskLogger.log_task` expects a Task object.
    """
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)

    if task_id_for_log:
        task_to_log_against = logger.get_task_by_id(task_id_for_log)
        if not task_to_log_against:
            click.echo(f"Error: Task ID '{task_id_for_log}' not found. Cannot log this entry.", err=True)
            return
        try:
            # Note: The 'description' field passed to this CLI command is not directly used here
            # because logger.log_task uses the description from the task_to_log_against object.
            logger.log_task(
                task=task_to_log_against,
                start_time=start_time,
                end_time=end_time,
                tags=tags
            )
            click.echo(f"Log entry for task '{task_to_log_against.description}' (ID: {task_id_for_log}) added successfully.")
        except Exception as e: # pragma: no cover
            click.echo(f"Error logging entry for task {task_id_for_log}: {e}", err=True)
    else:
        # This path is currently not supported as TaskLogger.log_task requires a Task object.
        click.echo("Error: --task-id is required for 'logentry add'. Logging arbitrary events without a task ID is not currently supported by this command.", err=True)


# --- Legacy View Raw Entries Group ---
@cli.group(name="viewentries")
def view_entries_group():
    """
    View raw log entries from the CSV file (legacy functionality).

    This provides a direct look at the data as it is stored in the log.
    """
    pass

@view_entries_group.command(name='all')
@click.option('--date', 'filter_date_str', type=click.DateTime(formats=["%Y-%m-%d"]),
              help='Filter log entries by date (YYYY-MM-DD), based on log_start_time.')
def view_all_log_entries(filter_date_str: Optional[datetime]):
    """Displays all raw logged entries from the CSV. Can be filtered by date."""
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)

    filter_date_obj: Optional[date] = None
    if filter_date_str: # click.DateTime passes datetime object
        filter_date_obj = filter_date_str.date()

    if not os.path.exists(LOG_FILE_PATH): # Check if log file exists
        click.echo(f"Log file not found at {LOG_FILE_PATH}.", err=True)
        return

    try:
        # Use the TaskLogger's get_log_entries method to fetch raw data
        raw_rows = logger.get_log_entries(date_filter=filter_date_obj)

        if not raw_rows:
            click.echo("No log entries found." + (f" for {filter_date_obj.strftime('%Y-%m-%d')}" if filter_date_obj else ""))
            return

        click.echo("\n--- Raw Log Entries ---")
        # Display each row. Using _CSV_HEADER from logger for consistent field order.
        for row_dict in raw_rows:
            display_parts = []
            for key in logger._CSV_HEADER:
                if key in row_dict: # Ensure key exists in the row from CSV
                    display_parts.append(f"{key}: \"{row_dict[key]}\"")
            click.echo("  " + ", ".join(display_parts))
        click.echo("--- End of Raw Log Entries ---")

    except Exception as e: # pragma: no cover
        click.echo(f"Error retrieving log entries: {e}", err=True)


if __name__ == '__main__': # pragma: no cover
    # This section allows running the CLI directly via `python timetracker/cli/main.py`
    # Ensures the main data directory exists before any logger operation attempts it.
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if log_dir and not os.path.exists(log_dir): # Create directory if it doesn't exist
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            # Warn if directory creation fails, though TaskLogger also tries.
            click.echo(f"Warning: Could not create log directory {log_dir}: {e}", err=True)
    cli()
