import unittest
import sys
import os
import csv
from datetime import datetime, date
import shutil # For easily removing directory

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from timetracker.core.logger import TaskLogger

class TestTaskLogger(unittest.TestCase):

    TEST_LOG_DIR = os.path.join(project_root, "tests", "temp_test_data")
    TEST_LOG_FILE = os.path.join(TEST_LOG_DIR, "test_tasks.csv")

    def setUp(self):
        # Ensure the test log directory exists
        os.makedirs(self.TEST_LOG_DIR, exist_ok=True)
        # Instantiate logger for each test
        self.logger = TaskLogger(log_file_path=self.TEST_LOG_FILE)
        # Clean up any existing log file from previous failed tests
        if os.path.exists(self.TEST_LOG_FILE):
            os.remove(self.TEST_LOG_FILE)

    def tearDown(self):
        # Remove the test log file after each test
        if os.path.exists(self.TEST_LOG_FILE):
            os.remove(self.TEST_LOG_FILE)
        # Remove the test log directory if it's empty
        if os.path.exists(self.TEST_LOG_DIR) and not os.listdir(self.TEST_LOG_DIR):
            shutil.rmtree(self.TEST_LOG_DIR)
        elif os.path.exists(self.TEST_LOG_DIR) and os.path.isfile(os.path.join(self.TEST_LOG_DIR, ".placeholder")):
             # If only placeholder exists, remove it and the dir
            os.remove(os.path.join(self.TEST_LOG_DIR, ".placeholder"))
            if not os.listdir(self.TEST_LOG_DIR):
                 shutil.rmtree(self.TEST_LOG_DIR)


    def test_initialization_stores_path(self):
        self.assertEqual(self.logger.log_file_path, self.TEST_LOG_FILE)

    def test_initialization_creates_directory(self):
        # Temporarily remove directory to test its creation
        if os.path.exists(self.TEST_LOG_DIR):
            shutil.rmtree(self.TEST_LOG_DIR)
        
        self.assertFalse(os.path.exists(self.TEST_LOG_DIR))
        # Instantiating TaskLogger should create the directory
        logger_for_dir_test = TaskLogger(log_file_path=self.TEST_LOG_FILE)
        self.assertTrue(os.path.exists(self.TEST_LOG_DIR))
        # Clean up for other tests
        if os.path.exists(self.TEST_LOG_FILE): # logger_for_dir_test might create an empty file
            os.remove(self.TEST_LOG_FILE)


    def test_log_single_task(self):
        start_dt = datetime(2023, 1, 1, 10, 0, 0)
        end_dt = datetime(2023, 1, 1, 10, 30, 0)
        self.logger.log_task("Test Task 1", start_dt, end_dt, 30, ["tag1", "tag2"])

        self.assertTrue(os.path.exists(self.TEST_LOG_FILE))
        with open(self.TEST_LOG_FILE, mode='r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertEqual(header, TaskLogger._CSV_HEADER)
            data_row = next(reader)
            self.assertEqual(data_row[0], start_dt.isoformat())
            self.assertEqual(data_row[1], end_dt.isoformat())
            self.assertEqual(int(data_row[2]), 30)
            self.assertEqual(data_row[3], "Test Task 1")
            self.assertEqual(data_row[4], "tag1,tag2")

    def test_log_multiple_tasks(self):
        start1 = datetime(2023, 1, 1, 10, 0, 0)
        end1 = datetime(2023, 1, 1, 10, 30, 0)
        self.logger.log_task("Task A", start1, end1, 30, ["work"])

        start2 = datetime(2023, 1, 1, 11, 0, 0)
        end2 = datetime(2023, 1, 1, 11, 45, 0)
        self.logger.log_task("Task B", start2, end2, 45, ["personal"])

        with open(self.TEST_LOG_FILE, mode='r', newline='') as f:
            reader = csv.reader(f)
            next(reader) # Skip header
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][3], "Task A")
            self.assertEqual(rows[1][3], "Task B")

    def test_log_task_no_tags(self):
        start_dt = datetime(2023, 1, 1, 12, 0, 0)
        end_dt = datetime(2023, 1, 1, 12, 15, 0)
        self.logger.log_task("Task No Tags", start_dt, end_dt, 15) # Tags default to None

        with open(self.TEST_LOG_FILE, mode='r', newline='') as f:
            reader = csv.reader(f)
            next(reader) # Skip header
            data_row = next(reader)
            self.assertEqual(data_row[4], "") # Tags column should be empty

    def test_get_tasks_empty_file(self):
        # Ensure file is empty (or non-existent, logger.get_tasks handles non-existent)
        if os.path.exists(self.TEST_LOG_FILE):
             os.remove(self.TEST_LOG_FILE)
        tasks = self.logger.get_tasks()
        self.assertEqual(tasks, [])

    def test_get_tasks_non_existent_file(self):
        # Ensure file does not exist
        if os.path.exists(self.TEST_LOG_FILE):
            os.remove(self.TEST_LOG_FILE)
        tasks = self.logger.get_tasks()
        self.assertEqual(tasks, [])

    def test_get_tasks_all_and_data_conversion(self):
        start1 = datetime(2023, 1, 1, 10, 0, 0)
        end1 = datetime(2023, 1, 1, 10, 30, 0)
        self.logger.log_task("Task X", start1, end1, 30, ["dev", "api"])

        start2 = datetime(2023, 1, 1, 14, 0, 0)
        end2 = datetime(2023, 1, 1, 14, 20, 0)
        self.logger.log_task("Task Y", start2, end2, 20, ["research"])
        
        tasks = self.logger.get_tasks()
        self.assertEqual(len(tasks), 2)

        task_x = tasks[0]
        self.assertEqual(task_x['description'], "Task X")
        self.assertIsInstance(task_x['start_time'], datetime)
        self.assertEqual(task_x['start_time'], start1)
        self.assertIsInstance(task_x['end_time'], datetime)
        self.assertEqual(task_x['end_time'], end1)
        self.assertIsInstance(task_x['duration_minutes'], int)
        self.assertEqual(task_x['duration_minutes'], 30)
        self.assertIsInstance(task_x['tags'], list)
        self.assertEqual(task_x['tags'], ["dev", "api"])

        task_y = tasks[1]
        self.assertEqual(task_y['description'], "Task Y")
        self.assertEqual(task_y['tags'], ["research"])


    def test_get_tasks_date_filter(self):
        date_filter_target = date(2023, 10, 28)
        
        # Task on the target date
        start1 = datetime(2023, 10, 28, 9, 0, 0)
        end1 = datetime(2023, 10, 28, 9, 30, 0)
        self.logger.log_task("On Date Task", start1, end1, 30)

        # Task on a different date
        start2 = datetime(2023, 10, 29, 10, 0, 0)
        end2 = datetime(2023, 10, 29, 10, 45, 0)
        self.logger.log_task("Different Date Task", start2, end2, 45)
        
        # Another task on the target date
        start3 = datetime(2023, 10, 28, 11, 0, 0)
        end3 = datetime(2023, 10, 28, 11, 15, 0)
        self.logger.log_task("Another On Date Task", start3, end3, 15)

        tasks = self.logger.get_tasks(date_filter=date_filter_target)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]['description'], "On Date Task")
        self.assertEqual(tasks[1]['description'], "Another On Date Task")
        for task in tasks:
            self.assertEqual(task['start_time'].date(), date_filter_target)

    def test_get_tasks_date_filter_no_match(self):
        start1 = datetime(2023, 11, 1, 9, 0, 0)
        end1 = datetime(2023, 11, 1, 9, 30, 0)
        self.logger.log_task("Some Task", start1, end1, 30)

        tasks = self.logger.get_tasks(date_filter=date(2023, 11, 2))
        self.assertEqual(len(tasks), 0)

    def test_header_written_once(self):
        start1 = datetime(2023, 1, 1, 10, 0, 0)
        end1 = datetime(2023, 1, 1, 10, 30, 0)
        self.logger.log_task("Task 1", start1, end1, 30)

        start2 = datetime(2023, 1, 1, 11, 0, 0)
        end2 = datetime(2023, 1, 1, 11, 45, 0)
        self.logger.log_task("Task 2", start2, end2, 45)

        with open(self.TEST_LOG_FILE, mode='r', newline='') as f:
            reader = csv.reader(f)
            header_count = 0
            for row in reader:
                if row == TaskLogger._CSV_HEADER:
                    header_count +=1
            self.assertEqual(header_count, 1, "Header should only be written once.")


if __name__ == '__main__':
    unittest.main()
