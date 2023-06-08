from maestro.core.task import Task

class Sum(Task):
    def __init__(self, name="sum_task", context={}, **kwargs):
        super().__init__(name, context, **kwargs)

    def run(self):
        return self.first + self.second
