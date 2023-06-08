import json
import yaml

from maestro.core.task import Task

class ConfigReader:
    @staticmethod
    def from_yaml(path):
        with open(path, "r") as file:
            data = yaml.safe_load(file)
        ConfigReader._validate_tasks(data)
        return ConfigReader._parse_tasks(data)

    @staticmethod
    def from_json(path):
        with open(path, "r") as file:
            data = json.load(file)
        ConfigReader._validate_tasks(data)
        return ConfigReader._parse_tasks(data)

    @staticmethod
    def _parse_tasks(data):
        tasks = []
        tasks_map = {}

        try:
            for task_data in data:
                name = task_data.get("name")
                dependencies = task_data.get("dependencies", [])

                task = Task(name, dependencies=dependencies)
                tasks.append(task)
                tasks_map[name] = task

                for dependency_name in dependencies:
                    dependency = tasks_map.get(dependency_name)
                    if dependency:
                        task.dependencies.append(dependency)
            return tasks
        except Exception as e:
            raise Exception("Error parsing tasks from configuration") from e

    @staticmethod
    def _validate_tasks(data):
        task_names = set()
        dependency_names = set()

        for task_data in data:
            name = task_data.get("name")
            dependencies = task_data.get("dependencies", [])

            if not name:
                raise ValueError("Invalid task: missing 'name' field")

            if name in task_names:
                raise ValueError(f"Duplicate task name: {name}")

            if not isinstance(dependencies, list):
                raise ValueError(f"Invalid dependencies for task '{name}': must be a list")

            if len(dependencies) != len(set(dependencies)):
                raise ValueError(f"Duplicate dependencies found for task '{name}'")

            task_names.add(name)
            dependency_names.update(dependencies)

        circular_references = ConfigReader._find_circular_references(data)
        if circular_references:
            raise ValueError(f"Circular references detected: {circular_references}")

        if dependency_names - task_names:
            raise ValueError("Invalid dependencies: some tasks are referenced but not defined")

    @staticmethod
    def _find_circular_references(data):
        tasks_map = {task_data.get("name"): task_data.get("dependencies", []) for task_data in data}

        for task_name in tasks_map:
            visited = set()
            stack = [(task_name, [])]

            while stack:
                current_task_name, path = stack.pop()

                if current_task_name in path:
                    return path + [current_task_name]

                if current_task_name not in visited:
                    visited.add(current_task_name)
                    dependencies = tasks_map.get(current_task_name, [])
                    for dependency_name in dependencies:
                        stack.append((dependency_name, path + [current_task_name]))

        return None
