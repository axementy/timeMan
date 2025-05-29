import click
import os
from datetime import datetime, date

# Adjust imports to be relative to the project structure if running as a module
# For direct script execution, ensure PYTHONPATH is set or use another approach
try:
    from timetracker.core.pomodoro import PomodoroTimer
    from timetracker.core.logger import TaskLogger
except ImportError:
    # This fallback allows direct execution for development if timetracker is in PYTHONPATH
    # or if the script is run from the project root and paths are adjusted.
    # For a packaged app, the `from timetracker.core...` should work.
    import sys
    # Assuming the script is in timetracker/cli/main.py, to import from timetracker/core:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from timetracker.core.pomodoro import PomodoroTimer
    from timetracker.core.logger import TaskLogger


# Define the default log file path relative to the project's 'timetracker' directory
# This assumes the script or the packaged module can determine its root or a known base path.
# For simplicity, using a path relative to where the command might be run from,
# or assuming 'timetracker/data/' exists.
LOG_FILE_DIR = "timetracker_data" # Simplified: create in current dir or specify full path
LOG_FILE_NAME = "tasks.csv"
# A more robust way for a package is to use appdirs or similar, but for this exercise:
# We assume 'timetracker/data/tasks.csv' is desired relative to project root.
# When running `python -m timetracker.cli.main`, cwd is usually project root.
LOG_FILE_PATH = os.path.join("timetracker", "data", LOG_FILE_NAME)


@click.group()
def cli():
    """A simple time tracker CLI."""
    pass

# --- Pomodoro Group ---
@cli.group()
def pomodoro():
    """Manage Pomodoro timers."""
    pass

@pomodoro.command()
@click.option('--work', 'work_duration', type=int, default=25, help='Duration of a work interval in minutes.')
@click.option('--short-break', 'short_break_duration', type=int, default=5, help='Duration of a short break in minutes.')
@click.option('--long-break', 'long_break_duration', type=int, default=15, help='Duration of a long break in minutes.')
def start(work_duration, short_break_duration, long_break_duration):
    """Starts a Pomodoro timer with specified or default durations."""
    timer = PomodoroTimer(
        work_duration=work_duration,
        short_break_duration=short_break_duration,
        long_break_duration=long_break_duration
    )
    click.echo(f"Starting Pomodoro timer: Work: {work_duration}m, Short Break: {short_break_duration}m, Long Break: {long_break_duration}m")
    click.echo("Press Ctrl+C to stop the timer at any time.")
    
    # The timer needs to be started for the first interval
    timer.start() # Start the first work interval
    
    while True:
        if timer.is_running: # Should be false after first start() completes
            pass # Waiting for current interval to finish or be paused by start() itself

        # After an interval finishes, timer.is_running is False.
        # timer.current_interval_type has been updated.
        # We need to call start() again to begin the next interval.
        if timer.get_remaining_time == 0: # Interval naturally completed
            click.echo(f"To begin the next interval ({timer.get_current_interval_type.replace('_', ' ')}), run 'pomodoro start' again or re-run current.")
            click.echo("For now, the timer requires manual restart for each segment via CLI 'start'.")
            # The current design of PomodoroTimer's start() method completes one interval and stops.
            # To make it continuous, PomodoroTimer.start() would need an outer loop,
            # or this CLI would need to call it repeatedly.
            # For this version, we'll follow the "start next interval" logic from PomodoroTimer
            if click.confirm(f"Start the next interval ({timer.get_current_interval_type.replace('_', ' ')})?", default=True):
                timer.start()
            else:
                click.echo("Timer stopped.")
                break
        elif not timer.is_running and timer.get_remaining_time > 0 : # Timer was paused or stopped by Ctrl+C
             if timer.get_current_interval_type == 'work' and timer.get_remaining_time == timer.work_duration: # Stopped fully
                 click.echo("Timer was stopped.")
                 break
             # If it was paused mid-interval, the current PomodoroTimer doesn't explicitly differentiate
             # a pause from a stop via Ctrl+C during sleep.
             # For now, any non-running state with remaining time is considered paused/stopped.
             click.echo(f"Timer paused/stopped. Remaining time: {timer.get_remaining_time}s for {timer.get_current_interval_type}.")
             if click.confirm(f"Resume {timer.get_current_interval_type.replace('_', ' ')}?", default=True):
                 timer.start() # This will resume from remaining_time
             else:
                click.echo("Timer stopped.")
                break
        
        if not timer.is_running and timer.get_remaining_time == 0 and timer._current_interval_type == 'work' and timer._completed_work_intervals == 0 :
            # This condition implies the timer was stopped and reset, ready for a fresh start
             click.echo("Timer is reset. Start again if needed.")
             break


