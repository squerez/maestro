from maestro.core import Task, Orchestrator

# Example usage of direct invokation of the maestro utils
a = Task("A")
b = Task("B")
c = Task("C", dependencies=[a])
d = Task("D", dependencies=[a])
e = Task("E", dependencies=[b])
f = Task("F", dependencies=[b])

tasks = [a, b, c, d, e, f]
scheduler = Orchestrator(tasks)
scheduler.run()
