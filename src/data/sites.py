"""
Site configuration loading and validation module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.config import SITES_CONFIG_FILE


REQUIRED_SITE_FIELDS = {"site_id", "name", "latitude", "longitude", "climate_zone"}


def load_and_validate_sites(config_path: Path | str = SITES_CONFIG_FILE) -> List[Dict[str, Any]]:
    """
    Load site configuration from JSON file and validate all constraints.

    Validation rules:
    - File exists and is valid JSON
    - Exactly 5 sites present
    - Required fields present in each site
    - Unique site_id for each site
    - Unique (latitude, longitude) coordinate pairs
    - Valid latitude range [-90, 90]
    - Valid longitude range [-180, 180]

    Returns:
        List of validated site dicts.

    Raises:
        ValueError or FileNotFoundError if validation fails.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Site configuration file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            sites = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in site configuration file {path}: {exc}") from exc

    if not isinstance(sites, list):
        raise ValueError("Site configuration must be a JSON array of site objects.")

    if len(sites) != 5:
        raise ValueError(f"Expected exactly 5 sites in configuration, found {len(sites)}.")

    seen_site_ids = set()
    seen_coordinates = set()

    for idx, site in enumerate(sites):
        if not isinstance(site, dict):
            raise ValueError(f"Site entry at index {idx} is not a dictionary.")

        missing_fields = REQUIRED_SITE_FIELDS - set(site.keys())
        if missing_fields:
            raise ValueError(f"Site at index {idx} ({site.get('name', 'Unknown')}) missing required fields: {missing_fields}")

        site_id = site["site_id"]
        if site_id in seen_site_ids:
            raise ValueError(f"Duplicate site_id found: '{site_id}'")
        seen_site_ids.add(site_id)

        lat = site["latitude"]
        lon = site["longitude"]

        if not isinstance(lat, (int, float)) or not (-90.0 <= float(lat) <= 90.0):
            raise ValueError(f"Invalid latitude '{lat}' for site '{site_id}'. Must be numeric and between -90 and 90.")

        if not isinstance(lon, (int, float)) or not (-180.0 <= float(lon) <= 180.0):
            raise ValueError(f"Invalid longitude '{lon}' for site '{site_id}'. Must be numeric and between -180 and 180.")

        coord_pair = (round(float(lat), 6), round(float(lon), 6))
        if coord_pair in seen_coordinates:
            raise ValueError(f"Duplicate coordinates found for site '{site_id}': {coord_pair}")
        seen_coordinates.add(coord_pair)

    return sites
