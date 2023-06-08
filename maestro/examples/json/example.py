from maestro.core import Orchestrator, ConfigReader

tasks = ConfigReader.from_json("example.json")
scheduler = Orchestrator(tasks)
scheduler.run()

