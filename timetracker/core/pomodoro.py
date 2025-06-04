"""
Provides the PomodoroTimer class for managing work and break intervals,
with integration for task tracking and logging.
"""
import time
import os # Moved import os to the top
from typing import Optional
from datetime import datetime

from timetracker.core.task import Task
from timetracker.core.logger import TaskLogger

class PomodoroTimer:
    """
    Manages Pomodoro work and break intervals with optional task association.

    This timer handles the cycling between work, short break, and long break
    intervals. It can be linked to a specific task via its ID, allowing for
    automatic logging of task status changes (e.g., to 'in-progress', 'completed')
    and work sessions using a `TaskLogger` instance. It also signals when a
    "big task" (based on logged time) is completed.

    Attributes:
        work_duration (int): Duration of work intervals in seconds.
        short_break_duration (int): Duration of short break intervals in seconds.
        long_break_duration (int): Duration of long break intervals in seconds.
        is_running (bool): True if the timer is currently active (counting down).
        current_task_id (Optional[str]): The ID of the task currently associated
                                         with the work interval.
        task_logger (TaskLogger): Instance used for logging task-related events.

    Private Attributes:
        _current_interval_type (str): Current type of interval ('work', 'short_break', 'long_break').
        _remaining_time (int): Remaining time in seconds for the current interval.
        _completed_work_intervals (int): Count of completed work intervals in the current cycle.
        _current_work_interval_start_time (Optional[datetime]): Start time of the active work interval,
                                                              used for logging duration.
    """
    def __init__(self, work_duration: int = 25, short_break_duration: int = 5, long_break_duration: int = 15,
                 task_logger_instance: Optional[TaskLogger] = None):
        """
        Initializes the PomodoroTimer.

        Args:
            work_duration (int): Duration of a work interval in minutes. Default is 25.
            short_break_duration (int): Duration of a short break in minutes. Default is 5.
            long_break_duration (int): Duration of a long break in minutes. Default is 15.
            task_logger_instance (Optional[TaskLogger]): An instance of `TaskLogger`.
                If `None`, a default `TaskLogger` instance will be created, which
                logs to a predefined path ('timetracker/data/tasks.csv').
        """
        self.work_duration: int = work_duration * 60  # Convert to seconds
        self.short_break_duration: int = short_break_duration * 60
        self.long_break_duration: int = long_break_duration * 60

        self.is_running: bool = False
        self._current_interval_type: str = 'work'  # work, short_break, long_break
        self._remaining_time: int = self.work_duration
        self._completed_work_intervals: int = 0

        self.current_task_id: Optional[str] = None

        if task_logger_instance:
            self.task_logger: TaskLogger = task_logger_instance
        else:
            # Create a default logger if none is provided.
            default_log_path = os.path.join("timetracker", "data", "tasks.csv")
            self.task_logger: TaskLogger = TaskLogger(log_file_path=default_log_path)

        self._current_work_interval_start_time: Optional[datetime] = None

    def start(self, task_id: Optional[str] = None) -> Optional[str]:
        """
        Starts the timer for the current interval.
        If a task_id is provided, associates this Pomodoro session with that task
        and logs its status updates.
        Manages transitions between work, short break, and long break intervals.

        Args:
            task_id: Optional ID of the task to associate with this Pomodoro session.

        Returns:
            Optional[str]: The task_id if a "big task" was just completed, otherwise None.
        """
        newly_completed_big_task_id: Optional[str] = None

        if task_id: # Allow associating a new task_id at the start of any interval if provided
            self.current_task_id = task_id

        if self.is_running:
            # If timer is already running (e.g. called start() again without pause/stop)
            # This might be a no-op or could be an error depending on desired behavior.
            # For now, let's assume it means "continue if paused" or "restart current if already running"
            # The current logic implies start() is called, and if it's already running, it prints and returns.
            # This is fine.
            print("Timer is already running.")
            return None # No new big task completed signal

        self.is_running = True
        current_duration = self._get_current_interval_duration()
        
        # If timer was reset or is starting for the first time for this interval type
        if self._remaining_time == 0 or self._remaining_time == current_duration:
             self._remaining_time = current_duration
             if self._current_interval_type == 'work':
                self._current_work_interval_start_time = datetime.now()
                if self.current_task_id:
                    task_to_start: Optional[Task] = self.task_logger.get_task_by_id(self.current_task_id)
                    if task_to_start and task_to_start.status != 'in-progress':
                        task_to_start.update(status='in-progress')
                        self.task_logger.log_task(task_to_start, self._current_work_interval_start_time,
                                                  self._current_work_interval_start_time,
                                                  tags=["pomodoro", "status_update", "start"])
                        print(f"Task '{task_to_start.description}' status updated to 'in-progress'.")

        interval_display_name = self._current_interval_type.replace('_', ' ').capitalize()
        task_id_info = f"(Task ID: {self.current_task_id})" if self.current_task_id and self._current_interval_type == 'work' else ""
        print(f"{interval_display_name} started for {current_duration // 60} minutes {task_id_info}.")

        while self._remaining_time > 0 and self.is_running:
            try:
                time.sleep(1)
                self._remaining_time -= 1
            except KeyboardInterrupt:
                print("\nTimer interrupted by user.")
                self.pause()
                return None # Interrupted, no big task completed signal

        if not self.is_running: # Timer was paused or stopped externally before finishing naturally
            # print("Timer paused or stopped.") # Can be noisy. Pause() prints "Timer paused."
            return None

        # --- Interval finished naturally ---
        interval_end_time = datetime.now()
        print(f"{interval_display_name} finished.")

        if self._current_interval_type == 'work':
            self._completed_work_intervals += 1
            if self.current_task_id and self._current_work_interval_start_time:
                task_just_worked_on: Optional[Task] = self.task_logger.get_task_by_id(self.current_task_id)
                if task_just_worked_on:
                    # Assuming one Pomodoro means task is 'completed'. This might need adjustment for real-world tasks.
                    task_just_worked_on.update(status='completed')
                    self.task_logger.log_task(task_just_worked_on, self._current_work_interval_start_time,
                                              interval_end_time,
                                              tags=["pomodoro", "work_session", "completed"])
                    print(f"Task '{task_just_worked_on.description}' logged as 'completed'.")

                    # Check if this completed task was a "big task"
                    if self.task_logger.check_if_big_task_completed(self.current_task_id):
                        newly_completed_big_task_id = self.current_task_id
                        # The CLI/caller will handle the prompt.

            # Reset work-specific timers/IDs for the next interval (which will be a break or new work)
            self._current_work_interval_start_time = None
            # self.current_task_id = None # Keep task_id if next is break, for context, or clear if breaks are general.
                                        # Current CLI loop re-passes task_id if starting next work interval.
                                        # For web, session handles this. Let's keep it for now.

            # Transition to next interval type
            if self._completed_work_intervals % 4 == 0:
                self._current_interval_type = 'long_break'
                print("Time for a long break.")
            else:
                self._current_interval_type = 'short_break'
                print("Time for a short break.")
        elif self._current_interval_type in ['short_break', 'long_break']:
            print(f"{self._current_interval_type.replace('_', ' ').capitalize()} finished.")
            self._current_interval_type = 'work' # Transition back to work
            print("Ready for the next work interval.")
        
        self._remaining_time = self._get_current_interval_duration()
        self.is_running = False # Ready for next explicit start command

    def pause(self) -> None:
        """Pauses the current timer."""
        if not self.is_running:
            print("Timer is not running.")
            return
        self.is_running = False
        # Note: _current_work_interval_start_time is preserved during pause
        print("Timer paused.")

    def reset(self) -> None:
        """
        Resets the timer to the beginning of the current interval type.
        Disassociates any currently linked task.
        """
        self.is_running = False
        self._remaining_time = self._get_current_interval_duration()
        self.current_task_id = None # Disassociate task on reset
        self._current_work_interval_start_time = None
        print(f"Timer reset to the beginning of {self._current_interval_type.replace('_', ' ')}. Task unlinked.")

    def stop(self) -> None:
        """
        Stops the timer completely and resets its state.
        Disassociates any currently linked task.
        """
        self.is_running = False
        self._current_interval_type = 'work'
        self._remaining_time = self.work_duration
        self._completed_work_intervals = 0
        self.current_task_id = None # Disassociate task on stop
        self._current_work_interval_start_time = None
        print("Timer stopped and reset. Task unlinked.")

    def _get_current_interval_duration(self) -> int:
        """Helper method to get duration of the current interval type in seconds."""
        if self._current_interval_type == 'work':
            return self.work_duration
        elif self._current_interval_type == 'short_break':
            return self.short_break_duration
        elif self._current_interval_type == 'long_break':
            return self.long_break_duration
        return 0 # Should not happen

    @property
    def remaining_time(self) -> int:
        """Returns the remaining time in the current interval in seconds."""
        return self._remaining_time

    @property
    def current_interval_type(self) -> str:
        """Returns the current interval type (e.g., 'work', 'short_break')."""
        return self._current_interval_type
