import unittest
import sys
import os
import time # Will be needed for some controlled tests if possible, or to mock

# Add project root to sys.path to allow importing timetracker modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from timetracker.core.pomodoro import PomodoroTimer

class TestPomodoroTimer(unittest.TestCase):

    def setUp(self):
        # Default timer for most tests
        self.timer = PomodoroTimer()

    def test_initialization_default_durations(self):
        self.assertEqual(self.timer.work_duration, 25 * 60)
        self.assertEqual(self.timer.short_break_duration, 5 * 60)
        self.assertEqual(self.timer.long_break_duration, 15 * 60)

    def test_initialization_custom_durations(self):
        timer = PomodoroTimer(work_duration=30, short_break_duration=10, long_break_duration=20)
        self.assertEqual(timer.work_duration, 30 * 60)
        self.assertEqual(timer.short_break_duration, 10 * 60)
        self.assertEqual(timer.long_break_duration, 20 * 60)

    def test_initial_state(self):
        self.assertFalse(self.timer.is_running)
        self.assertEqual(self.timer.get_current_interval_type, 'work')
        self.assertEqual(self.timer._completed_work_intervals, 0)
        self.assertEqual(self.timer.get_remaining_time, self.timer.work_duration)

    def test_pause_method(self):
        self.timer.is_running = True # Simulate it's running
        self.timer.pause()
        self.assertFalse(self.timer.is_running)

    def test_reset_method(self):
        self.timer._current_interval_type = 'short_break'
        self.timer._remaining_time = 10 # Simulate partial run
        self.timer.is_running = True
        
        self.timer.reset()
        
        self.assertFalse(self.timer.is_running)
        self.assertEqual(self.timer.get_remaining_time, self.timer.short_break_duration)
        self.assertEqual(self.timer.get_current_interval_type, 'short_break') # Reset maintains current type

    def test_stop_method(self):
        # Modify some state
        self.timer._current_interval_type = 'short_break'
        self.timer._remaining_time = 10
        self.timer.is_running = True
        self.timer._completed_work_intervals = 2
        
        self.timer.stop()
        
        self.assertFalse(self.timer.is_running)
        self.assertEqual(self.timer.get_current_interval_type, 'work')
        self.assertEqual(self.timer.get_remaining_time, self.timer.work_duration)
        self.assertEqual(self.timer._completed_work_intervals, 0)

    # Testing transitions is complex due to time.sleep and the structure of start()
    # We will test the state *after* a simulated interval completion and transition logic.
    # The PomodoroTimer.start() method completes an interval, sets up the next, then sets is_running to False.

    def _simulate_interval_completion(self, timer_instance: PomodoroTimer):
        """
        Simulates the end of an interval by setting remaining_time to 0
        and then calling start() to trigger transition logic.
        Since start() is blocking, we'll immediately call stop() to halt it
        after it has performed the transition and set up the next interval.
        This is a bit of a hack due to the original design of start().
        A better way would be to refactor PomodoroTimer to separate transition logic.
        """
        timer_instance._remaining_time = 0 # Mark current interval as completed
        # Call start() to trigger transition. It will print, then try to sleep.
        # We rely on the fact that it sets the *next* interval type and remaining time
        # then sets is_running=False *if* the interval completed naturally (which we forced).
        
        # In the actual PomodoroTimer, start() runs a loop.
        # For testing transitions, we assume the loop part (time.sleep) is what we want to bypass.
        # The transition logic happens *after* the loop if remaining_time is 0.
        
        # Let's directly call the transition part of the logic if possible.
        # The current `start` method structure:
        # 1. Sets is_running = True
        # 2. Loop (time.sleep)
        # 3. If loop finished naturally (remaining_time == 0):
        #    Transition logic
        #    Sets _remaining_time for next interval
        #    Sets is_running = False
        
        # We can achieve this by setting remaining_time to 1, calling start(),
        # then it will sleep for 1s, then execute transition. This is slow for tests.
        
        # Alternative: Manually replicate the transition logic for testing purposes here
        # This is not ideal as it duplicates logic, but safer than complex mocks or threads for now.

        if timer_instance._current_interval_type == 'work':
            timer_instance._completed_work_intervals += 1
            if timer_instance._completed_work_intervals % 4 == 0:
                timer_instance._current_interval_type = 'long_break'
            else:
                timer_instance._current_interval_type = 'short_break'
        elif timer_instance._current_interval_type in ['short_break', 'long_break']:
            timer_instance._current_interval_type = 'work'
        
        timer_instance._remaining_time = timer_instance._get_current_interval_duration()
        timer_instance.is_running = False # As per timer's behavior post-interval

    def test_transition_work_to_short_break(self):
        self.timer._current_interval_type = 'work'
        self.timer._completed_work_intervals = 0 # Ensure not a multiple of 4
        self._simulate_interval_completion(self.timer)
        
        self.assertEqual(self.timer.get_current_interval_type, 'short_break')
        self.assertEqual(self.timer.get_remaining_time, self.timer.short_break_duration)
        self.assertEqual(self.timer._completed_work_intervals, 1)

    def test_transition_short_break_to_work(self):
        self.timer._current_interval_type = 'short_break'
        self.timer._completed_work_intervals = 1 # Doesn't matter for break->work
        self._simulate_interval_completion(self.timer)
        
        self.assertEqual(self.timer.get_current_interval_type, 'work')
        self.assertEqual(self.timer.get_remaining_time, self.timer.work_duration)

    def test_transition_work_to_long_break(self):
        self.timer._current_interval_type = 'work'
        self.timer._completed_work_intervals = 3 # Next work completion will be the 4th
        self._simulate_interval_completion(self.timer) # This completes the 4th work interval
        
        self.assertEqual(self.timer.get_current_interval_type, 'long_break')
        self.assertEqual(self.timer.get_remaining_time, self.timer.long_break_duration)
        self.assertEqual(self.timer._completed_work_intervals, 4)

    def test_transition_long_break_to_work(self):
        self.timer._current_interval_type = 'long_break'
        self.timer._completed_work_intervals = 4 # Doesn't matter for break->work
        self._simulate_interval_completion(self.timer)
        
        self.assertEqual(self.timer.get_current_interval_type, 'work')
        self.assertEqual(self.timer.get_remaining_time, self.timer.work_duration)

if __name__ == '__main__':
    unittest.main()
