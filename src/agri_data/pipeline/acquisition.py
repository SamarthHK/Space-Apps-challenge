"""Configuration-driven acquisition for all currently implemented adapters."""

from datetime import date, timedelta
from typing import Any, Dict, Iterable, Optional
import json
import hashlib
import requests
from agri_data.config import settings

from agri_data.sources.soilgrids import SoilGridsClient
from agri_data.sources.nasa_power import NasaPowerClient
from agri_data.sources.gee import SatelliteImageryAdapter
from agri_data.sources.cgwb import CGWBGroundwaterAdapter


ADAPTERS = {
    "soil": SoilGridsClient,
    "climate": NasaPowerClient,
    "historical_land": SatelliteImageryAdapter,
    "water": CGWBGroundwaterAdapter,
}


def default_date_range(year: Optional[int] = None) -> tuple[str, str]:
    year = year or date.today().year - 1
    return f"{year}-01-01", f"{year}-12-31"


def acquire_field_data(field: Any, domains: Optional[Iterable[str]] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       mode: str = "live") -> Dict[str, Any]:
    """Acquire raw and processed data for one field.

    Network failures are handled by the existing adapters' offline fallbacks.
    Each result keeps both raw response metadata and normalized observations.
    """
    if mode not in {"live", "demo"}:
        raise ValueError("mode must be live or demo")
    selected = list(domains if domains is not None else ADAPTERS)
    start_date, end_date = (start_date, end_date) if start_date and end_date else default_date_range()
    results: Dict[str, Any] = {}
    for domain in selected:
        adapter_cls = ADAPTERS.get(domain)
        if not adapter_cls:
            results[domain] = {"status": "unsupported", "observations": []}
            continue
        adapter = adapter_cls()
        try:
            if mode == "demo":
                rep = field.geometry.representative_point()
                if domain == "soil":
                    from agri_data.sources.soilgrids import DEFAULT_PROPERTIES
                    raw = adapter._generate_synthetic_soilgrids_response(rep.x, rep.y, DEFAULT_PROPERTIES)
                elif domain == "climate":
                    raw = adapter._generate_synthetic_climate_response(rep.x, rep.y, start_date.replace("-", ""), end_date.replace("-", ""))
                else:
                    raw = adapter.retrieve(field.geometry, field_id=field.field_id, start_date=start_date, end_date=end_date)
            elif domain in {"water", "historical_land"}:
                raise RuntimeError("Live adapter is not implemented; existing adapter contains example data")
            else:
                # Legacy caches contain unlabelled synthetic responses: never trust them in live mode.
                rep = field.geometry.representative_point()
                if domain == "soil":
                    from agri_data.sources.soilgrids import DEFAULT_PROPERTIES, DEPTH_INTERVALS
                    response = requests.get(adapter.base_url.rstrip("/") + "/properties/query", params={"lon": rep.x, "lat": rep.y, "property": DEFAULT_PROPERTIES, "depth": DEPTH_INTERVALS}, timeout=30)
                else:
                    from agri_data.sources.nasa_power import DEFAULT_PARAMS
                    response = requests.get(adapter.base_url, params={"longitude": rep.x, "latitude": rep.y, "start": start_date.replace("-", ""), "end": end_date.replace("-", ""), "parameters": ",".join(DEFAULT_PARAMS), "community": "AG", "format": "JSON"}, timeout=30)
                response.raise_for_status()
                raw = response.json()
            payload = json.dumps(raw, sort_keys=True).encode()
            path = settings.raw_dir / mode / adapter.source_id / (hashlib.sha256(payload).hexdigest() + ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(payload)
            raw["_raw_file"] = str(path)
        except (RuntimeError, ValueError, OSError, requests.exceptions.RequestException) as exc:
            results[domain] = {"status": "unavailable", "reason": str(exc), "observations": []}
            continue
        processed = adapter.process(raw, field.geometry)
        processed["raw_file"] = str(path)
        processed["mode"] = mode
        processed["status"] = "synthetic" if mode == "demo" else "available"
        if mode == "demo":
            for observation in processed.get("observations", []):
                observation["measurement_type"] = "synthetic"
                observation["quality_flag"] = "SYNTHETIC"
        processed["valid"] = bool(adapter.validate(processed))
        results[domain] = processed
    return results
