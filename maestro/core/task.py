import logging
from datetime import datetime

from maestro.core.state import TaskState

class Task:
    def __init__(self, name, dependencies=None, **kwargs):
        self.name = name
        self.dependencies = dependencies or []
        self.state = TaskState.PENDING

        for key, value in kwargs.items():
            setattr(self, key, value)

    def setup(self):
        self.state = TaskState.IN_PROGRESS
        print(f"[{self._get_timestamp()}] Setting up task: {self.name}")

    def run(self):
        print(f"[{self._get_timestamp()}] Running task: {self.name}")

    def teardown(self):
        print(f"[{self._get_timestamp()}] Tearing down task: {self.name}")
        self.state = TaskState.COMPLETED

    def _get_timestamp(self):
        return datetime.now().strftime("%H:%M:%S.%f")

    def log(self, message):
        logging.info(message)
