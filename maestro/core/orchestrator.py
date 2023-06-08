import concurrent.futures

import matplotlib.pyplot as plt
import networkx as nx

from maestro.core.task import Task

class Orchestrator:
    def __init__(self, tasks):
        self.tasks = tasks
        self.execution_order = []

    def run(self):
        self._validate_dependencies()
        self._add_root_dependency()
        self._build_execution_order()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}

            for task in self.execution_order:
                dependencies = [futures[dep.name] for dep in task.dependencies]
                future = executor.submit(self._execute_task, task, dependencies)
                futures[task.name] = future

        self._teardown_tasks()

    def _validate_dependencies(self):
        for task in self.tasks:
            for dependency in task.dependencies:
                if dependency not in self.tasks:
                    raise Exception(f"Invalid dependency for task {task.name}: {dependency.name}")

    def _add_root_dependency(self):
        root = Task("Root")
        for task in self.tasks:
            if not task.dependencies:
                task.dependencies.append(root)

    def _build_execution_order(self):
        visited = set()

        def visit(task):
            if task in visited:
                return
            visited.add(task)
            for dependency in task.dependencies:
                visit(dependency)
            self.execution_order.append(task)

        for task in self.tasks:
            visit(task)

    def _execute_task(self, task, dependencies):
        concurrent.futures.wait(dependencies)
        task.setup()
        task.run()

    def _teardown_tasks(self):
        for task in reversed(self.execution_order):
            task.teardown()

    def dag(self):
        dag = {}

        for task in self.execution_order:
            task_name = task.name
            dependencies = task.dependencies

            node = {"name": task_name, "children": []}
            for dep in dependencies:
                parent_node = dag.get(dep.name)
                if parent_node:
                    parent_node["children"].append(node)

            dag[task_name] = node

        root = None
        for task in self.execution_order:
            if not task.dependencies:
                root = dag[task.name]
                break

        graph = nx.DiGraph()
        self._traverse_and_add_edges(root, graph)

        pos = nx.spring_layout(graph, seed=42)
        nx.draw_networkx_nodes(graph, pos, node_color='lightblue', node_size=800, alpha=0.9)
        nx.draw_networkx_edges(graph, pos, arrows=True, alpha=0.7)
        nx.draw_networkx_labels(graph, pos, font_size=10, font_weight='bold')

        plt.title("Execution Order DAG")
        plt.axis('off')
        plt.savefig("dag.png", dpi=300)

    def _traverse_and_add_edges(self, node, graph):
        for child in node['children']:
            graph.add_edge(node['name'], child['name'])
            self._traverse_and_add_edges(child, graph)

