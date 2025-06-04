# TimeTracker Application

## 1. Introduction

TimeTracker is a command-line (CLI) and web-based application designed to help you manage your time effectively using the Pomodoro Technique, track your tasks, and gain insights into your productivity.

**Key Features:**

*   **Task Management:** Create, view, update, and delete tasks with attributes like priority, due date, type, and status.
*   **Pomodoro Timer:** Utilize the Pomodoro Technique with configurable work, short break, and long break durations. Associate Pomodoro sessions with specific tasks.
*   **Activity Logging:** Automatically log work sessions and task status changes to a CSV file.
*   **Reporting:** Generate daily and weekly reports to understand how your time is spent and what you've accomplished.
*   **"Big Task" Summaries:** Get prompted to write a brief report upon completing significant tasks.
*   **Dual Interface:** Interact with the application via a comprehensive CLI or a user-friendly web interface.

## 2. Core Concepts

Understanding these core concepts will help you use TimeTracker effectively:

*   **Tasks:**
    *   The fundamental unit of work. Each task has:
        *   `ID`: A unique identifier (UUID).
        *   `Description`: What the task is about.
        *   `Priority`: A number (e.g., 1 for high, 2 for medium, 3 for low).
        *   `Due Time`: An optional date and time by which the task should be completed.
        *   `Type`: A category for the task (e.g., "Work", "Personal").
        *   `Status`: The current state of the task (e.g., "pending", "in-progress", "completed", "deleted").
        *   `Created At / Updated At`: Timestamps tracking when the task was created and last modified.
*   **Pomodoro Technique:**
    *   A time management method that uses a timer to break down work into intervals, traditionally 25 minutes in length, separated by short breaks. Long breaks are typically taken after four work intervals.
    *   TimeTracker helps you follow this by managing work and break timers and associating work intervals with your tasks.
*   **Logging:**
    *   **Task Snapshots:** Whenever a task is created or its definition (description, priority, status, etc.) is updated, a "snapshot" of its current state is logged in the `tasks.csv` file. These entries have a duration of 0 and are tagged "task_snapshot".
    *   **Work/Activity Logs:** When you complete a Pomodoro work interval for a task, or manually log time (future feature), an entry is created detailing the start time, end time, duration, and associated task details. These logs are used for time tracking and report generation.

## 3. Installation

**Prerequisites:**
*   Python 3.7 or newer.
*   `pip` (Python package installer).

**Setup Steps:**

1.  **Clone the Repository (Optional):**
    If you have access to the source code repository:
    ```bash
    git clone <repository_url>
    cd timetracker-application # Or your repository's directory name
    ```
    If you have the application files directly, navigate to the root project directory (the one containing this README and the `timetracker` package).

2.  **Create a Virtual Environment (Recommended):**
    It's good practice to use a virtual environment to manage project dependencies.
    ```bash
    python -m venv .venv
    ```
    Activate the virtual environment:
    *   On macOS and Linux:
        ```bash
        source .venv/bin/activate
        ```
    *   On Windows:
        ```bash
        .venv\Scripts\activate
        ```

3.  **Install Dependencies:**
    With your virtual environment activated, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
    (Note: If `requirements.txt` is not present or minimal, key dependencies like `click` and `Flask` would need to be listed or installed manually, e.g., `pip install click Flask`).

## 4. Running the Application

You can interact with TimeTracker via its Command Line Interface (CLI) or Web Interface.

### 4.1. Command Line Interface (CLI)

The CLI is invoked using `timetracker` (if installed as a package via `setup.py`) or `python -m timetracker.cli.main` from the project root directory. For simplicity, examples will use `timetracker`. If you are running from source without installation, replace `timetracker` with `python -m timetracker.cli.main`.

To see all available commands and options:
```bash
timetracker --help
```

### 4.2. Web Interface

The web interface provides a graphical way to manage tasks and use the Pomodoro timer.

1.  **Start the Flask Development Server:**
    From the project's root directory:
    ```bash
    python -m timetracker.web.app
    ```
    This will typically start the server on `http://127.0.0.1:5000/` or `http://0.0.0.0:5000/`. The console output will indicate the exact address.

2.  **Access in Browser:**
    Open your web browser and navigate to the address shown when you started the server (e.g., `http://127.0.0.1:5000/`).

## 5. Using the Command Line Interface (CLI)

The CLI is structured with command groups. General usage:
`timetracker <group> <command> [OPTIONS]`

### 5.1. Task Management (`timetracker task ...`)

