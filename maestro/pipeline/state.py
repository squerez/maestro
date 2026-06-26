from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional


@dataclass
class Checkpoint:
    pipeline: str
    last_run: datetime
    status: Literal["success", "failed", "partial"]
    last_watermark: Optional[Any] = None
    records_processed: int = 0
    extra: dict = field(default_factory=dict)


class CheckpointStore:
    """
    Persists pipeline checkpoints as JSON files.

    Default location: ~/.maestro/checkpoints/<pipeline>.json
    Override with a directory path at construction time.
    """

    def __init__(self, directory: str | Path = "~/.maestro/checkpoints") -> None:
        self._dir = Path(directory).expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, pipeline: str) -> Path:
        return self._dir / f"{pipeline}.json"

    def load(self, pipeline: str) -> Optional[Checkpoint]:
        p = self._path(pipeline)
        if not p.exists():
            return None
        data = json.loads(p.read_text())
        data["last_run"] = datetime.fromisoformat(data["last_run"])
        return Checkpoint(**data)

    def save(self, checkpoint: Checkpoint) -> None:
        data = asdict(checkpoint)
        data["last_run"] = checkpoint.last_run.isoformat()
        self._path(checkpoint.pipeline).write_text(json.dumps(data, indent=2))

    def delete(self, pipeline: str) -> None:
        p = self._path(pipeline)
        if p.exists():
            p.unlink()

    def list_all(self) -> list[Checkpoint]:
        result = []
        for path in self._dir.glob("*.json"):
            cp = self.load(path.stem)
            if cp is not None:
                result.append(cp)
        return sorted(result, key=lambda c: c.last_run, reverse=True)

    @staticmethod
    def now() -> datetime:
        return datetime.now(tz=timezone.utc)
