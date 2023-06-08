from maestro.core import *

# Example usage
root = Task("Root")
a = Task("A", dependencies=[root])
b = Task("B", dependencies=[root])
c = Task("C", dependencies=[a])
d = Task("D", dependencies=[a])
e = Task("E", dependencies=[b])
f = Task("F", dependencies=[b])

tasks = [root, a, b, c, d, e, f]

scheduler = Orchestrator(tasks)
scheduler.run()
scheduler.dag()
