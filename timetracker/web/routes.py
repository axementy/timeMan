from flask import render_template, session, redirect, url_for, current_app, request, flash
import time
import os
from datetime import datetime

# Adjust import path for core modules based on project structure
# This assumes routes.py is in timetracker/web/
try:
    from timetracker.core.pomodoro import PomodoroTimer
    from timetracker.core.logger import TaskLogger
    from timetracker.core.evaluator import ProductivityEvaluator
except ImportError:
    # Fallback for different execution contexts
    import sys
    project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root_dir not in sys.path:
        sys.path.insert(0, project_root_dir)
    from timetracker.core.pomodoro import PomodoroTimer
    from timetracker.core.logger import TaskLogger
    from timetracker.core.evaluator import ProductivityEvaluator


# --- Global Instances / Configuration ---
# Pomodoro timer instance (as per previous setup)
pomodoro_timer_instance = PomodoroTimer() 

# Path for the task log file
# Consistent with CLI setup and TaskLogger's expectation if run from project root
LOG_FILE_PATH = os.path.join("timetracker", "data", "tasks.csv")


# --- Pomodoro Helper ---
def get_default_pomodoro_state():
    pomodoro_timer_instance.stop() # Reset the timer to its initial 'work' state
    return {
        'interval_type': pomodoro_timer_instance.get_current_interval_type,
        'remaining_seconds': pomodoro_timer_instance.get_remaining_time,
        'is_running': False,
        'display_until': None, # Target timestamp for countdown
        'completed_intervals': pomodoro_timer_instance._completed_work_intervals
    }

