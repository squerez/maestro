import yaml
import json 

from maestro.core.task import Task

class ConfigReader:
    @staticmethod
    def from_yaml(path):
        with open(path, "r") as file:
            data = yaml.safe_load(file)
        return ConfigReader._parse_tasks(data)

    @staticmethod
    def from_json(path):
        with open(path, "r") as file:
            data = json.load(file)
        return ConfigReader._parse_tasks(data)

    @staticmethod
    def _parse_tasks(data):
        tasks = []
        tasks_map = {}

        for task_data in data:
            name = task_data.get("name")
            dependencies = task_data.get("dependencies", [])

            task = Task(name)
            tasks.append(task)
            tasks_map[name] = task

            for dependency_name in dependencies:
                dependency = tasks_map.get(dependency_name)
                if dependency:
                    task.dependencies.append(dependency)
        return tasks

