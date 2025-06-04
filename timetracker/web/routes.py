"""
Defines the web routes for the TimeTracker Flask application.

This module includes routes for:
- Basic navigation (home page).
- Pomodoro timer functionality (managing session-based timer state).
- Task management (CRUD operations for tasks).
- Prompting for and saving reports for "big tasks" completed via Pomodoro.
- Viewing daily and weekly activity reports.
- Legacy routes for older logging and reporting features.
"""
from flask import render_template, session, redirect, url_for, current_app, request, flash
import time
import os
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any # For type hints

# Adjust import path for core modules based on project structure
# This assumes routes.py is in timetracker/web/
try:
    from timetracker.core.pomodoro import PomodoroTimer
    from timetracker.core.logger import TaskLogger
    from timetracker.core.evaluator import ProductivityEvaluator # Kept for legacy productivity_report_old
    from timetracker.core.task import Task
except ImportError: # pragma: no cover
    # Fallback for different execution contexts if running script directly
    import sys
    project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root_dir not in sys.path:
        sys.path.insert(0, project_root_dir)
    from timetracker.core.pomodoro import PomodoroTimer
    from timetracker.core.logger import TaskLogger
    from timetracker.core.evaluator import ProductivityEvaluator
    from timetracker.core.task import Task


# --- Global Instances / Configuration ---

# NOTE: The global `pomodoro_timer_instance` is problematic for a web application
# due to shared state across requests/users. The current Pomodoro web routes primarily
# use the Flask session to manage timer state per user. An instance of PomodoroTimer
# is created locally in routes or helpers when its configuration (like durations) is needed.
# This global instance is not actively used by the session-based Pomodoro logic below.
# It might be a remnant from an earlier design or used by other non-web parts if any.
# pomodoro_timer_instance = PomodoroTimer() # Commented out to avoid confusion

# Path for the task log CSV file. Consistent with CLI.
LOG_FILE_PATH = os.path.join("timetracker", "data", "tasks.csv")
# A global TaskLogger instance will be initialized in `init_app_routes`.
task_logger_instance: Optional[TaskLogger] = None


# --- Helper Functions ---

