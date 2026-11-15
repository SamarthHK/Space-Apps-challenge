"""Configuration-driven acquisition for all currently implemented adapters."""

from datetime import date, timedelta
from typing import Any, Dict, Iterable, Optional

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
                       end_date: Optional[str] = None) -> Dict[str, Any]:
    """Acquire raw and processed data for one field.

    Network failures are handled by the existing adapters' offline fallbacks.
    Each result keeps both raw response metadata and normalized observations.
    """
    selected = list(domains or ADAPTERS)
    start_date, end_date = (start_date, end_date) if start_date and end_date else default_date_range()
    results: Dict[str, Any] = {}
    for domain in selected:
        adapter_cls = ADAPTERS.get(domain)
        if not adapter_cls:
            results[domain] = {"status": "unsupported", "observations": []}
            continue
        adapter = adapter_cls()
        raw = adapter.retrieve(field.geometry, field_id=field.field_id,
                               start_date=start_date, end_date=end_date)
        processed = adapter.process(raw, field.geometry)
        processed["valid"] = bool(adapter.validate(processed))
        results[domain] = processed
    return results
