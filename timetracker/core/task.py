"""
Defines the Task class, representing a single to-do item or task.
"""
import uuid
from datetime import datetime
from typing import Optional

class Task:
    """
    Represents a task in the time tracker application.

    Each task has a unique identifier, description, priority, due date/time,
    type (e.g., work, personal), status (e.g., pending, completed), and
    timestamps for creation and last update.

    Attributes:
        id (uuid.UUID): A unique identifier for the task.
        description (str): A textual description of the task.
        priority (int): The priority of the task (e.g., 1 for high, 2 for medium).
        due_time (Optional[datetime]): The due date and time for the task. Can be None.
        type (str): The category or type of the task (e.g., "work", "personal").
        status (str): The current status of the task (e.g., "pending", "in-progress", "completed").
        created_at (datetime): Timestamp of when the task was created.
        updated_at (datetime): Timestamp of when the task was last updated.
    """

    def __init__(
        self,
        description: str,
        priority: int,
        due_time: Optional[datetime],
        type: str,
        status: str = "pending",
    ):
        """
        Initializes a new Task object.

        When a task is created, `created_at` and `updated_at` are automatically
        set to the current time.

        Args:
            description: A string describing the task.
            priority: An integer representing the task's priority.
            due_time: An optional datetime object representing the task's due date and time.
                      Pass None if there is no specific due date.
            type: A string representing the task's type (e.g., "work", "personal").
            status: A string representing the task's status. Defaults to "pending".
        """
        self.id: uuid.UUID = uuid.uuid4()
        self.description: str = description
        self.priority: int = priority
        self.due_time: Optional[datetime] = due_time
        self.type: str = type
        self.status: str = status
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now() # Initially same as created_at

    def __repr__(self) -> str:
        """Returns a string representation of the Task object."""
        return (
            f"Task(id={self.id!r}, description={self.description!r}, "
            f"priority={self.priority!r}, due_time={self.due_time!r}, "
            f"type={self.type!r}, status={self.status!r}, "
            f"created_at={self.created_at!r}, updated_at={self.updated_at!r})"
        )

    def update(
        self,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_time: Optional[datetime] = None, # Note: To clear due_time, pass None explicitly if it was previously set.
                                         # However, the type hint Optional[datetime] on the attribute already implies it can be None.
                                         # The method signature here reflects what can be *passed* to update.
                                         # If a field is not passed (is None by default in method call), it's not updated.
                                         # To *set* due_time to None, one must pass due_time=None.
        type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> None:
        """
        Updates specified attributes of the task.

        Any attribute provided (i.e., not None) will be updated.
        The `updated_at` timestamp is automatically set to the current time
        anytime this method is called, even if no other attributes are changed.
        To clear an existing `due_time`, pass `due_time=None` explicitly.

        Args:
            description: An optional new description for the task.
            priority: An optional new priority for the task.
            due_time: An optional new due date and time for the task. Pass `None` to remove an existing due date.
            type: An optional new type for the task.
            status: An optional new status for the task.
        """
        # Flag to check if any actual data field was changed to warrant updated_at change
        # However, the requirement is to update updated_at regardless.
        # changed = False
        if description is not None:
            self.description = description
            # changed = True
        if priority is not None:
            self.priority = priority
            # changed = True

        # Special handling for due_time: if the key 'due_time' is part of update_data,
        # it means the user intends to change it, even if to None.
        # The current signature with default None for due_time means if due_time is not passed,
        # it's not updated. If due_time=None is passed, it IS updated to None.
        # This is correct.
        if due_time is not None: # This means due_time was explicitly passed as an argument.
            self.due_time = due_time # Update to new datetime or to None if None was passed
            # changed = True
        # If the intention was to allow explicit update to None even if current value is not None,
        # then this logic is okay. If due_time=None was passed, self.due_time becomes None.

        if type is not None:
            self.type = type
            # changed = True
        if status is not None:
            self.status = status
            # changed = True

        # As per previous implementation and typical behavior:
        # always update updated_at if .update() is called.
        self.updated_at = datetime.now()