def init_app_routes(app):
    # Ensure app.secret_key is set (should be in app.py, but good to be aware)
    if not app.secret_key: # pragma: no cover
        app.logger.warning("Flask app.secret_key is not set! Session will not work.")


    # --- Basic Routes ---
    @app.route('/')
    def index():
        return render_template('index.html', title='Home')

    # --- Pomodoro Routes ---
    @app.route('/pomodoro', methods=['GET'])
    def pomodoro():
        if 'pomodoro_state' not in session:
            session['pomodoro_state'] = get_default_pomodoro_state()
        current_pomodoro_state = session['pomodoro_state']
        return render_template('pomodoro.html', title='Pomodoro Timer', current_state=current_pomodoro_state)

    def _start_interval(interval_type_str):
        # Logic to start/resume an interval, updating session
        current_pomodoro_state = session.get('pomodoro_state', get_default_pomodoro_state())
        
        # Determine duration based on interval type
        if interval_type_str == 'work':
            # Reset completed intervals if starting fresh after a break cycle
            if current_pomodoro_state['interval_type'] != 'work':
                 pomodoro_timer_instance._current_interval_type = 'work' # Set the type
            duration = pomodoro_timer_instance.work_duration
        elif interval_type_str == 'short_break':
            pomodoro_timer_instance._current_interval_type = 'short_break'
            duration = pomodoro_timer_instance.short_break_duration
        elif interval_type_str == 'long_break':
            pomodoro_timer_instance._current_interval_type = 'long_break'
            duration = pomodoro_timer_instance.long_break_duration
        else: # Should not happen with fixed buttons
            flash("Invalid interval type.", "error")
            return redirect(url_for('pomodoro'))

        current_pomodoro_state.update({
            'interval_type': interval_type_str,
            'remaining_seconds': duration,
            'is_running': True,
            'display_until': time.time() + duration,
            # 'completed_intervals' is updated by finish_interval
        })
        session['pomodoro_state'] = current_pomodoro_state
    
    @app.route('/pomodoro/start_work', methods=['POST'])
    def start_work():
        _start_interval('work')
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/start_short_break', methods=['POST'])
    def start_short_break():
        _start_interval('short_break')
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/start_long_break', methods=['POST'])
    def start_long_break():
        _start_interval('long_break')
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/pause', methods=['POST'])
    def pause_timer():
        current_pomodoro_state = session.get('pomodoro_state')
        if current_pomodoro_state and current_pomodoro_state['is_running']:
            # Calculate remaining time based on display_until
            new_remaining = current_pomodoro_state['display_until'] - time.time()
            current_pomodoro_state['remaining_seconds'] = max(0, int(new_remaining))
            current_pomodoro_state['is_running'] = False
            current_pomodoro_state['display_until'] = None 
            session['pomodoro_state'] = current_pomodoro_state
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/resume', methods=['POST'])
    def resume_timer():
        current_pomodoro_state = session.get('pomodoro_state')
        if current_pomodoro_state and not current_pomodoro_state['is_running'] and current_pomodoro_state['remaining_seconds'] > 0:
            current_pomodoro_state['is_running'] = True
            current_pomodoro_state['display_until'] = time.time() + current_pomodoro_state['remaining_seconds']
            session['pomodoro_state'] = current_pomodoro_state
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/reset', methods=['POST'])
    def reset_timer():
        current_pomodoro_state = session.get('pomodoro_state', get_default_pomodoro_state())
        current_interval = current_pomodoro_state.get('interval_type', 'work')
        
        if current_interval == 'work':
            duration = pomodoro_timer_instance.work_duration
        elif current_interval == 'short_break':
            duration = pomodoro_timer_instance.short_break_duration
        elif current_interval == 'long_break':
            duration = pomodoro_timer_instance.long_break_duration
        else:
            duration = pomodoro_timer_instance.work_duration
            current_interval = 'work'

        current_pomodoro_state.update({
            'interval_type': current_interval,
            'remaining_seconds': duration,
            'is_running': False,
            'display_until': None,
        })
        session['pomodoro_state'] = current_pomodoro_state
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/stop', methods=['POST'])
    def stop_timer():
        session['pomodoro_state'] = get_default_pomodoro_state()
        return redirect(url_for('pomodoro'))

    @app.route('/pomodoro/finish_interval', methods=['POST'])
    def finish_interval():
        current_pomodoro_state = session.get('pomodoro_state', get_default_pomodoro_state())
        
        if current_pomodoro_state['interval_type'] == 'work':
            # Use the global pomodoro_timer_instance to track completed cycles across sessions if desired,
            # or store completed_intervals in session and manage it carefully.
            # For simplicity with current setup, let's use session for completed_intervals
            completed_session_intervals = current_pomodoro_state.get('completed_intervals', 0) + 1
            current_pomodoro_state['completed_intervals'] = completed_session_intervals
            
            if completed_session_intervals % 4 == 0:
                next_interval = 'long_break'
                next_duration = pomodoro_timer_instance.long_break_duration
            else:
                next_interval = 'short_break'
                next_duration = pomodoro_timer_instance.short_break_duration
        else: 
            next_interval = 'work'
            next_duration = pomodoro_timer_instance.work_duration

        current_pomodoro_state.update({
            'interval_type': next_interval,
            'remaining_seconds': next_duration,
            'is_running': False, 
            'display_until': None,
        })
        session['pomodoro_state'] = current_pomodoro_state
        return redirect(url_for('pomodoro'))

    # --- Task Logging Routes ---
    @app.route('/log_task', methods=['GET', 'POST'])
    def log_task():
        if request.method == 'POST':
            description = request.form.get('description')
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            duration_str = request.form.get('duration_minutes')
            tags_str = request.form.get('tags', '') # Default to empty string if not provided

            # Validate required fields
            if not all([description, start_time_str, end_time_str, duration_str]):
                flash('All fields except Tags are required.', 'error')
                return render_template('log_task.html', title='Log Task', form_data=request.form)

            try:
                # Convert and validate data types
                start_datetime = datetime.fromisoformat(start_time_str)
                end_datetime = datetime.fromisoformat(end_time_str)
                duration_int = int(duration_str)

                if duration_int <= 0:
                    flash('Duration must be a positive number of minutes.', 'error')
                    raise ValueError("Duration not positive.")

                if end_datetime <= start_datetime:
                    flash('End time must be after start time.', 'error')
                    raise ValueError("End time not after start time.")
                
                # Further check if provided duration matches start/end time diff (approx)
                calculated_duration = (end_datetime - start_datetime).total_seconds() / 60
                if abs(calculated_duration - duration_int) > 1: # Allow 1 min difference for rounding
                    flash(f'Warning: Provided duration ({duration_int} min) differs from calculated duration based on start/end times ({calculated_duration:.0f} min). Using provided duration.', 'warning')

            except ValueError as e:
                current_app.logger.error(f"Validation error: {e} - Data: {request.form}")
                flash('Invalid data format. Please check times and duration.', 'error')
                return render_template('log_task.html', title='Log Task', form_data=request.form)

            tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            
            try:
                logger = TaskLogger(log_file_path=LOG_FILE_PATH)
                logger.log_task(
                    task_description=description,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    duration_minutes=duration_int,
                    tags=tags_list
                )
                flash('Task logged successfully!', 'success')
                return redirect(url_for('log_task')) # Redirect to clear form on success
            except Exception as e: # Catch any other error during logging
                current_app.logger.error(f"Error logging task: {e}")
                flash(f'An error occurred while logging the task: {e}', 'error')
                return render_template('log_task.html', title='Log Task', form_data=request.form)
        
        # For GET request
        return render_template('log_task.html', title='Log Task')

    # --- View Tasks Routes ---
    @app.route('/tasks', methods=['GET'])
    def view_tasks():
        filter_date_str = request.args.get('filter_date') # Comes from <input type="date"> as YYYY-MM-DD
        filter_date_obj = None
        tasks_list = []

        if filter_date_str:
            try:
                filter_date_obj = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
                # Optionally, one might choose to not load any tasks if date is invalid,
                # or load all tasks. For now, let's proceed as if no filter was applied
                # but the invalid string will be passed back to pre-fill the form.
                filter_date_str = filter_date_str # Keep it to show back to user
                filter_date_obj = None # Ensure it's None so all tasks are fetched or none if that's desired

        try:
            logger = TaskLogger(log_file_path=LOG_FILE_PATH)
            # get_tasks will handle filter_date_obj being None (to fetch all tasks)
            tasks_list = logger.get_tasks(date_filter=filter_date_obj)
        except FileNotFoundError:
            flash('Log file not found. Log some tasks first.', 'warning')
        except Exception as e:
            current_app.logger.error(f"Error retrieving tasks: {e}")
            flash(f'An error occurred while retrieving tasks: {e}', 'error')
            tasks_list = [] # Ensure tasks_list is empty on error

        return render_template(
            'view_tasks.html',
            title='View Tasks',
            tasks_list=tasks_list,
            filter_date_str=filter_date_str if filter_date_str else '' # Pass for pre-filling form
        )

    # --- Productivity Report Routes ---
    @app.route('/productivity_report', methods=['GET'])
    def productivity_report():
        report_date_str = request.args.get('report_date') # From <input type="date"> as YYYY-MM-DD
        report_date_obj = None
        summary = None

        if report_date_str:
            try:
                report_date_obj = datetime.strptime(report_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
                # Render template without summary, but with the invalid date string to pre-fill form
                return render_template(
                    'productivity_report.html',
                    title='Productivity Report',
                    summary=None,
                    report_date_str=report_date_str
                )

            # If date is valid, proceed to get summary
            try:
                task_logger = TaskLogger(log_file_path=LOG_FILE_PATH)
                evaluator = ProductivityEvaluator(task_logger)
                summary = evaluator.get_daily_summary(report_date_obj)
                # get_daily_summary returns a dict with zeroed values if no tasks,
                # so summary will not be None here unless an exception occurs in ProductivityEvaluator
            except FileNotFoundError:
                flash(f'Log file not found. Cannot generate report for {report_date_str}.', 'warning')
                summary = None # Ensure summary is None if log file missing
            except Exception as e:
                current_app.logger.error(f"Error generating productivity report for {report_date_str}: {e}")
                flash(f'An error occurred while generating the report for {report_date_str}.', 'error')
                summary = None # Ensure summary is None on error

        # For GET request without a date, or after processing (summary might be None or populated)
        return render_template(
            'productivity_report.html',
            title='Productivity Report',
            summary=summary,
            report_date_str=report_date_str if report_date_str else '' # For pre-filling form
        )
