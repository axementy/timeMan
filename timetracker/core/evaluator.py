from datetime import date
from collections import defaultdict

# Assuming TaskLogger is in a sibling directory core or accessible via PYTHONPATH
try:
    from timetracker.core.logger import TaskLogger
except ImportError:
    # Fallback for scenarios where the module structure isn't set up as expected
    # This is primarily for development or direct script execution tests
    # A proper package installation should handle this.
    # For this exercise, we assume TaskLogger can be imported.
    # If this were a real package, we'd rely on the Python path being correct.
    # A placeholder for TaskLogger if it cannot be imported, to allow basic class definition.
    class TaskLogger: # pragma: no cover
        def __init__(self, log_file_path: str):
            self.log_file_path = log_file_path
            print(f"Warning: Using placeholder TaskLogger for {self.log_file_path}")

        def get_tasks(self, date_filter=None):
            print(f"Placeholder TaskLogger.get_tasks called with date_filter: {date_filter}")
            return []


class ProductivityEvaluator:
    """
    Evaluates productivity based on tasks logged by a TaskLogger.
    """

    def __init__(self, task_logger: TaskLogger):
        """
        Initializes the ProductivityEvaluator.

        Args:
            task_logger (TaskLogger): An instance of TaskLogger to access task data.
        """
        if not isinstance(task_logger, TaskLogger):
            raise TypeError("task_logger must be an instance of TaskLogger.")
        self.task_logger = task_logger

    def get_total_focused_time(self, target_date: date) -> int:
        """
        Calculates the total focused time for a given date.

        Args:
            target_date (date): The specific date for which to calculate focused time.

        Returns:
            int: Total focused time in minutes for the target_date.
        """
        if not isinstance(target_date, date):
            raise TypeError("target_date must be a datetime.date object.")
            
        tasks_for_date = self.task_logger.get_tasks(date_filter=target_date)
        total_time = 0
        for task in tasks_for_date:
            total_time += task.get('duration_minutes', 0)
        return total_time

    def get_daily_summary(self, target_date: date) -> dict:
        """
        Provides a productivity summary for a given date.

        Args:
            target_date (date): The specific date for which to generate the summary.

        Returns:
            dict: A dictionary containing the summary:
                  {
                      "date": "YYYY-MM-DD",
                      "total_tasks": int,
                      "total_focused_time_minutes": int,
                      "tasks_by_tag": {tag_name: minutes, ...}
                  }
        """
        if not isinstance(target_date, date):
            raise TypeError("target_date must be a datetime.date object.")

        tasks_for_date = self.task_logger.get_tasks(date_filter=target_date)
        
        total_tasks = 0
        total_focused_time_minutes = 0
        tasks_by_tag = defaultdict(int)

        for task in tasks_for_date:
            total_tasks += 1
            duration = task.get('duration_minutes', 0)
            total_focused_time_minutes += duration
            
            tags = task.get('tags', [])
            if isinstance(tags, list): # Ensure tags is a list
                for tag in tags:
                    tasks_by_tag[tag] += duration
        
        return {
            "date": target_date.isoformat(),
            "total_tasks": total_tasks,
            "total_focused_time_minutes": total_focused_time_minutes,
            "tasks_by_tag": dict(tasks_by_tag) # Convert defaultdict to dict for output
        }
