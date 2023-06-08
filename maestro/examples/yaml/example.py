from maestro.core import Orchestrator, ConfigReader

tasks = ConfigReader.from_yaml("example.yaml")
scheduler = Orchestrator(tasks)
scheduler.run()
