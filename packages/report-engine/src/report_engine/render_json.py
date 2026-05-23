"""JSON report renderer (T086).

Produces a deterministic JSON string via Pydantic's model_dump_json
with sort_keys=True. Same `ReportBundle` input always yields the
same byte sequence.
"""

from __future__ import annotations

import json

from shared_types.report import ReportBundle


def render_report_json(bundle: ReportBundle) -> str:
    """Render a `ReportBundle` to a deterministic JSON string."""
    payload = bundle.model_dump(mode="json")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
