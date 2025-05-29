import time

class PomodoroTimer:
    """
    A Pomodoro timer to help manage work and break intervals.
    """
    def __init__(self, work_duration=25, short_break_duration=5, long_break_duration=15):
        """
        Initializes the PomodoroTimer.

        Args:
            work_duration (int): Duration of a work interval in minutes.
            short_break_duration (int): Duration of a short break in minutes.
            long_break_duration (int): Duration of a long break in minutes.
        """
        self.work_duration = work_duration * 60  # Convert to seconds
        self.short_break_duration = short_break_duration * 60  # Convert to seconds
        self.long_break_duration = long_break_duration * 60  # Convert to seconds

        self.is_running = False
        self._current_interval_type = 'work'  # work, short_break, long_break
        self._remaining_time = self.work_duration
        self._completed_work_intervals = 0

    def start(self):
        """
        Starts the timer for the current interval.
        Manages transitions between work, short break, and long break intervals.
        """
        if self.is_running:
            print("Timer is already running.")
            return

        self.is_running = True
        current_duration = self._get_current_interval_duration()
        
        if self._remaining_time == 0 : # If reset was called on a finished timer
             self._remaining_time = current_duration

        print(f"{self._current_interval_type.replace('_', ' ').capitalize()} started for {current_duration // 60} minutes.")

        while self._remaining_time > 0 and self.is_running:
            try:
                time.sleep(1)
                self._remaining_time -= 1
            except KeyboardInterrupt: # Allow manual interruption for now
                print("\nTimer interrupted.")
                self.stop()
                return

        if not self.is_running: # Timer was paused or stopped
            print("Timer paused or stopped.")
            return

        # Interval finished
        if self._current_interval_type == 'work':
            self._completed_work_intervals += 1
            print("Work interval finished.")
            if self._completed_work_intervals % 4 == 0:
                self._current_interval_type = 'long_break'
                print("Start your long break.")
            else:
                self._current_interval_type = 'short_break'
                print("Start your short break.")
        elif self._current_interval_type in ['short_break', 'long_break']:
            print(f"{self._current_interval_type.replace('_', ' ').capitalize()} finished.")
            self._current_interval_type = 'work'
            print("Start your work interval.")
        
        self._remaining_time = self._get_current_interval_duration()
        self.is_running = False # Ready for next start command
        # To auto-start next, call self.start() here, but prompt wants user to call start again.

    def pause(self):
        """Pauses the current timer."""
        if not self.is_running:
            print("Timer is not running.")
            return
        self.is_running = False
        print("Timer paused.")

    def reset(self):
        """Resets the timer to the beginning of the current interval type."""
        self.is_running = False
        self._remaining_time = self._get_current_interval_duration()
        print(f"Timer reset to the beginning of {self._current_interval_type.replace('_', ' ')}.")

    def stop(self):
        """Stops the timer completely and resets its state."""
        self.is_running = False
        self._current_interval_type = 'work'
        self._remaining_time = self.work_duration
        self._completed_work_intervals = 0
        print("Timer stopped and reset.")

    def _get_current_interval_duration(self):
        """Helper method to get duration of the current interval type."""
        if self._current_interval_type == 'work':
            return self.work_duration
        elif self._current_interval_type == 'short_break':
            return self.short_break_duration
        elif self._current_interval_type == 'long_break':
            return self.long_break_duration
        return 0

    @property
    def get_remaining_time(self):
        """Returns the remaining time in the current interval in seconds."""
        return self._remaining_time

    @property
    def get_current_interval_type(self):
        """Returns the current interval type (e.g., 'work', 'short_break')."""
        return self._current_interval_type
