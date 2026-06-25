from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class StepDryRunResult:
    name: str
    plugin: str
    records_in: int
    records_out: int
    duration_seconds: float
    skipped: bool = False
    preview: Optional[Any] = None


@dataclass
class DryRunResult:
    pipeline: str
    total_duration_seconds: float
    step_results: List[StepDryRunResult] = field(default_factory=list)

    @property
    def total_records_out(self) -> int:
        return sum(s.records_out for s in self.step_results if not s.skipped)

    def summary(self) -> str:
        lines = [
            f"DRY RUN: {self.pipeline}",
            f"  Duration : {self.total_duration_seconds:.2f}s",
            f"  Steps    : {len(self.step_results)}",
            "",
        ]
        for s in self.step_results:
            tag = "SKIP" if s.skipped else " OK "
            lines.append(
                f"  [{tag}] {s.name:<30} {s.plugin:<40} "
                f"{s.records_in:>6} → {s.records_out:<6} rows   {s.duration_seconds:.3f}s"
            )
        return "\n".join(lines)