*   **Create a Task:**
    ```bash
    timetracker task create --description "My new task" [OPTIONS]
    ```
    Options:
    *   `--description TEXT`: (Required) The description of the task.
    *   `--priority INTEGER`: Priority (e.g., 1-High, 2-Medium, 3-Low). Default: 2.
    *   `--due-time TEXT`: Due date/time (e.g., "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD").
    *   `--type TEXT`: Task type (e.g., "work", "personal"). Default: "work".
    *Example:*
    ```bash
    timetracker task create -d "Plan project timeline" -p 1 -dt "2024-09-15" -t "ProjectX"
    ```

*   **View Tasks:**
    ```bash
    timetracker task view [OPTIONS]
    ```
    Options:
    *   `--id TEXT`: View a specific task by its UUID.
    *   `--priority INTEGER`: Filter by priority.
    *   `--due-time TEXT`: Filter by due date (YYYY-MM-DD). Shows tasks due on that specific day.
    *   `--type TEXT`: Filter by task type (case-insensitive).
    *   `--status TEXT`: Filter by task status (e.g., "pending", "in-progress", "completed", "deleted").
    *   `--sort-by TEXT`: Field to sort by (priority, due_time, type, status, description, created_at, updated_at). Default: `created_at`.
    *   `--sort-order TEXT`: Sort order ('asc' or 'desc'). Default: `asc`.
    *Example:*
    ```bash
    timetracker task view --status "in-progress" --sort-by priority
    ```

*   **Update a Task:**
    ```bash
    timetracker task update <TASK_ID> [OPTIONS]
    ```
    `<TASK_ID>` is the UUID of the task to update.
    Options (provide only those you want to change):
    *   `--description TEXT`
    *   `--priority INTEGER`
    *   `--due-time TEXT` (To clear due date, behavior might depend on system; often passing empty string or specific keyword if supported by parser).
    *   `--type TEXT`
    *   `--status TEXT`
    *Example:*
    ```bash
    timetracker task update <TASK_ID_HERE> --priority 1 --status "in-progress"
    ```

*   **Delete a Task (Mark as Deleted):**
    ```bash
    timetracker task delete <TASK_ID>
    ```
    This marks the task's status as 'deleted'. It is not physically removed from the log but will be hidden from default views.
    *Example:*
    ```bash
    timetracker task delete <TASK_ID_HERE>
    ```

### 5.2. Pomodoro Timer (`timetracker pomodoro ...`)

*   **Start a Pomodoro Session:**
    ```bash
    timetracker pomodoro start [OPTIONS]
    ```
    Options:
    *   `--work INTEGER`: Work interval duration in minutes. Default: 25.
    *   `--short-break INTEGER`: Short break duration in minutes. Default: 5.
    *   `--long-break INTEGER`: Long break duration in minutes. Default: 15.
    *   `--task-id TEXT`: ID of the task to associate with work intervals.
    *Operation:*
    The timer will start (typically a work interval). Console messages will indicate the current interval type and time remaining (updated per second).
    When an interval finishes, it will print a message and prompt you to start the next one (e.g., "Start the next interval (short break)? [Y/n]:").
    Press `Ctrl+C` during an interval's countdown to pause it. You will then be prompted to resume or stop.
    *Example:*
    ```bash
    timetracker pomodoro start --work 30 --task-id <YOUR_TASK_ID>
    ```

### 5.3. Reporting (`timetracker report ...`)

*   **Daily Report:**
    ```bash
    timetracker report daily [OPTIONS]
    ```
    Option:
    *   `--date TEXT`: Date for the report (YYYY-MM-DD). Defaults to today.
    *Example Output:*
    ```
    --- Daily Report for 2024-08-01 ---
    Total Tasks Completed: 1
    Total Time Spent: 50 minutes
    Time Spent by Task Type:
      - Work: 50 minutes
    Tasks Marked Completed Today:
      - ID: ..., Desc: Finish documentation
    ```

*   **Weekly Report:**
    ```bash
    timetracker report weekly [OPTIONS]
    ```
    Options:
    *   `--start-date TEXT`: Start date (YYYY-MM-DD). Defaults to Monday of the current week.
    *   `--end-date TEXT`: End date (YYYY-MM-DD). Defaults to Sunday of the current week.
    *Example:*
    ```bash
    timetracker report weekly --start-date 2024-07-29 --end-date 2024-08-04
    ```

### 5.4. Legacy Log Entry Commands

These commands interact with the logging system at a more basic level.
*   **Log a Generic Timed Entry:**
    ```bash
    timetracker logentry add "<description>" --start "<datetime>" --end "<datetime>" [--tags "<t1,t2>"] [--task-id <TASK_ID>]
    ```
    *Note:* Currently, `--task-id` is effectively required for this command to associate the log with a structured `Task` object, as the underlying logger method expects one. The `<description>` here is for the log entry itself and might be superseded by the task's description if a `task-id` is provided.