def _parse_datetime_form(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    Parses a datetime string from a form input into a datetime object.

    Supports "YYYY-MM-DDTHH:MM" (from datetime-local input),
    "YYYY-MM-DD HH:MM", and "YYYY-MM-DD" formats.
    If only a date is provided, time defaults to 00:00:00.

    Args:
        datetime_str (Optional[str]): The date/time string to parse.
                                      Can be None or empty.

    Returns:
        Optional[datetime]: A datetime object if parsing is successful,
                            None if the input string is None or empty.
                            Flashes a warning and returns None if parsing fails for a non-empty string.
    """
    if not datetime_str:
        return None
    formats_to_try = [
        "%Y-%m-%dT%H:%M",  # Common format for datetime-local input
        "%Y-%m-%d %H:%M:%S", # Full format
        "%Y-%m-%d %H:%M",   # Format without seconds
        "%Y-%m-%d"          # Date only
    ]
    for fmt in formats_to_try:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    flash(f"Invalid date/time format: '{datetime_str}'. Please use YYYY-MM-DD or YYYY-MM-DD HH:MM.", "warning")
    return None

def _get_latest_tasks(logger: TaskLogger) -> List[Task]:
    """
    Retrieves all unique tasks, prioritizing the latest version of each.

    Fetches all log entries, then processes them to find the most recent
    snapshot or activity log for each unique task ID, based on `updated_at`.
    This function returns all unique tasks, including those marked 'deleted',
    allowing routes to decide on filtering them.

    Args:
        logger (TaskLogger): The TaskLogger instance to use for fetching tasks.

    Returns:
        List[Task]: A list of `Task` objects, each representing the latest known
                    state of a unique task.
    """
    all_task_entries = logger.get_tasks() # Gets Task objects from all log entries
    latest_tasks: Dict[uuid.UUID, Task] = {}
    for task_entry in all_task_entries:
        if task_entry.id not in latest_tasks or task_entry.updated_at > latest_tasks[task_entry.id].updated_at:
            latest_tasks[task_entry.id] = task_entry
    return list(latest_tasks.values())


# --- Pomodoro Session Helper ---
def get_default_pomodoro_state() -> Dict[str, Any]:
    """
    Returns a dictionary representing the initial state for a Pomodoro timer session.
    This is used to initialize or reset the Pomodoro state stored in Flask's session.
    """
    # Uses a temporary PomodoroTimer instance just to get default durations
    default_timer_config = PomodoroTimer()
    return {
        'interval_type': 'work',
        'remaining_seconds': default_timer_config.work_duration,
        'is_running': False,
        'display_until': None,  # Timestamp for client-side countdown target
        'completed_intervals': 0, # Work intervals in the current cycle of 4
        'current_task_id': None,  # ID of task associated with current work interval
        'work_start_time': None,  # ISO format string of when current work interval started
    }

# --- Route Initialization ---
def init_app_routes(app: Flask):
    """
    Initializes and registers all application routes.

    This function is called by the app factory (`create_app`) to set up
    the web endpoints. It also initializes a global `task_logger_instance`
    for use by the routes.

    Args:
        app (Flask): The Flask application instance.
    """
    global task_logger_instance
    task_logger_instance = TaskLogger(LOG_FILE_PATH)

    if not app.secret_key: # pragma: no cover
        # Should be set in create_app, but double-check. Essential for sessions.
        app.logger.warning("Flask app.secret_key is not set! Sessions will not work.")

    # --- Basic Routes ---
    @app.route('/')
    def index() -> str:
        """Renders the home page."""
        return render_template('index.html', title='Home')

    # --- Pomodoro Timer Routes ---
    @app.route('/pomodoro', methods=['GET'])
    def pomodoro() -> str:
        """
        Displays the Pomodoro timer page.

        Initializes Pomodoro state in the session if not already present.
        Fetches available tasks (pending or in-progress) to populate a dropdown
        for associating a task with a work interval.
        """
        if 'pomodoro_state' not in session:
            session['pomodoro_state'] = get_default_pomodoro_state()

        current_pomodoro_state = session['pomodoro_state']
        
        available_tasks = [
            t for t in _get_latest_tasks(task_logger_instance)
            if t.status in ['pending', 'in-progress']
        ]

        return render_template('pomodoro.html', title='Pomodoro Timer',
                               current_state=current_pomodoro_state,
                               available_tasks=available_tasks)

    def _start_interval(interval_type_str: str, task_id: Optional[str] = None) -> None:
        """
        Internal helper to start or transition to a new Pomodoro interval.
        Updates the session with the new interval's state.
        If starting a work interval with a task_id, updates task status to 'in-progress'.
        """
        current_pomodoro_state = session.get('pomodoro_state', get_default_pomodoro_state())
        pomodoro_config = PomodoroTimer() # Temporary instance for duration configuration

        duration: int
        if interval_type_str == 'work':
            duration = pomodoro_config.work_duration
            current_pomodoro_state['work_start_time'] = datetime.now().isoformat()
            current_pomodoro_state['current_task_id'] = task_id
            if task_id: # If a task is associated with this work interval
                task = task_logger_instance.get_task_by_id(task_id)
                if task and task.status == 'pending': # Auto-set to in-progress
                    task.update(status='in-progress')
                    task_logger_instance.save_task_snapshot(task)
                    flash(f"Task '{task.description}' status updated to in-progress.", "info")
        elif interval_type_str == 'short_break':
            duration = pomodoro_config.short_break_duration
            current_pomodoro_state['current_task_id'] = None # No task during breaks
            current_pomodoro_state['work_start_time'] = None
        elif interval_type_str == 'long_break':
            duration = pomodoro_config.long_break_duration
            current_pomodoro_state['current_task_id'] = None
            current_pomodoro_state['work_start_time'] = None
        else: # Should not happen with valid UI calls
            flash("Invalid interval type specified.", "error")
            # No redirect here, as this is an internal helper. Calling route should handle.
            return

        current_pomodoro_state.update({
            'interval_type': interval_type_str,
            'remaining_seconds': duration,
            'is_running': True,
            'display_until': time.time() + duration, # For client-side countdown
        })
        session['pomodoro_state'] = current_pomodoro_state
    
    @app.route('/pomodoro/start_work', methods=['POST'])
    def start_work():
        """Starts a new 'work' interval. Handles optional task_id from form."""
        task_id = request.form.get('task_id') # Get task_id from form submission
        _start_interval('work', task_id if task_id else None)
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/start_short_break', methods=['POST'])
    def start_short_break():
        """Starts a 'short_break' interval."""
        _start_interval('short_break')
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/start_long_break', methods=['POST'])
    def start_long_break():
        """Starts a 'long_break' interval."""
        _start_interval('long_break')
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/pause', methods=['POST'])
    def pause_timer():
        """Pauses the currently running Pomodoro interval."""
        current_pomodoro_state = session.get('pomodoro_state')
        if current_pomodoro_state and current_pomodoro_state['is_running']:
            # Calculate time elapsed based on when it should have ended
            time_left = current_pomodoro_state['display_until'] - time.time()
            current_pomodoro_state['remaining_seconds'] = max(0, int(time_left))
            current_pomodoro_state['is_running'] = False
            current_pomodoro_state['display_until'] = None # Clear target end time
            session['pomodoro_state'] = current_pomodoro_state
            flash("Timer paused.", "info")
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/resume', methods=['POST'])
    def resume_timer():
        """Resumes a paused Pomodoro interval."""
        current_pomodoro_state = session.get('pomodoro_state')
        if current_pomodoro_state and \
           not current_pomodoro_state['is_running'] and \
           current_pomodoro_state['remaining_seconds'] > 0:
            current_pomodoro_state['is_running'] = True
            # Set new display_until based on remaining time
            current_pomodoro_state['display_until'] = time.time() + current_pomodoro_state['remaining_seconds']
            session['pomodoro_state'] = current_pomodoro_state
            flash("Timer resumed.", "info")
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/reset', methods=['POST'])
    def reset_timer():
        """Resets the current interval to its full duration and pauses it."""
        current_pomodoro_state = session.get('pomodoro_state', get_default_pomodoro_state())
        current_interval = current_pomodoro_state.get('interval_type', 'work')
        
        pomodoro_config = PomodoroTimer() # For getting default durations
        duration: int
        if current_interval == 'work':
            duration = pomodoro_config.work_duration
        elif current_interval == 'short_break':
            duration = pomodoro_config.short_break_duration
        elif current_interval == 'long_break':
            duration = pomodoro_config.long_break_duration
        else: # Default to work if type is unknown
            duration = pomodoro_config.work_duration
            current_interval = 'work'

        current_pomodoro_state.update({
            'interval_type': current_interval, # Keep current type
            'remaining_seconds': duration,     # Reset to full duration of current type
            'is_running': False,
            'display_until': None,
            # current_task_id and work_start_time are preserved if just resetting interval timing
        })
        session['pomodoro_state'] = current_pomodoro_state
        flash(f"Timer reset to beginning of {current_interval.replace('_',' ')}.", "info")
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/stop', methods=['POST'])
    def stop_timer():
        """Stops the Pomodoro timer completely, resetting to a default work state."""
        session['pomodoro_state'] = get_default_pomodoro_state() # Resets all state including task
        flash("Timer stopped and reset.", "info")
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/finish_interval', methods=['POST'])
    def finish_interval():
        """
        Handles the completion of a Pomodoro interval (triggered by client-side timer).

        If a work interval for an associated task was completed:
        - Logs the work session.
        - Marks the task as 'completed'.
        - Checks if it was a "big task"; if so, redirects to a report prompting page.

        Transitions to the next logical interval (e.g., work to break, break to work)
        and updates the session state.
        """
        current_pomodoro_state = session.get('pomodoro_state', get_default_pomodoro_state())
        # Use a temp PomodoroTimer to get duration configs and access TaskLogger
        # The task_logger_instance is now global to this routes module.
        pomodoro_logic_helper = PomodoroTimer(task_logger_instance=task_logger_instance)

        task_id_completed = current_pomodoro_state.get('current_task_id')
        work_start_time_iso = current_pomodoro_state.get('work_start_time')
        
        redirect_url = url_for('pomodoro') # Default redirect destination

        if current_pomodoro_state['interval_type'] == 'work':
            if task_id_completed and work_start_time_iso:
                task = task_logger_instance.get_task_by_id(task_id_completed)
                if task:
                    try:
                        work_start_time = datetime.fromisoformat(work_start_time_iso)
                        if task.status != 'completed': # Update status if not already completed
                            task.update(status='completed')

                        task_logger_instance.log_task(task, work_start_time, datetime.now(), tags=["pomodoro_web", "completed"])
                        flash(f"Work session for task '{task.description}' logged as completed.", "success")

                        if task_logger_instance.check_if_big_task_completed(task_id_completed):
                            session['prompt_big_task_report_info'] = {
                                'id': str(task.id),
                                'description': task.description
                            }
                            redirect_url = url_for('prompt_task_report_route', task_id=str(task.id))
                            flash("Congratulations on completing a major task! Please consider writing a brief report.", "info")
                    except Exception as e: # pragma: no cover
                        flash(f"Error processing task completion for {task_id_completed}: {str(e)}", "error")
                        current_app.logger.error(f"Error processing Pomodoro task completion {task_id_completed}: {e}")

            # Update completed work intervals count for cycle tracking
            completed_session_intervals = current_pomodoro_state.get('completed_intervals', 0) + 1
            current_pomodoro_state['completed_intervals'] = completed_session_intervals
            
            # Determine next interval based on completed cycles
            if completed_session_intervals % 4 == 0:
                next_interval = 'long_break'
                next_duration = pomodoro_logic_helper.long_break_duration
            else:
                next_interval = 'short_break'
                next_duration = pomodoro_logic_helper.short_break_duration
        else: # Current interval was a break
            next_interval = 'work'
            next_duration = pomodoro_logic_helper.work_duration

        # Update session for the next interval
        current_pomodoro_state.update({
            'interval_type': next_interval,
            'remaining_seconds': next_duration,
            'is_running': False, # New interval always starts paused, requires user action
            'display_until': None,
            'current_task_id': None, # Clear task for break; for work, user re-selects or it's passed
            'work_start_time': None,
        })
        session['pomodoro_state'] = current_pomodoro_state
        return redirect(redirect_url)

    # --- Task Management Routes ---
    @app.route('/tasks/all')
    def list_all_tasks() -> str:
        """
        Displays a list of all tasks with filtering and sorting capabilities.

        Query Parameters (GET):
            filter_priority (str, optional): Filter tasks by priority number.
            filter_due_time (str, optional): Filter tasks by due date (YYYY-MM-DD).
            filter_type (str, optional): Filter tasks by type (case-insensitive).
            filter_status (str, optional): Filter tasks by status (case-insensitive).
                                           If not provided, 'deleted' tasks are hidden.
            sort_by (str, optional): Field to sort by (e.g., 'priority', 'due_time').
                                     Defaults to 'created_at'.
            order (str, optional): Sort order ('asc' or 'desc'). Defaults to 'asc'.
        """
        filter_priority_str = request.args.get('filter_priority', '')
        filter_due_time_str = request.args.get('filter_due_time', '')
        filter_type = request.args.get('filter_type', '')
        filter_status = request.args.get('filter_status', '')

        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'asc')

        tasks = _get_latest_tasks(task_logger_instance)

        active_filters: Dict[str, Any] = {}
        if filter_priority_str:
            try:
                filter_priority = int(filter_priority_str)
                tasks = [t for t in tasks if t.priority == filter_priority]
                active_filters['priority'] = filter_priority
            except ValueError: # pragma: no cover
                flash("Invalid priority value for filtering.", "warning")

        if filter_due_time_str:
            parsed_date = _parse_datetime_form(filter_due_time_str)
            if parsed_date:
                filter_date_actual = parsed_date.date()
                tasks = [t for t in tasks if t.due_time and t.due_time.date() == filter_date_actual]
                active_filters['due_time'] = filter_date_actual.strftime("%Y-%m-%d")
            # _parse_datetime_form handles flashing error for bad format

        if filter_type:
            tasks = [t for t in tasks if t.type.lower() == filter_type.lower()]
            active_filters['type'] = filter_type

        if filter_status:
            tasks = [t for t in tasks if t.status.lower() == filter_status.lower()]
            active_filters['status'] = filter_status
        else:
            tasks = [t for t in tasks if t.status.lower() != 'deleted']

        reverse_sort = (order == 'desc')

        def get_web_sort_key(task_item: Task):
            """Key function for sorting tasks in web view, handling None values."""
            val = getattr(task_item, sort_by, None)
            if val is None:
                if sort_by == 'due_time': # Nones last for asc, first for desc
                    return (datetime.max if not reverse_sort else datetime.min)
                # For other types, ensure Nones are grouped consistently (e.g., always last or first)
                return (1, None) # Groups Nones after non-None values

            primary_key = val.lower() if isinstance(val, str) else val
            return (0, primary_key) # Groups actual values first

        tasks.sort(key=get_web_sort_key, reverse=reverse_sort)

        return render_template('task_list.html', tasks=tasks, title="All Tasks",
                               sort_by=sort_by, sort_order=order, filters=active_filters,
                               current_filter_priority=filter_priority_str,
                               current_filter_due_time=filter_due_time_str,
                               current_filter_type=filter_type,
                               current_filter_status=filter_status)

    @app.route('/tasks/create', methods=['GET', 'POST'])
    def create_new_task():
        """
        Handles creation of a new task.
        GET: Displays the task creation form.
        POST: Processes form data, creates the task, and redirects to task list.
        """
        if request.method == 'POST':
            description = request.form.get('description')
            priority_str = request.form.get('priority', '2') # Default if not provided
            due_time_str = request.form.get('due_time')
            task_type = request.form.get('type', 'work') # Default if not provided

            if not description: # Basic validation
                flash('Description is required.', 'error')
                return render_template('task_form.html', form_title='Create Task',
                                       form_action=url_for('create_new_task'),
                                       submit_button_text='Create Task', task=request.form) # Pass back form data
            try:
                priority = int(priority_str)
            except ValueError: # pragma: no cover
                flash('Priority must be an integer.', 'error')
                priority = 2 # Fallback default

            due_time = _parse_datetime_form(due_time_str)
            # _parse_datetime_form will flash a message on parsing error.

            new_task = Task(
                description=description,
                priority=priority,
                due_time=due_time,
                type=task_type
            )
            task_logger_instance.save_task_snapshot(new_task)
            flash(f"Task '{new_task.description}' created successfully!", 'success')
            return redirect(url_for('list_all_tasks'))

        # For GET request
        return render_template('task_form.html', form_title='Create Task',
                               form_action=url_for('create_new_task'),
                               submit_button_text='Create Task')

    @app.route('/tasks/edit/<string:task_id>', methods=['GET', 'POST'])
    def edit_existing_task(task_id: str):
        """
        Handles editing of an existing task.
        GET: Displays the task form pre-filled with the task's current details.
        POST: Processes form data, updates the task, and redirects to task list.
        """
        task = task_logger_instance.get_task_by_id(task_id)
        if not task: # pragma: no cover
            flash(f"Task with ID {task_id} not found.", 'error')
            return redirect(url_for('list_all_tasks'))

        if request.method == 'POST':
            description = request.form.get('description')
            priority_str = request.form.get('priority')
            due_time_str = request.form.get('due_time')
            task_type = request.form.get('type')
            status = request.form.get('status')

            if not description: # Basic validation
                flash('Description is required.', 'error')
                return render_template('task_form.html', form_title=f'Edit Task: {task.description}',
                                   task=task, form_action=url_for('edit_existing_task', task_id=task.id),
                                   submit_button_text='Update Task')
            try:
                priority = int(priority_str) if priority_str else task.priority
            except ValueError: # pragma: no cover
                flash('Priority must be an integer.', 'error')
                priority = task.priority # Keep original if parse fails

            # Handle due_time update, including clearing it if an empty string is passed
            parsed_due_time: Optional[datetime]
            if due_time_str is not None: # If due_time field was submitted (even if empty)
                if due_time_str == "":
                    parsed_due_time = None # Clear the due_time
                else:
                    parsed_due_time = _parse_datetime_form(due_time_str)
                    if parsed_due_time is None and due_time_str != "": # Parsing failed for non-empty string
                        # Error flashed by _parse_datetime_form, re-render form
                        return render_template('task_form.html', form_title=f'Edit Task: {task.description}',
                                   task=task, form_action=url_for('edit_existing_task', task_id=task.id),
                                   submit_button_text='Update Task')
            else: # due_time field not in form submission, keep original
                parsed_due_time = task.due_time


            update_data = {
                'description': description,
                'priority': priority,
                'due_time': parsed_due_time,
                'type': task_type if task_type else task.type,
                'status': status if status else task.status
            }
            task.update(**update_data)
            task_logger_instance.save_task_snapshot(task)
            flash(f"Task '{task.description}' updated successfully!", 'success')
            return redirect(url_for('list_all_tasks'))

        # For GET request
        return render_template('task_form.html', form_title=f'Edit Task: {task.description}',
                               task=task, form_action=url_for('edit_existing_task', task_id=task.id),
                               submit_button_text='Update Task')

    @app.route('/tasks/delete/<string:task_id>', methods=['POST'])
    def delete_existing_task(task_id: str):
        """
        Marks a task as 'deleted'.
        This is a soft delete; the task's status is changed to 'deleted'.
        Requires POST request.
        """
        task = task_logger_instance.get_task_by_id(task_id)
        if task:
            task.update(status='deleted')
            task_logger_instance.save_task_snapshot(task)
            flash(f"Task '{task.description}' marked as deleted.", 'success')
        else: # pragma: no cover
            flash(f"Task with ID {task_id} not found.", 'error')
        return redirect(url_for('list_all_tasks'))

    # --- "Big Task" Report Prompt Route ---
    @app.route('/tasks/prompt_report/<string:task_id>', methods=['GET', 'POST'])
    def prompt_task_report_route(task_id: str):
        """
        Handles prompting for and saving a report for a "big task".
        GET: Displays the report form if session indicates a big task was completed.
        POST: Saves the submitted report text.
        """
        report_info = session.get('prompt_big_task_report_info')
        # Validate that the prompt is for the correct task ID
        if not report_info or str(report_info.get('id')) != task_id:
            flash("No pending big task report for this ID, or ID mismatch.", "warning")
            return redirect(url_for('pomodoro')) # Or list_all_tasks

        task = task_logger_instance.get_task_by_id(task_id)
        if not task: # pragma: no cover
            flash(f"Task {task_id} not found for reporting.", "error")
            session.pop('prompt_big_task_report_info', None)
            return redirect(url_for('list_all_tasks'))

        if request.method == 'POST':
            report_text = request.form.get('report_text')
            if not report_text or not report_text.strip():
                flash("Report text cannot be empty.", "error")
                # Pass task_info again for GET-like rendering on error
                return render_template('prompt_task_report.html', title="Task Completion Report", task_info=report_info)

            try:
                total_logged_time = task_logger_instance.get_total_logged_time_for_task(task_id)
                task_logger_instance.save_task_completion_report(task, report_text, total_logged_time)
                flash("Task report saved successfully!", "success")
                session.pop('prompt_big_task_report_info', None)
                return redirect(url_for('pomodoro'))
            except Exception as e: # pragma: no cover
                current_app.logger.error(f"Error saving task report for {task_id}: {e}")
                flash(f"Could not save task report: {str(e)}", "error")
                return redirect(url_for('pomodoro'))

        # For GET request
        # Use task object for most up-to-date details if needed, or session info is fine
        display_task_info = {'id': str(task.id), 'description': task.description}
        return render_template('prompt_task_report.html', title="Task Completion Report", task_info=display_task_info)


    # --- New Reporting Routes ---
    @app.route('/reports', methods=['GET'])
    def reports_main_index() -> str:
        """Displays the main index page for reports, with date pickers."""
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        current_week_end = current_week_start + timedelta(days=6)
        return render_template('reports_index.html', title="Reports",
                               today_date_str=today.isoformat(),
                               current_week_start_str=current_week_start.isoformat(),
                               current_week_end_str=current_week_end.isoformat())

    @app.route('/reports/daily', methods=['GET'])
    def daily_report_view() -> str:
        """
        Displays a daily activity report.
        Accepts 'date' query parameter (YYYY-MM-DD). Defaults to today.
        """
        report_date_str = request.args.get('date')
        report_date_obj: date = date.today()

        if report_date_str:
            parsed_dt = _parse_datetime_form(report_date_str)
            if not parsed_dt:
                # _parse_datetime_form flashes a message for invalid format
                # Default to today if parsing fails or string is invalid
                flash("Invalid date format for daily report. Defaulting to today.", "warning")
            else:
                report_date_obj = parsed_dt.date()

        try:
            report_data = task_logger_instance.generate_daily_report(report_date_obj)
            return render_template('daily_report.html', title=f"Daily Report - {report_date_obj.isoformat()}",
                                   report_data=report_data)
        except Exception as e: # pragma: no cover
            current_app.logger.error(f"Error generating daily report for {report_date_obj.isoformat()}: {e}")
            flash(f"Could not generate daily report: {str(e)}", "error")
            return redirect(url_for('reports_main_index'))

    @app.route('/reports/weekly', methods=['GET'])
    def weekly_report_view() -> str:
        """
        Displays a weekly activity report.
        Accepts 'start_date' and 'end_date' query parameters (YYYY-MM-DD).
        Defaults to the current week (Monday-Sunday).
        """
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        today = date.today()
        default_start_date: date = today - timedelta(days=today.weekday())
        default_end_date: date = default_start_date + timedelta(days=6)

        start_date_obj: date = default_start_date
        if start_date_str:
            parsed_start = _parse_datetime_form(start_date_str)
            if parsed_start: start_date_obj = parsed_start.date()
            else: flash("Invalid start date format. Using default for start date.", "warning")

        end_date_obj: date = default_end_date
        if end_date_str:
            parsed_end = _parse_datetime_form(end_date_str)
            if parsed_end: end_date_obj = parsed_end.date()
            else: flash("Invalid end date format. Using default for end date.", "warning")

        if start_date_obj > end_date_obj: # pragma: no cover
            flash("Start date must be before or same as end date for weekly report.", "error")
            return redirect(url_for('reports_main_index'))

        try:
            report_data = task_logger_instance.generate_weekly_report(start_date_obj, end_date_obj)
            return render_template('weekly_report.html',
                                   title=f"Weekly Report ({start_date_obj.isoformat()} to {end_date_obj.isoformat()})",
                                   report_data=report_data)
        except Exception as e: # pragma: no cover
            current_app.logger.error(f"Error generating weekly report ({start_date_obj} to {end_date_obj}): {e}")
            flash(f"Could not generate weekly report: {str(e)}", "error")
            return redirect(url_for('reports_main_index'))

    # --- Legacy Routes (Originals, for reference or gradual phase-out) ---
    @app.route('/log_task_old', methods=['GET', 'POST'])
    def log_task_old():
        """
        Legacy route for logging simple task entries (description, times, tags).
        NOTE: This route is not fully compatible with the current TaskLogger which
        expects structured Task objects for its main `log_task` method.
        """
        if request.method == 'POST':
            description = request.form.get('description')
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            tags_str = request.form.get('tags', '')

            if not all([description, start_time_str, end_time_str]):
                flash('Description, Start Time, and End Time are required for old log.', 'error')
                return render_template('log_task.html', title='Log Task (Old)', form_data=request.form)

            try:
                start_datetime = _parse_datetime_form(start_time_str)
                end_datetime = _parse_datetime_form(end_time_str)

                if not start_datetime or not end_datetime:
                    return render_template('log_task.html', title='Log Task (Old)', form_data=request.form)

                if end_datetime <= start_datetime: # pragma: no cover
                    flash('End time must be after start time.', 'error')
                    raise ValueError("End time not after start time.")

                # The old logger.log_task took these params directly.
                # The new one requires a Task object. This route is now mainly for reference
                # or would need adaptation to create a dummy Task or use a different logger method.
                flash("This old logging route is for simple, non-Task object entries. "
                      "The main `TaskLogger.log_task` now expects a full Task object. "
                      "This entry will not be processed by the new system correctly without adaptation.", "warning")
                # Example of what one might do for a generic log if TaskLogger had such a method:
                # task_logger_instance.log_generic_event(description, start_datetime, end_datetime, tags_list)
                # For now, it just flashes and redirects.
                return redirect(url_for('log_task_old'))
            except ValueError as e: # pragma: no cover
                 flash(str(e), 'error') # Display specific validation error
                 return render_template('log_task.html', title='Log Task (Old)', form_data=request.form)
            except Exception as e: # pragma: no cover
                current_app.logger.error(f"Error in old log_task: {e}")
                flash(f'An error occurred: {str(e)}', 'error')
                return render_template('log_task.html', title='Log Task (Old)', form_data=request.form)

        return render_template('log_task.html', title='Log Task (Old)')

    @app.route('/view_tasks_old', methods=['GET'])
    def view_tasks_old():
        """
        Legacy route for viewing task log entries.
        Displays data somewhat rawly from the log, reflecting the old data structure.
        The current `TaskLogger.get_tasks()` returns List[Task], so this route adapts
        them to a dictionary structure for the old `view_tasks.html` template.
        """
        filter_date_str = request.args.get('filter_date')
        filter_date_obj: Optional[date] = None

        if filter_date_str:
            parsed_dt = _parse_datetime_form(filter_date_str)
            if parsed_dt: filter_date_obj = parsed_dt.date()
            else: flash('Invalid date format for filtering. Showing all entries.', 'warning')

        display_list = []
        try:
            # TaskLogger.get_tasks returns List[Task] objects, each from a row.
            tasks_from_log = task_logger_instance.get_tasks(date_filter=filter_date_obj)
            if not tasks_from_log:
                 flash('No log entries found for the selected criteria.', 'info')

            # Adapt Task objects to the dictionary structure expected by 'view_tasks.html'
            for task_obj in tasks_from_log:
                # This is a bit of a hack because view_tasks.html expects specific log entry fields
                # not just task attributes. We use task attributes as placeholders.
                # A proper solution would be for get_log_entries to return dicts and use that,
                # or for view_tasks.html to be updated.
                entry_dict = {
                    'description': task_obj.description,
                    'id': str(task_obj.id),
                    'status': task_obj.status,
                    'type': task_obj.type,
                    'priority': task_obj.priority,
                    # These are from the Task object, not necessarily the log_start/end of the activity from that row.
                    # This view is thus showing task states, not activity timings from those rows.
                    'start_time': task_obj.updated_at, # Placeholder using updated_at
                    'end_time': task_obj.updated_at,   # Placeholder
                    'duration_minutes': 0, # Placeholder, as this is not a direct Task attribute
                    'tags': [task_obj.type, task_obj.status], # Example placeholder for tags
                    'due_time': task_obj.due_time,
                }
                display_list.append(entry_dict)

        except FileNotFoundError: # pragma: no cover
            flash('Log file not found. Log some tasks first.', 'warning')
        except Exception as e: # pragma: no cover
            current_app.logger.error(f"Error retrieving tasks for old view: {e}")
            flash(f'An error occurred: {str(e)}', 'error')

        return render_template(
            'view_tasks.html',
            title='View Logged Entries (Old)',
            tasks_list=display_list,
            filter_date_str=filter_date_str if filter_date_str else ''
        )

    @app.route('/productivity_report_old', methods=['GET'])
    def productivity_report_old():
        """
        Legacy route for displaying a productivity report.
        Uses the `ProductivityEvaluator` which may have different logic
        than the new report generation methods in `TaskLogger`.
        """
        report_date_str = request.args.get('report_date')
        report_date_obj: Optional[date] = None
        summary: Optional[Dict[str, Any]] = None

        if report_date_str:
            parsed_dt = _parse_datetime_form(report_date_str)
            if parsed_dt:
                report_date_obj = parsed_dt.date()
            else: # _parse_datetime_form flashes error
                return render_template(
                    'productivity_report.html', title='Productivity Report (Old)',
                    summary=None, report_date_str=report_date_str)

            if report_date_obj:
                try:
                    # ProductivityEvaluator might use a different logger instance or path.
                    # For consistency, it should use the same LOG_FILE_PATH.
                    eval_logger = TaskLogger(log_file_path=LOG_FILE_PATH)
                    evaluator = ProductivityEvaluator(eval_logger)
                    summary = evaluator.get_daily_summary(report_date_obj)
                except FileNotFoundError: # pragma: no cover
                    flash(f'Log file not found. Cannot generate old report for {report_date_str}.', 'warning')
                except Exception as e: # pragma: no cover
                    current_app.logger.error(f"Error generating old productivity report for {report_date_str}: {e}")
                    flash(f'An error occurred generating old report for {report_date_str}.', 'error')

        return render_template(
            'productivity_report.html', title='Productivity Report (Old)',
            summary=summary,
            report_date_str=report_date_str if report_date_str else ''
        )