# --- Log Group ---
@cli.group()
def log():
    """Log completed tasks."""
    pass

def parse_tags(ctx, param, value):
    if value:
        return [tag.strip() for tag in value.split(',')]
    return []

@log.command()
@click.argument('description', type=str)
@click.option('--start', 'start_time', type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S"]), required=True, help='Start time in YYYY-MM-DDTHH:MM:SS format.')
@click.option('--end', 'end_time', type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S"]), required=True, help='End time in YYYY-MM-DDTHH:MM:SS format.')
@click.option('--duration', 'duration_minutes', type=int, required=True, help='Duration of the task in minutes.')
@click.option('--tags', callback=parse_tags, help='Comma-separated tags (e.g., "dev,projectX").')
def task(description, start_time, end_time, duration_minutes, tags):
    """Logs a new task with specified details."""
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)
    try:
        # Ensure start_time and end_time are datetime objects (Click does this)
        logger.log_task(
            task_description=description,
            start_time=start_time, # Already datetime from Click
            end_time=end_time,     # Already datetime from Click
            duration_minutes=duration_minutes,
            tags=tags if tags else []
        )
        click.echo(f"Task '{description}' logged successfully to {LOG_FILE_PATH}.")
    except Exception as e:
        click.echo(f"Error logging task: {e}", err=True)

# --- View Group ---
@cli.group()
def view():
    """View logged data."""
    pass

@view.command(name='log') # Renamed to avoid conflict with the 'log' group
@click.option('--date', 'filter_date_str', type=click.DateTime(formats=["%Y-%m-%d"]), help='Filter tasks by date (YYYY-MM-DD).')
def view_log_command(filter_date_str):
    """Displays logged tasks. Can be filtered by date."""
    logger = TaskLogger(log_file_path=LOG_FILE_PATH)
    
    filter_date_obj = None
    if filter_date_str:
        filter_date_obj = filter_date_str.date() # Convert datetime from Click to date object

    try:
        tasks = logger.get_tasks(date_filter=filter_date_obj)
        if not tasks:
            click.echo("No tasks found." + (f" for {filter_date_obj.strftime('%Y-%m-%d')}" if filter_date_obj else ""))
            return

        click.echo("\n--- Logged Tasks ---")
        for t in tasks:
            tags_str = f"Tags: {', '.join(t['tags'])}" if t['tags'] else "Tags: None"
            click.echo(
                f"  Start: {t['start_time'].strftime('%Y-%m-%d %H:%M:%S')}, "
                f"End: {t['end_time'].strftime('%Y-%m-%d %H:%M:%S')}, "
                f"Duration: {t['duration_minutes']}min, "
                f"Desc: \"{t['description']}\", "
                f"{tags_str}"
            )
        click.echo("--- End of Log ---")
    except FileNotFoundError:
        click.echo(f"Log file not found at {LOG_FILE_PATH}. Log some tasks first.", err=True)
    except Exception as e:
        click.echo(f"Error retrieving tasks: {e}", err=True)


if __name__ == '__main__':
    # This is necessary for Click to process commands
    # Ensure LOG_FILE_PATH directory exists before logger is first called
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            # This might happen due to permissions or other issues.
            # TaskLogger also tries to create it, but good to be defensive.
            click.echo(f"Warning: Could not create log directory {log_dir}: {e}", err=True)
    cli()
