from __future__ import annotations

from typing import Any

from maestro.transforms.transform import transform


@transform(
    name="normalize_eonet_events",
    tags=["eonet", "nasa", "geospatial", "normalization"],
    description=(
        "Flattens raw EONET v3 events JSON into one row per geometry track point. "
        "Extracts category, source, coordinates, magnitude and closed status."
    ),
    input_schema=[{"name": "id", "type": "string", "nullable": False}],
    output_schema=[
        {"name": "event_id",        "type": "string",  "nullable": False},
        {"name": "title",           "type": "string",  "nullable": False},
        {"name": "category_id",     "type": "string",  "nullable": True},
        {"name": "category_title",  "type": "string",  "nullable": True},
        {"name": "source_id",       "type": "string",  "nullable": True},
        {"name": "source_url",      "type": "string",  "nullable": True},
        {"name": "closed",          "type": "string",  "nullable": True},
        {"name": "point_date",      "type": "string",  "nullable": True},
        {"name": "longitude",       "type": "float",   "nullable": True},
        {"name": "latitude",        "type": "float",   "nullable": True},
        {"name": "magnitude_value", "type": "float",   "nullable": True},
        {"name": "magnitude_unit",  "type": "string",  "nullable": True},
    ],
)
class NormalizeEonetEventsTransform:
    def run(self, data: Any, params: dict) -> Any:
        import polars as pl
        df = data.collect()
        rows = []

        for event in df.to_dicts():
            event_id    = event.get("id", "")
            title       = event.get("title", "")
            closed      = event.get("closed")
            link        = event.get("link", "")

            categories  = event.get("categories") or []
            cat_id      = categories[0]["id"]    if categories else None
            cat_title   = categories[0]["title"] if categories else None

            sources     = event.get("sources") or []
            src_id      = sources[0]["id"]  if sources else None
            src_url     = sources[0]["url"] if sources else None

            geometry    = event.get("geometry") or []
            if not geometry:
                rows.append({
                    "event_id": event_id, "title": title,
                    "category_id": cat_id, "category_title": cat_title,
                    "source_id": src_id, "source_url": src_url,
                    "closed": closed, "link": link,
                    "point_date": None, "longitude": None, "latitude": None,
                    "magnitude_value": None, "magnitude_unit": None,
                })
                continue

            for pt in geometry:
                coords = pt.get("coordinates") or []
                rows.append({
                    "event_id":        event_id,
                    "title":           title,
                    "category_id":     cat_id,
                    "category_title":  cat_title,
                    "source_id":       src_id,
                    "source_url":      src_url,
                    "closed":          closed,
                    "link":            link,
                    "point_date":      pt.get("date"),
                    "longitude":       float(coords[0]) if len(coords) > 0 else None,
                    "latitude":        float(coords[1]) if len(coords) > 1 else None,
                    "magnitude_value": pt.get("magnitudeValue"),
                    "magnitude_unit":  pt.get("magnitudeUnit"),
                })

        return pl.DataFrame(rows, infer_schema_length=len(rows) or 1).lazy()
