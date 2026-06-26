from __future__ import annotations

from typing import Any

from maestro.transforms.transform import transform

_ATTR_COLS = [
    "5_o_Clock_Shadow", "Arched_Eyebrows", "Attractive", "Bags_Under_Eyes",
    "Bald", "Bangs", "Big_Lips", "Big_Nose", "Black_Hair", "Blond_Hair",
    "Blurry", "Brown_Hair", "Bushy_Eyebrows", "Chubby", "Double_Chin",
    "Eyeglasses", "Goatee", "Gray_Hair", "Heavy_Makeup", "High_Cheekbones",
    "Male", "Mouth_Slightly_Open", "Mustache", "Narrow_Eyes", "No_Beard",
    "Oval_Face", "Pale_Skin", "Pointy_Nose", "Receding_Hairline",
    "Rosy_Cheeks", "Sideburns", "Smiling", "Straight_Hair", "Wavy_Hair",
    "Wearing_Earrings", "Wearing_Hat", "Wearing_Lipstick", "Wearing_Necklace",
    "Wearing_Necktie", "Young",
]


@transform(
    name="normalize_celeba_attrs",
    tags=["celeba", "vision", "normalization"],
    description=(
        "Converts CelebA attribute columns from -1/1 integers to booleans "
        "and adds a comma-separated dominant_attributes string column."
    ),
    input_schema=[{"name": "image_id", "type": "string", "nullable": False}],
    output_schema=[
        {"name": "image_id",            "type": "string",  "nullable": False},
        {"name": "dominant_attributes", "type": "string",  "nullable": True},
        {"name": "attr_count",          "type": "int",     "nullable": False},
    ],
)
class NormalizeCelebAAttrsTransform:
    def run(self, data: Any, params: dict) -> Any:
        import polars as pl

        available = set(data.collect_schema().names())
        attr_cols = [c for c in _ATTR_COLS if c in available]

        bool_exprs = [(pl.col(c) == 1).alias(c) for c in attr_cols]

        dominant = pl.concat_str(
            [
                pl.when(pl.col(c)).then(pl.lit(c)).otherwise(pl.lit(None))
                for c in attr_cols
            ],
            separator=", ",
            ignore_nulls=True,
        ).alias("dominant_attributes")

        attr_count = pl.sum_horizontal([pl.col(c).cast(pl.Int32) for c in attr_cols]).alias("attr_count")

        return data.with_columns(bool_exprs).with_columns([dominant, attr_count])