*   **View Raw Log Entries:**
    ```bash
    timetracker viewentries all [--date YYYY-MM-DD]
    ```
    Displays all raw entries from the `tasks.csv` log file, useful for debugging or inspection.

## 6. Using the Web Interface

The web interface provides a graphical way to interact with TimeTracker.

*   **Navigation:**
    The main navigation bar typically includes:
    *   `Home`: Back to the main page.
    *   `Pomodoro Timer`: Access the Pomodoro timer page.
    *   `Manage Tasks`: View and manage your tasks.
    *   `Reports`: Access daily and weekly reports.
    *   Legacy links (e.g., "Log Entry (Old)") might also be present.

*   **Task Management (`/tasks/all`):**
    *   **Viewing Tasks:** The main task page lists your tasks. By default, it shows active tasks.
    *   **Filtering:** Use the filter controls at the top of the list to narrow down tasks by priority, due date, type, or status (including "deleted").
    *   **Sorting:** Click on table headers (e.g., "Description", "Priority") to sort the task list. Click again to toggle ascending/descending order.
    *   **Creating a New Task:** Click the "Create New Task" button. Fill in the form (description, priority, due date/time, type).
    *   **Editing an Existing Task:** Click the "Edit" button next to a task. Modify details in the form and save.
    *   **Deleting a Task:** Click the "Delete" button. This marks the task as 'deleted'.

*   **Pomodoro Timer (`/pomodoro`):**
    *   **Starting Intervals:** Use buttons like "Start Work Interval", "Start Short Break", etc.
    *   **Associating a Task:** Before starting a work interval, you can select a task from the "Associate Task (Optional)" dropdown. This links the work session to that task for logging and status updates.
    *   The timer display (client-side JavaScript) will show the current interval and remaining time. When an interval finishes, the page usually reloads to reflect the next state or prompt (e.g., for a "big task" report).
    *   Use "Pause", "Resume", "Reset Current Interval", or "Stop" buttons to control the timer.

*   **Viewing Reports (`/reports`):**
    *   The main reports page provides forms to select dates for daily or weekly reports.
    *   **Daily Report:** Choose a date and click "View Daily".
    *   **Weekly Report:** Choose a start and end date and click "View Weekly".
    *   The reports show summaries of completed tasks, time spent, and breakdowns similar to the CLI reports.

## 7. "Big Task" Completion Reports

To help reflect on significant accomplishments, TimeTracker prompts for a brief report when a "big task" is completed.

*   **What is a "Big Task"?**
    Currently, a task is considered "big" if it's marked as 'completed' AND has accumulated a total logged work time of 2 hours (120 minutes) or more.
*   **How the Prompt Appears:**
    *   **CLI:** After a Pomodoro work session that results in a big task being completed, a message will appear in the console: "Congratulations on completing a major task: [Task Description]! Would you like to write a brief report/summary for it? (yes/no)".
    *   **Web Interface:** After a Pomodoro work interval finishes via the web UI and a big task is completed, you will be redirected to a special page titled "Task Completion Report" for that task.
*   **Submitting the Report:**
    *   **CLI:** If you answer "yes", you'll be prompted to enter your report multiline. Type "ENDREPORT" on a new line to finish.
    *   **Web Interface:** Fill in the textarea on the "Task Completion Report" page and click "Save Report". You can also choose to skip.
*   **Storage:**
    These reports are saved in Markdown format by appending to the `timetracker/data/task_reports.md` file. Each report includes the task details, completion date, total logged time, and your summary.

## 8. Data Storage

Your task and activity data is stored locally:

*   `timetracker/data/tasks.csv`: This CSV file contains all task snapshots and logged work/Pomodoro sessions. It's the primary data store.
*   `timetracker/data/task_reports.md`: Markdown file where reports for "big tasks" are appended.

It's advisable to back up the `timetracker/data/` directory periodically if you store important information in the application.

## 9. Troubleshooting (Tips)

*   **CLI not found (`timetracker: command not found`):**
    *   Ensure your virtual environment is activated.
    *   If running from source without installation, use `python -m timetracker.cli.main ...` from the project root.
    *   If installed via `setup.py`, ensure `.local/bin` (Linux) or Python Scripts directory (Windows) is in your system's PATH.
*   **Web server doesn't start:**
    *   Check for error messages in the console.
    *   Ensure all dependencies from `requirements.txt` are installed.
    *   Make sure port 5000 (or the configured port) is not already in use.
*   **Incorrect dates or times:**
    *   Ensure your system's date, time, and timezone are set correctly.
    *   When providing dates/times to CLI options or web forms, use the specified formats (e.g., YYYY-MM-DD HH:MM:SS).

---
This user manual should provide a good starting point for using TimeTracker. For developer information or contribution guidelines, please refer to other documentation if available.
