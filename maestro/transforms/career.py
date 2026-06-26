from __future__ import annotations

from typing import Any

from maestro.transforms.transform import transform


@transform(
    name="enrich_career_index",
    tags=["enrichment", "career"],
    description="Enriches the AI career threat index with derived salary and score-trend columns.",
    input_schema=[
        {"name": "slug",                "type": "string", "nullable": False},
        {"name": "title",               "type": "string", "nullable": False},
        {"name": "category",            "type": "string", "nullable": False},
        {"name": "score",               "type": "int",    "nullable": False},
        {"name": "risk_level",          "type": "string", "nullable": False},
        {"name": "salary_low_usd",      "type": "int",    "nullable": False},
        {"name": "salary_high_usd",     "type": "int",    "nullable": False},
        {"name": "score_q1_2025",       "type": "int",    "nullable": False},
        {"name": "score_q2_2026",       "type": "int",    "nullable": False},
        {"name": "salary_trend",        "type": "string", "nullable": True},
        {"name": "tasks_at_risk_count", "type": "int",    "nullable": True},
        {"name": "tasks_growing_count", "type": "int",    "nullable": True},
        {"name": "defense_skill_1",     "type": "string", "nullable": True},
        {"name": "defense_skill_2",     "type": "string", "nullable": True},
        {"name": "defense_skill_3",     "type": "string", "nullable": True},
        {"name": "insight",             "type": "string", "nullable": True},
    ],
    output_schema=[
        {"name": "slug",                "type": "string", "nullable": False},
        {"name": "title",               "type": "string", "nullable": False},
        {"name": "category",            "type": "string", "nullable": False},
        {"name": "score",               "type": "int",    "nullable": False},
        {"name": "risk_level",          "type": "string", "nullable": False},
        {"name": "salary_low_usd",      "type": "int",    "nullable": False},
        {"name": "salary_high_usd",     "type": "int",    "nullable": False},
        {"name": "salary_mid_usd",      "type": "int",    "nullable": False},
        {"name": "score_delta",         "type": "int",    "nullable": False},
        {"name": "salary_trend",        "type": "string", "nullable": True},
        {"name": "tasks_at_risk_count", "type": "int",    "nullable": True},
        {"name": "tasks_growing_count", "type": "int",    "nullable": True},
        {"name": "defense_skill_1",     "type": "string", "nullable": True},
        {"name": "defense_skill_2",     "type": "string", "nullable": True},
        {"name": "defense_skill_3",     "type": "string", "nullable": True},
        {"name": "insight",             "type": "string", "nullable": True},
    ],
)
class EnrichCareerIndexTransform:
    def run(self, data: Any, params: dict) -> Any:
        import polars as pl

        return (
            data.with_columns(
                # mid-point salary
                ((pl.col("salary_low_usd") + pl.col("salary_high_usd")) // 2)
                .alias("salary_mid_usd"),
                # score trend: latest quarter vs earliest available
                (pl.col("score_q2_2026") - pl.col("score_q1_2025"))
                .alias("score_delta"),
            )
            .select([
                "slug", "title", "category",
                "score", "risk_level",
                "salary_low_usd", "salary_high_usd", "salary_mid_usd",
                "score_delta",
                "salary_trend", "tasks_at_risk_count", "tasks_growing_count",
                "defense_skill_1", "defense_skill_2", "defense_skill_3",
                "insight",
            ])
        )
