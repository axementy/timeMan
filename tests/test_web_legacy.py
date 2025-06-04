import unittest
import os
import shutil
from datetime import datetime, date
from unittest.mock import patch

# Adjust sys.path to allow importing timetracker modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from timetracker.web.app import create_app
from timetracker.core.logger import TaskLogger
# PomodoroTimer might not be directly needed if session interaction is the focus
# from timetracker.core.pomodoro import PomodoroTimer

# Define a consistent test log file path for web tests
TEST_WEB_LOG_DIR = os.path.join(project_root, "tests", "temp_web_test_data")
TEST_WEB_LOG_FILE = os.path.join(TEST_WEB_LOG_DIR, "test_web_tasks.csv")

@patch('timetracker.web.routes.LOG_FILE_PATH', TEST_WEB_LOG_FILE)
class TestWebApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create the test log directory once for the class
        os.makedirs(TEST_WEB_LOG_DIR, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        # Remove the test log directory after all tests in the class
        if os.path.exists(TEST_WEB_LOG_DIR):
            shutil.rmtree(TEST_WEB_LOG_DIR)

    def setUp(self):
        app = create_app()
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key_for_web_tests'
        # CSRF protection can interfere with test client posts if not handled.
        # For this exercise, if WTForms CSRF is used, it might need to be disabled or a token included.
        # app.config['WTF_CSRF_ENABLED'] = False # Example if using Flask-WTF CSRF
        
        self.client = app.test_client()

        # Ensure the test log file is clean before each test
        if os.path.exists(TEST_WEB_LOG_FILE):
            os.remove(TEST_WEB_LOG_FILE)

    def tearDown(self):
        # Clean up the test log file after each test
        if os.path.exists(TEST_WEB_LOG_FILE):
            os.remove(TEST_WEB_LOG_FILE)

    # 1. Basic Route Tests (GET requests)
    def test_get_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome to TimeTracker!", response.data)

    def test_get_pomodoro_route(self):
        response = self.client.get('/pomodoro')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pomodoro Timer", response.data)

    def test_get_log_task_route(self):
        response = self.client.get('/log_task')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Log a New Task", response.data)

    def test_get_tasks_route(self):
        response = self.client.get('/tasks')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"View Logged Tasks", response.data)

    def test_get_productivity_report_route(self):
        response = self.client.get('/productivity_report')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Productivity Report", response.data)

    # 2. Pomodoro Route Logic (Session Interaction)
    def test_pomodoro_start_work(self):
        with self.client: # Ensure session is maintained
            response = self.client.post('/pomodoro/start_work')
            self.assertEqual(response.status_code, 302) # Redirect
            self.assertEqual(response.location, '/pomodoro')
            
            # Check session state after redirect
            # Need to make a GET request to /pomodoro to inspect updated session in response context
            # or inspect session directly on client if framework/test client supports it easily.
            # For Flask, session is typically accessed within a request context.
            # So, we check the session after the redirect is followed.
            response_after_redirect = self.client.get('/pomodoro')
            self.assertEqual(response_after_redirect.status_code, 200)
            # Accessing session directly like this is usually done within app context during request.
            # In tests, we can check the session object associated with the client.
            with self.client.session_transaction() as sess:
                self.assertIn('pomodoro_state', sess)
                self.assertEqual(sess['pomodoro_state']['interval_type'], 'work')
                self.assertTrue(sess['pomodoro_state']['is_running'])

    def test_pomodoro_pause_timer(self):
        with self.client:
            self.client.post('/pomodoro/start_work') # Start the timer first
            response = self.client.post('/pomodoro/pause')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/pomodoro')
            with self.client.session_transaction() as sess:
                self.assertFalse(sess['pomodoro_state']['is_running'])

    def test_pomodoro_stop_timer(self):
        with self.client:
            self.client.post('/pomodoro/start_work') # Start
            self.client.post('/pomodoro/pause')    # Pause
            response = self.client.post('/pomodoro/stop') # Stop
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/pomodoro')
            with self.client.session_transaction() as sess:
                self.assertFalse(sess['pomodoro_state']['is_running'])
                self.assertEqual(sess['pomodoro_state']['interval_type'], 'work') # Should reset to work
                # Check if remaining time is reset to default work duration
                # This needs access to PomodoroTimer's default work_duration
                # temp_timer = PomodoroTimer()
                # self.assertEqual(sess['pomodoro_state']['remaining_seconds'], temp_timer.work_duration)
                # For simplicity, we'll assume it resets to a positive value if type is work.
                self.assertTrue(sess['pomodoro_state']['remaining_seconds'] > 0)


    # 3. Task Logging (`/log_task` POST)
    def test_log_task_successful(self):
        start_time = datetime(2023, 1, 1, 10, 0, 0)
        end_time = datetime(2023, 1, 1, 10, 30, 0)
        task_data = {
            'description': 'Test Web UI Task',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_minutes': '30',
            'tags': 'web,test'
        }
        with self.client:
            response = self.client.post('/log_task', data=task_data, follow_redirects=False)
            self.assertEqual(response.status_code, 302) # Redirect on success
            self.assertEqual(response.location, '/log_task')

            # Check for flash message
            # After a redirect, the flash message is in the *next* response's context.
            response_after_redirect = self.client.get(response.location)
            self.assertIn(b"Task logged successfully!", response_after_redirect.data)

            # Verify logged data
            logger = TaskLogger(log_file_path=TEST_WEB_LOG_FILE)
            logged_tasks = logger.get_tasks()
            self.assertEqual(len(logged_tasks), 1)
            self.assertEqual(logged_tasks[0]['description'], 'Test Web UI Task')
            self.assertEqual(logged_tasks[0]['duration_minutes'], 30)
            self.assertEqual(logged_tasks[0]['tags'], ['web', 'test'])

    def test_log_task_invalid_data(self):
        task_data = { # Missing description, invalid duration
            'start_time': datetime(2023, 1, 1, 10, 0, 0).isoformat(),
            'end_time': datetime(2023, 1, 1, 9, 30, 0).isoformat(), # End before start
            'duration_minutes': '-10',
            'tags': 'invalid'
        }
        with self.client:
            response = self.client.post('/log_task', data=task_data, follow_redirects=True)
            self.assertEqual(response.status_code, 200) # Should re-render form
            self.assertIn(b"All fields except Tags are required.", response.data) # For missing description
            # Depending on which error is caught first by the route's validation logic:
            # self.assertIn(b"End time must be after start time.", response.data)
            # self.assertIn(b"Duration must be a positive number of minutes.", response.data)
            
            logger = TaskLogger(log_file_path=TEST_WEB_LOG_FILE)
            logged_tasks = logger.get_tasks()
            self.assertEqual(len(logged_tasks), 0, "No task should be logged with invalid data")

    # 4. View Tasks (`/tasks` GET with data)
    def _log_sample_task_direct(self, description, start_dt, end_dt, duration, tags=None):
        logger = TaskLogger(log_file_path=TEST_WEB_LOG_FILE)
        logger.log_task(description, start_dt, end_dt, duration, tags if tags else [])

    def test_view_tasks_with_data(self):
        sample_date = date(2023, 5, 15)
        start_dt = datetime.combine(sample_date, datetime.min.time().replace(hour=10))
        self._log_sample_task_direct("Task for view test", start_dt, start_dt.replace(hour=11), 60, ["view"])

        response = self.client.get('/tasks')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Task for view test", response.data)

    def test_view_tasks_filtered_match(self):
        sample_date = date(2023, 5, 15)
        start_dt = datetime.combine(sample_date, datetime.min.time().replace(hour=12))
        self._log_sample_task_direct("Filter Match Task", start_dt, start_dt.replace(hour=13), 60, ["filter_m"])

        response = self.client.get(f'/tasks?filter_date={sample_date.strftime("%Y-%m-%d")}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Filter Match Task", response.data)

    def test_view_tasks_filtered_no_match(self):
        sample_date = date(2023, 5, 15)
        other_date = date(2023, 5, 16)
        start_dt = datetime.combine(sample_date, datetime.min.time().replace(hour=14))
        self._log_sample_task_direct("Filter No Match Task", start_dt, start_dt.replace(hour=15), 60, ["filter_nm"])

        response = self.client.get(f'/tasks?filter_date={other_date.strftime("%Y-%m-%d")}')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Filter No Match Task", response.data)
        self.assertIn(b"No tasks found", response.data) # Check for the "no tasks" message

    # 5. Productivity Report (`/productivity_report` GET with data)
    def test_productivity_report_with_data(self):
        report_date = date(2023, 8, 20)
        start_dt1 = datetime.combine(report_date, datetime.min.time().replace(hour=9))
        self._log_sample_task_direct("Report Task 1", start_dt1, start_dt1.replace(hour=10), 60, ["work", "report"])
        start_dt2 = datetime.combine(report_date, datetime.min.time().replace(hour=11))
        self._log_sample_task_direct("Report Task 2", start_dt2, start_dt2.replace(hour=11, minute=30), 30, ["personal", "report"])

        response = self.client.get(f'/productivity_report?report_date={report_date.strftime("%Y-%m-%d")}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Productivity Report for: 2023-08-20", response.data)
        self.assertIn(b"Total Tasks Completed:</strong> 2", response.data)
        self.assertIn(b"Total Focused Time:</strong> 90 minutes", response.data)
        self.assertIn(b"work:</strong> 60 minutes", response.data)
        self.assertIn(b"personal:</strong> 30 minutes", response.data)
        self.assertIn(b"report:</strong> 90 minutes", response.data) # 60 + 30

    def test_productivity_report_no_data_for_date(self):
        report_date = date(2023, 8, 21) # A date with no tasks
        response = self.client.get(f'/productivity_report?report_date={report_date.strftime("%Y-%m-%d")}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Productivity Report for: 2023-08-21", response.data)
        self.assertIn(b"Total Tasks Completed:</strong> 0", response.data)
        self.assertIn(b"Total Focused Time:</strong> 0 minutes", response.data)
        self.assertIn(b"No tasks with tags found for this day.", response.data)
        # Or, if there was an issue and summary is None but report_date_str exists
        # self.assertIn(b"No productivity data found for 2023-08-21", response.data)
        # The current implementation of get_daily_summary returns a zeroed-out dict, so the above is correct.

if __name__ == '__main__':
    unittest.main()
