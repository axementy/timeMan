# TimeTracker

## 1. Project Overview

TimeTracker is a command-line and web application for managing time using the Pomodoro technique, logging tasks, and evaluating productivity.

## 2. Current Features

### Core Logic

-   **`PomodoroTimer`**: Manages work and break intervals based on the Pomodoro technique.
    -   Default work duration: 25 minutes.
    -   Default short break duration: 5 minutes.
    -   Default long break duration: 15 minutes (triggered after 4 work cycles).
    -   Currently, the timer is synchronous and prints notifications and progress to the console.
-   **`TaskLogger`**: Logs details of completed tasks.
    -   Information logged: task description, start datetime, end datetime, duration in minutes, and associated tags.
    -   Data is stored in a CSV file located at `timetracker/data/tasks.csv`.
-   **`ProductivityEvaluator`**: Analyzes logged tasks to provide productivity insights.
    -   Calculates total focused time for a specific day.
    -   Generates a daily summary including total number of tasks, total focused time in minutes, and a breakdown of time spent per tag.

### Command-Line Interface (CLI)

The CLI provides commands to interact with the core logic:

-   **Start a Pomodoro session:**
    ```bash
    python -m timetracker.cli.main pomodoro start [--work DURATION] [--short_break DURATION] [--long_break DURATION]
    ```
    -   `DURATION`s are specified in minutes.

-   **Log a completed task:**
    ```bash
    python -m timetracker.cli.main log task "Your task description" --start "YYYY-MM-DDTHH:MM:SS" --end "YYYY-MM-DDTHH:MM:SS" --duration <minutes> [--tags <T1,T2,T3>]
    ```
    -   `--start` and `--end` require datetime in ISO format.
    -   `--duration` is the task duration in minutes.
    -   `--tags` are optional, comma-separated.

-   **View logged tasks:**
    ```bash
    python -m timetracker.cli.main view log [--date YYYY-MM-DD]
    ```
    -   Optionally filters tasks by a specific date.

-   *(A CLI command for displaying productivity reports generated by `ProductivityEvaluator` is planned).*

## 3. Dependencies

Currently, the project relies on the following Python libraries:

-   **`click`**: Used for building the command-line interface.
-   **`Flask`**: Used for the web user interface.

## 4. Setup and Running

### CLI

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
    *(Note: Replace `<repository_url>` and `<repository_directory>` with actual values if applicable. For the current environment, assume the code is already checked out.)*

2.  **Navigate to the project's root directory** (the one containing the `timetracker` package directory and `requirements.txt`, if you are not already there).

3.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the CLI:**
    Commands are executed using the Python module syntax from the project's root directory.
    For example:
    ```bash
    python -m timetracker.cli.main pomodoro start
    python -m timetracker.cli.main view log --date 2023-10-28
    ```

### Web UI

The Flask web application provides a basic interface and will be expanded in the future.

1.  **Ensure dependencies are installed** (see CLI setup above, specifically `pip install -r requirements.txt`).

2.  **Run the Flask development server:**
    From the project's root directory:
    ```bash
    python timetracker/web/app.py
    ```
    Or, using Flask CLI (requires `FLASK_APP` environment variable):
    ```bash
    export FLASK_APP=timetracker.web.app:create_app  # Or set FLASK_APP=timetracker.web.app for auto-discovery if app instance is global
    flask run
    ```
    The application will typically be available at `http://127.0.0.1:5000/` or `http://0.0.0.0:5000/`.

## 5. Potential Improvements (Future Enhancements)

-   **Timer Mechanism**:
    -   More robust CLI timer (e.g., asynchronous operations, better resilience to system sleep/interrupts, background execution).
    -   Persistent storage for timer state across application restarts.
    -   GUI desktop notifications for timer events (instead of just console messages).
-   **Configuration**:
    -   Implement a configuration file (e.g., `config.ini` or `config.json`) for user-definable defaults such as timer durations, log file paths, etc.
-   **CLI Interactivity**:
    -   Develop an interactive CLI mode with more dynamic controls for the timer (e.g., quick commands to pause, skip, reset from an active timer session).

## 6. Examples of New Features That Could Be Added

-   **Advanced Reporting**:
    -   Detailed productivity reports (e.g., weekly/monthly trends, analysis by project/tag over time).
    -   Visualizations and charts for productivity data.
    -   Exporting data in different formats (e.g., JSON, Excel).
-   **User Management**:
    -   User accounts and data separation (if the application is intended for multiple users).
-   **Goal Setting**:
    -   Functionality to set daily or weekly goals for focused time or number of tasks.
-   **Integrations**:
    -   Cloud synchronization of task data (e.g., Google Drive, Dropbox).
    -   Integrations with external calendars or task management tools (e.g., Google Calendar, Todoist, Jira).
-   **Productivity Insights**:
    -   More sophisticated productivity scoring or personalized insights based on logged data.

This `README.md` will be updated as the project evolves.
