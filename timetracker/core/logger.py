"""
Handles logging of task states, activities, and generating reports from this data.

The TaskLogger class is central to persisting task information to a CSV file.
It supports logging different types of events:
- Task snapshots: The state of a task at a specific point (e.g., creation, update).
- Task activities: Timed work sessions or other events related to a task.

It also provides methods to retrieve task data and generate summary reports.
"""
import csv
import os
import uuid
from datetime import datetime, date, timedelta # Added timedelta just in case, though not directly used in this file
from typing import List, Optional, Dict, Any

from timetracker.core.task import Task

class TaskLogger:
    """
    Manages logging task definitions and activities to a CSV file.

    This class is responsible for writing task-related events, such as task creation,
    updates (snapshots), and timed work sessions, to a structured CSV file.
    It also provides methods to retrieve these logs, reconstruct Task objects,
    and generate summary reports based on the logged data.

    The CSV file includes both the core attributes of a Task (as per its state
    at the time of logging) and specific attributes for the log entry itself
    (e.g., start/end time of an activity, duration, log-specific tags).
    """
    _CSV_HEADER = [
        "id", "description", "priority", "due_time", "type", "status",
        "created_at", "updated_at",  # Core Task attributes (snapshot of task state)
        "log_start_time", "log_end_time", "log_duration_minutes", "log_tags" # Log entry specific attributes
    ]
    # Defines the standard columns for the CSV log file.
    # - Core Task attributes: Reflect the state of the task at the moment this log entry was made.
    # - Log entry specific attributes: Describe the activity or event being logged (e.g., a work session).
    #   For 'task_snapshot' entries, log_start_time and log_end_time usually match task.updated_at,
    #   and log_duration_minutes is 0.

    def __init__(self, log_file_path: str):
        """
        Initializes the TaskLogger with a specific path for the log file.

        If the directory for the log file does not exist, it will be created.

        Args:
            log_file_path (str): The path to the CSV file where task activities
                                 and snapshots will be logged.
                                 Example: 'timetracker/data/tasks.csv'
        """
        self.log_file_path = log_file_path
        
        # Ensure the directory for the log file exists.
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir: # Check if log_dir is not an empty string (e.g., if path is just 'tasks.csv')
            os.makedirs(log_dir, exist_ok=True)

    def log_task(self, task: Task, start_time: datetime, end_time: datetime,
                 tags: Optional[List[str]] = None) -> None:
        """
        Records a specific timed activity or work session for a given task.

        This method appends a new row to the CSV log file. The row includes a
        snapshot of the task's current attributes (like description, priority, status,
        its own created_at/updated_at) and details of the logged activity itself
        (log_start_time, log_end_time, calculated duration, and log-specific tags).

        Args:
            task (Task): The Task object for which the activity is being logged.
                         Its current state will be recorded.
            start_time (datetime): The wall-clock start time of this specific activity.
            end_time (datetime): The wall-clock end time of this specific activity.
            tags (Optional[List[str]]): A list of tags to associate specifically
                                        with this log entry (e.g., "pomodoro", "meeting").
                                        These are stored in the 'log_tags' column.
        """
        file_exists = os.path.exists(self.log_file_path)
        
        # Calculate duration of the logged activity.
        duration_seconds = (end_time - start_time).total_seconds()
        duration_minutes = int(duration_seconds // 60)

        tags_str = ",".join(tags) if tags else ""
        
        row_data = [
            str(task.id),
            task.description,
            task.priority,
            task.due_time.isoformat() if task.due_time else "",
            task.type,
            task.status,
            task.created_at.isoformat(),
            task.updated_at.isoformat(),
            start_time.isoformat(),
            end_time.isoformat(),
            duration_minutes,
            tags_str
        ]
        
        with open(self.log_file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists or os.path.getsize(self.log_file_path) == 0:
                writer.writerow(self._CSV_HEADER)
            writer.writerow(row_data)

    def _reconstruct_task_from_row(self, row: dict) -> Task:
        """Helper method to reconstruct a Task object from a CSV row."""
        task_id = uuid.UUID(row["id"])
        description = row["description"]
        priority = int(row["priority"])
        due_time_str = row["due_time"]
        due_time = datetime.fromisoformat(due_time_str) if due_time_str else None
        task_type = row["type"]
        status = row["status"]
        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])

        # Create a new Task instance
        # The constructor of Task might set its own created_at/updated_at
        # We are overriding them here with the values from the CSV.
        task = Task(
            description=description,
            priority=priority,
            due_time=due_time,
            type=task_type,
            status=status,
        )
        # Manually set id, created_at, and updated_at to match the record from CSV
        task.id = task_id
        task.created_at = created_at
        task.updated_at = updated_at

        # Note: log_start_time, log_end_time, etc. from the row are not directly
        # part of the reconstructed Task object's persistent attributes as defined in Task class.
        # If needed, they could be added as transient attributes or handled differently.
        return task

    def get_log_entries(self, date_filter: Optional[date] = None,
                        start_date: Optional[date] = None, end_date: Optional[date] = None,
                        entry_type_tag: Optional[str] = None) -> list[dict]:
        """
        Retrieves raw log entries from the CSV file based on specified filters.

        Args:
            date_filter: Specific date to filter entries by (log_start_time).
            start_date: Start of a date range for filtering.
            end_date: End of a date range for filtering.
            entry_type_tag: A specific tag to filter entries by (e.g., "task_snapshot", "pomodoro").

        Returns:
            A list of dictionaries, where each dictionary represents a raw row from the CSV.
        """
        if not os.path.exists(self.log_file_path):
            return []

        log_entries: list[dict] = []
        try:
            with open(self.log_file_path, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or not all(header in reader.fieldnames for header in self._CSV_HEADER):
                    print(f"Log file '{self.log_file_path}' has a mismatched header. Skipping read.")
                    return []

                for row in reader:
                    try:
                        log_start_time_dt = datetime.fromisoformat(row['log_start_time'])
                        log_date = log_start_time_dt.date()

                        # Date filtering
                        if date_filter and log_date != date_filter:
                            continue
                        if start_date and log_date < start_date:
                            continue
                        if end_date and log_date > end_date:
                            continue

                        # Tag filtering
                        if entry_type_tag:
                            tags_in_row = row.get('log_tags', '').split(',')
                            if entry_type_tag not in tags_in_row:
                                continue

                        log_entries.append(row)
                    except ValueError: # Error parsing date in a row
                        print(f"Skipping row with malformed date: {row}")
                        continue
                    except KeyError: # Missing expected key
                        print(f"Skipping row with missing key: {row}")
                        continue
        except Exception as e:
            print(f"Error reading or processing log file '{self.log_file_path}': {e}")
            return []
        return log_entries

    def generate_daily_report(self, report_date: date) -> dict:
        """Generates a report for a specific day."""
        report = {
            'report_date': report_date.isoformat(),
            'total_tasks_completed_on_date': 0,
            'total_time_spent_minutes': 0,
            'time_spent_by_type': {}, # e.g. {'work': 60, 'personal': 30}
            'tasks_worked_on_details': [], # List of Task objects or dicts with their details
            'completed_tasks_details': [] # List of Task objects or dicts for tasks marked completed
        }

        all_entries_for_date = self.get_log_entries(date_filter=report_date)

        tasks_completed_ids = set()
        tasks_worked_on_ids = set()

        for entry in all_entries_for_date:
            # Time tracking from non-snapshot entries with duration
            duration_minutes = int(entry.get('log_duration_minutes', 0))
            is_snapshot = 'task_snapshot' in entry.get('log_tags', '')

            if not is_snapshot and duration_minutes > 0:
                report['total_time_spent_minutes'] += duration_minutes
                task_id = entry.get('id')
                if task_id:
                    tasks_worked_on_ids.add(task_id)
                    # Fetch task details for type breakdown
                    task_details = self.get_task_by_id(task_id) # Fetches latest state
                    if task_details:
                        task_type = task_details.type
                        report['time_spent_by_type'][task_type] = \
                            report['time_spent_by_type'].get(task_type, 0) + duration_minutes

            # Identify tasks marked as completed on this date
            if is_snapshot and entry.get('status') == 'completed':
                task_id = entry.get('id')
                if task_id:
                    # Ensure the snapshot's "updated_at" (which is log_start_time for snapshots) is on report_date
                    # This is already guaranteed by get_log_entries(date_filter=report_date)
                    tasks_completed_ids.add(task_id)

        report['total_tasks_completed_on_date'] = len(tasks_completed_ids)

        for task_id_str in tasks_completed_ids:
            task = self.get_task_by_id(task_id_str)
            if task:
                report['completed_tasks_details'].append(self._task_to_dict_summary(task))

        for task_id_str in tasks_worked_on_ids:
            task = self.get_task_by_id(task_id_str)
            if task:
                 # Avoid duplicates if a task was both worked on and completed
                if task_id_str not in tasks_completed_ids or \
                   not any(d['id'] == task_id_str for d in report['completed_tasks_details']):
                    report['tasks_worked_on_details'].append(self._task_to_dict_summary(task))

        # If a task was worked on AND completed, ensure it's listed appropriately
        # The current logic might list it in both. This could be fine.
        # For tasks_worked_on_details, we could refine to only include those not in completed_tasks_details.
        # For now, let's keep it simple. User can see status.

        return report

    def generate_weekly_report(self, start_date: date, end_date: date) -> dict:
        """Generates a report for a specific week (inclusive date range)."""
        report = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_days': (end_date - start_date).days + 1,
            'total_tasks_completed_in_week': 0,
            'total_time_spent_minutes': 0,
            'time_spent_by_type': {},
            'tasks_worked_on_or_completed_details': [], # Combined list for simplicity
            'daily_averages': {}
        }

        all_entries_for_week = self.get_log_entries(start_date=start_date, end_date=end_date)

        tasks_completed_in_week_ids = set()
        tasks_worked_on_in_week_ids = set()

        for entry in all_entries_for_week:
            duration_minutes = int(entry.get('log_duration_minutes', 0))
            is_snapshot = 'task_snapshot' in entry.get('log_tags', '')

            if not is_snapshot and duration_minutes > 0:
                report['total_time_spent_minutes'] += duration_minutes
                task_id = entry.get('id')
                if task_id:
                    tasks_worked_on_in_week_ids.add(task_id)
                    task_details = self.get_task_by_id(task_id)
                    if task_details:
                        task_type = task_details.type
                        report['time_spent_by_type'][task_type] = \
                            report['time_spent_by_type'].get(task_type, 0) + duration_minutes

            if is_snapshot and entry.get('status') == 'completed':
                 # Check if snapshot's log_start_time (updated_at for task) is within the week
                entry_date = datetime.fromisoformat(entry['log_start_time']).date()
                if start_date <= entry_date <= end_date:
                    tasks_completed_in_week_ids.add(entry.get('id'))

        report['total_tasks_completed_in_week'] = len(tasks_completed_in_week_ids)

        combined_ids = tasks_worked_on_in_week_ids.union(tasks_completed_in_week_ids)
        for task_id_str in combined_ids:
            task = self.get_task_by_id(task_id_str)
            if task:
                report['tasks_worked_on_or_completed_details'].append(self._task_to_dict_summary(task))

        if report['total_days'] > 0:
            report['daily_averages'] = {
                'avg_tasks_completed_per_day': round(report['total_tasks_completed_in_week'] / report['total_days'], 2),
                'avg_time_spent_minutes_per_day': round(report['total_time_spent_minutes'] / report['total_days'], 2)
            }
        return report

    def _task_to_dict_summary(self, task: Task) -> dict:
        """Helper to convert a Task object to a dictionary summary."""
        return {
            "id": str(task.id),
            "description": task.description,
            "priority": task.priority,
            "due_time": task.due_time.isoformat() if task.due_time else None,
            "type": task.type,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        }

    def get_total_logged_time_for_task(self, task_id_str: str) -> int:
        """Calculates the total logged work time for a specific task."""
        total_minutes = 0
        # Ensure task_id_str is a string for comparison with CSV string IDs
        # UUID objects might be passed, so convert.
        task_id_to_match = str(task_id_str)

        # We need to fetch all log entries, not just for a specific date/tag here.
        # This might be inefficient if the log is huge. Consider optimizing if needed.
        all_log_entries = self.get_log_entries()

        for entry in all_log_entries:
            entry_task_id = entry.get('id')
            if entry_task_id == task_id_to_match:
                is_snapshot = 'task_snapshot' in entry.get('log_tags', '')
                if not is_snapshot:
                    try:
                        duration = int(entry.get('log_duration_minutes', 0))
                        if duration > 0:
                            total_minutes += duration
                    except ValueError:
                        # Log or handle malformed duration in CSV
                        print(f"Warning: Malformed duration for entry related to task ID {entry_task_id}")
                        pass
        return total_minutes

    def check_if_big_task_completed(self, task_id_str: str, threshold_minutes: int = 120) -> bool:
        """Checks if a task is completed and has logged time exceeding a threshold."""
        task = self.get_task_by_id(task_id_str) # get_task_by_id returns latest Task object
        if not task or task.status != 'completed':
            return False

        total_logged_time = self.get_total_logged_time_for_task(task_id_str)
        return total_logged_time >= threshold_minutes

    def save_task_completion_report(self, task: Task, report_text: str, total_logged_time_minutes: int) -> None:
        """Saves a textual report/summary for a completed task to a markdown file."""
        reports_dir = os.path.join("timetracker", "data")
        reports_file_path = os.path.join(reports_dir, "task_reports.md")

        os.makedirs(reports_dir, exist_ok=True)

        hours = total_logged_time_minutes // 60
        minutes = total_logged_time_minutes % 60
        logged_time_str = f"{hours} hours {minutes} minutes"

        report_content = (
            f"## Task Report: {task.id} - {task.description}\n"
            f"**Completed On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Status:** {task.status}\n"
            f"**Priority:** {task.priority}, **Type:** {task.type}\n"
            f"**Originally Due:** {task.due_time.strftime('%Y-%m-%d %H:%M') if task.due_time else 'N/A'}\n"
            f"**Total Logged Time:** {logged_time_str}\n\n"
            f"### Summary/Notes:\n{report_text}\n\n"
            f"---\n\n"
        )

        try:
            with open(reports_file_path, "a", encoding="utf-8") as f:
                f.write(report_content)
            print(f"Report for task {task.id} saved to {reports_file_path}")
        except IOError as e:
            print(f"Error saving task report: {e}")


    def save_task_snapshot(self, task: Task) -> None:
        """
        Saves the current state of a Task object to the CSV log file.
        This is used for logging task creation or explicit updates to its definition.
        The log entry will use the task's updated_at as the log time, with zero duration.
        """
        file_exists = os.path.exists(self.log_file_path)

        # Use task.updated_at for log_start_time and log_end_time for a snapshot
        log_time_iso = task.updated_at.isoformat()

        row_data = [
            str(task.id),
            task.description,
            task.priority,
            task.due_time.isoformat() if task.due_time else "",
            task.type,
            task.status,
            task.created_at.isoformat(),
            task.updated_at.isoformat(),
            log_time_iso,  # log_start_time
            log_time_iso,  # log_end_time
            0,             # log_duration_minutes
            "task_snapshot" # log_tags
        ]

        with open(self.log_file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists or os.path.getsize(self.log_file_path) == 0:
                writer.writerow(self._CSV_HEADER)
            writer.writerow(row_data)


    def get_tasks(self, date_filter: Optional[date] = None) -> List[Task]:
        """
        Reads task activity logs from the CSV file and reconstructs Task objects.
        If multiple log entries exist for the same task ID, each will be reconstructed as a
        Task object reflecting its state at the time of that log. For a unique list of tasks,
        further processing (e.g., keeping only the latest entry per ID) would be needed.

        Args:
            date_filter: If provided, returns only tasks whose 'log_start_time'
                         (the start of the logged activity) falls on this specific date.

        Returns:
            A list of Task objects. Returns an empty list if the log file doesn't exist or is empty.
        """
        if not os.path.exists(self.log_file_path):
            return []

        tasks: List[Task] = []
        try:
            with open(self.log_file_path, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or not all(header in reader.fieldnames for header in self._CSV_HEADER):
                    print(f"Log file '{self.log_file_path}' has a mismatched header. Expected: {self._CSV_HEADER}, Got: {reader.fieldnames}")
                    return []

                for row in reader:
                    try:
                        if date_filter:
                            log_start_time_dt = datetime.fromisoformat(row['log_start_time'])
                            if log_start_time_dt.date() != date_filter:
                                continue

                        task = self._reconstruct_task_from_row(row)
                        tasks.append(task)
                    except ValueError as e:
                        print(f"Skipping malformed row: {row} - Error: {e}")
                        continue
                    except KeyError as e:
                        print(f"Skipping row with missing key: {row} - Error: {e}")
                        continue
        except FileNotFoundError:
            return [] # Should be caught by os.path.exists, but as a safeguard
        except Exception as e: # Catch other potential errors like empty file, permissions
            print(f"Error reading log file '{self.log_file_path}': {e}")
            return []
        return tasks

    def get_tasks_by_priority(self, priority: int) -> List[Task]:
        """Retrieves tasks filtered by priority."""
        all_tasks = self.get_tasks()
        return [task for task in all_tasks if task.priority == priority]

    def get_tasks_by_due_time(self, due_time: datetime) -> List[Task]:
        """Retrieves tasks filtered by an exact due date and time."""
        all_tasks = self.get_tasks()
        return [task for task in all_tasks if task.due_time == due_time]

    def get_tasks_by_type(self, task_type: str) -> List[Task]:
        """Retrieves tasks filtered by type."""
        all_tasks = self.get_tasks()
        return [task for task in all_tasks if task.type.lower() == task_type.lower()]

    def get_task_by_id(self, task_id_str: str) -> Optional[Task]:
        """
        Retrieves a task by its ID.
        Since multiple log entries can exist for the same task ID, this will return the
        one from the latest log entry (latest updated_at).
        If you need the task as per its latest logged activity (log_end_time),
        additional sorting would be required before picking.
        For simplicity, this currently returns the first one found or the one with latest updated_at.
        Let's refine to return the one with the most recent 'updated_at' timestamp from the CSV.
        """
        try:
            target_uuid = uuid.UUID(task_id_str)
        except ValueError:
            print(f"Invalid task ID format: {task_id_str}")
            return None

        all_tasks = self.get_tasks()

        candidate_tasks = [task for task in all_tasks if task.id == target_uuid]
        if not candidate_tasks:
            return None

        # Return the one with the most recent updated_at timestamp
        candidate_tasks.sort(key=lambda t: t.updated_at, reverse=True)
        return candidate_tasks[0]
