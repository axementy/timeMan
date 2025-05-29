import csv
import os
from datetime import datetime, date

class TaskLogger:
    """
    Logs completed tasks to a CSV file and allows retrieval of tasks.
    """
    _CSV_HEADER = ["start_time", "end_time", "duration_minutes", "description", "tags"]

    def __init__(self, log_file_path: str):
        """
        Initializes the TaskLogger.

        Args:
            log_file_path (str): The path to the CSV file where tasks will be logged.
                                 Example: 'timetracker/data/tasks.csv'
        """
        self.log_file_path = log_file_path
        
        # Ensure the directory for the log file exists
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir: # Check if log_dir is not an empty string (e.g. if path is just 'tasks.csv')
            os.makedirs(log_dir, exist_ok=True)

    def log_task(self, task_description: str, start_time: datetime, end_time: datetime, 
                 duration_minutes: int, tags: list = None):
        """
        Records a completed task to the CSV log file.

        Args:
            task_description (str): A description of the task.
            start_time (datetime): The time the task started.
            end_time (datetime): The time the task ended.
            duration_minutes (int): The duration of the task in minutes.
            tags (list, optional): A list of tags associated with the task. Defaults to None.
        """
        file_exists = os.path.exists(self.log_file_path)
        
        # Prepare data for CSV
        start_time_iso = start_time.isoformat()
        end_time_iso = end_time.isoformat()
        tags_str = ",".join(tags) if tags else ""
        
        row_data = [start_time_iso, end_time_iso, duration_minutes, task_description, tags_str]
        
        with open(self.log_file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header if file is new or empty
            if not file_exists or os.path.getsize(self.log_file_path) == 0:
                writer.writerow(self._CSV_HEADER)
            writer.writerow(row_data)

    def get_tasks(self, date_filter: date = None) -> list:
        """
        Reads tasks from the log file.

        Args:
            date_filter (date, optional): If provided, returns only tasks that started
                                          on this specific date. Defaults to None.

        Returns:
            list: A list of dictionaries, where each dictionary represents a task.
                  Returns an empty list if the log file doesn't exist or is empty.
        """
        if not os.path.exists(self.log_file_path):
            return []

        tasks = []
        with open(self.log_file_path, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Perform date filtering if a filter is provided
                    if date_filter:
                        start_time_dt = datetime.fromisoformat(row['start_time'])
                        if start_time_dt.date() != date_filter:
                            continue
                    
                    # Convert types for the output dictionary
                    task = {
                        'start_time': datetime.fromisoformat(row['start_time']),
                        'end_time': datetime.fromisoformat(row['end_time']),
                        'duration_minutes': int(row['duration_minutes']),
                        'description': row['description'],
                        'tags': row['tags'].split(',') if row['tags'] else []
                    }
                    tasks.append(task)
                except ValueError as e:
                    # Handle potential errors in row data, e.g. malformed date
                    print(f"Skipping malformed row: {row} - Error: {e}")
                    continue
                except KeyError as e:
                    # Handle rows that don't match the expected header
                    print(f"Skipping row with missing key: {row} - Error: {e}")
                    continue
        return tasks
