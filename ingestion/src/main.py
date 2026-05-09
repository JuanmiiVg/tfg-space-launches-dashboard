import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from urllib3.util.retry import Retry


def env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError:
        return default


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def stable_int(value: str, minimum: int = 1000, span: int = 900000) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return minimum + (int(digest[:8], 16) % span)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def create_session(timeout_seconds: int) -> tuple[requests.Session, int]:
    session = requests.Session()
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=2.0,  # Exponential backoff: 2s, 4s, 8s
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        respect_retry_after_header=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session, timeout_seconds


def ensure_output_dir(base_dir: str) -> Path:
    run_folder = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = Path(base_dir) / run_folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_launch_library_cursor(
    cursor_file: Path,
    base_url: str,
    reset_cursor: bool,
) -> str:
    if reset_cursor or not cursor_file.exists():
        return base_url

    try:
        with cursor_file.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        cursor = payload.get("next_url")
        if isinstance(cursor, str) and cursor.strip():
            return cursor.strip()
    except (OSError, json.JSONDecodeError):
        pass

    return base_url


def save_launch_library_cursor(
    cursor_file: Path,
    next_url: str | None,
    base_url: str,
    pages_fetched: int,
    launches_fetched: int,
    was_rate_limited: bool,
) -> None:
    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "next_url": next_url if next_url else base_url,
        "pages_fetched": pages_fetched,
        "launches_fetched": launches_fetched,
        "was_rate_limited": was_rate_limited,
    }
    write_json(cursor_file, payload)


def compact_launch_record(launch: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields required by Silver/Gold processing and image extraction."""
    status = launch.get("status") or {}
    provider = launch.get("launch_service_provider") or {}
    rocket = launch.get("rocket") or {}
    rocket_cfg = rocket.get("configuration") or {}
    mission = launch.get("mission") or {}
    orbit = mission.get("orbit") or {}
    pad = launch.get("pad") or {}
    location = pad.get("location") or {}

    return {
        "id": launch.get("id"),
        "name": launch.get("name"),
        "net": launch.get("net"),
        "type": launch.get("type"),
        "image": launch.get("image"),
        "infographic": launch.get("infographic"),
        "status": {
            "id": status.get("id"),
            "name": status.get("name"),
            "abbrev": status.get("abbrev"),
        },
        "launch_service_provider": {
            "id": provider.get("id"),
            "name": provider.get("name"),
        },
        "rocket": {
            "id": rocket.get("id"),
            "configuration": {
                "id": rocket_cfg.get("id"),
                "name": rocket_cfg.get("name"),
                "family": rocket_cfg.get("family"),
            },
        },
        "mission": {
            "id": mission.get("id"),
            "name": mission.get("name"),
            "type": mission.get("type"),
            "orbit": {"name": orbit.get("name")},
        },
        "pad": {
            "id": pad.get("id"),
            "name": pad.get("name"),
            "country_code": pad.get("country_code"),
            "latitude": pad.get("latitude"),
            "longitude": pad.get("longitude"),
            "location": {
                "name": location.get("name"),
                "country_code": location.get("country_code"),
            },
        },
    }


def fetch_launch_library(
    session: requests.Session,
    timeout_seconds: int,
    start_url: str,
    page_limit: int,
    max_pages: int,
) -> tuple[list[dict[str, Any]], str | None, bool, int]:
    launches: list[dict[str, Any]] = []
    next_url = start_url
    current_page = 0
    was_rate_limited = False

    while next_url:
        if max_pages > 0 and current_page >= max_pages:
            break

        # Add delay between requests to respect rate limiting
        if current_page > 0:
            time.sleep(5.0)  # 5 seconds between requests (aggressive rate limiting)

        params = {"limit": page_limit}
        response = session.get(next_url, params=params, timeout=timeout_seconds)
        try:
            response.raise_for_status()
        except HTTPError:
            if response.status_code == 429:
                was_rate_limited = True
                print(
                    "[ingestion] ⚠️  Launch Library respondió 429 Too Many Requests. "
                    "Se mantiene cursor para siguiente lote y se usa fallback."
                )
                break
            raise
        payload = response.json()
        results = payload.get("results", [])
        if not results:
            break

        compacted_results = [compact_launch_record(row) for row in results]
        launches.extend(compacted_results)
        next_url = payload.get("next")
        current_page += 1
        print(
            f"[ingestion] Launch Library página {current_page}: +{len(compacted_results)} "
            f"(acumulado={len(launches)})"
        )

    return launches, next_url, was_rate_limited, current_page


def fetch_spacex_generic(
    session: requests.Session,
    timeout_seconds: int,
    url: str,
    label: str,
) -> list[dict[str, Any]]:
    response = session.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        print(f"[ingestion] {label}: {len(data)} registros")
        return data
    return [data] if data else []


def fetch_spacex_rockets(
    session: requests.Session,
    timeout_seconds: int,
    rockets_url: str,
) -> list[dict[str, Any]]:
    return fetch_spacex_generic(session, timeout_seconds, rockets_url, "SpaceX rockets")


def fetch_spacex_launchpads(
    session: requests.Session,
    timeout_seconds: int,
    launchpads_url: str,
) -> dict[str, dict[str, Any]]:
    response = session.get(launchpads_url, timeout=timeout_seconds)
    response.raise_for_status()
    launchpads = response.json()

    coords_by_pad_id: dict[str, dict[str, Any]] = {}
    for pad in launchpads:
        pad_id = pad.get("id")
        if not pad_id:
            continue
        coords_by_pad_id[pad_id] = {
            "name": pad.get("name"),
            "country_code": pad.get("country_code"),
            "latitude": pad.get("latitude"),
            "longitude": pad.get("longitude"),
            "locality": pad.get("locality"),
            "region": pad.get("region"),
        }

    return coords_by_pad_id


def fetch_spacex_launch_catalog(
    session: requests.Session,
    timeout_seconds: int,
    launches_query_url: str,
    page_size: int,
    max_pages: int,
) -> list[dict[str, Any]]:
    launch_catalog: list[dict[str, Any]] = []

    page = 1
    while True:
        if max_pages > 0 and page > max_pages:
            break

        if page > 1:
            time.sleep(1.0)

        payload = {
            "query": {},
            "options": {
                "page": page,
                "limit": page_size,
                "sort": {"date_utc": "asc"},
                "pagination": True,
            },
        }

        response = session.post(launches_query_url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()

        docs = data.get("docs", [])
        if not docs:
            break

        launch_catalog.extend(docs)

        if not data.get("hasNextPage"):
            break
        page += 1

    print(f"[ingestion] SpaceX catálogo de lanzamientos: {len(launch_catalog)}")
    return launch_catalog


def fetch_spacex_launches_with_images(
    session: requests.Session,
    timeout_seconds: int,
    launches_query_url: str,
    page_size: int,
    max_pages: int,
) -> list[dict[str, Any]]:
    launches_with_images: list[dict[str, Any]] = []

    page = 1
    while True:
        if max_pages > 0 and page > max_pages:
            break

        # Add delay between requests to respect rate limiting
        if page > 1:
            time.sleep(1.0)  # 1 second between requests

        payload = {
            "query": {},
            "options": {
                "page": page,
                "limit": page_size,
                "sort": {"date_utc": "asc"},
                "pagination": True,
            },
        }

        response = session.post(launches_query_url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()

        docs = data.get("docs", [])
        if not docs:
            break

        for launch in docs:
            links = launch.get("links") or {}
            patch = links.get("patch") or {}
            reddit = links.get("reddit") or {}
            flickr = links.get("flickr") or {}

            image_urls = []
            if patch.get("small"):
                image_urls.append(patch["small"])
            if patch.get("large"):
                image_urls.append(patch["large"])
            image_urls.extend(flickr.get("original") or [])

            if not image_urls:
                continue

            launches_with_images.append(
                {
                    "spacex_launch_id": launch.get("id"),
                    "name": launch.get("name"),
                    "date_utc": launch.get("date_utc"),
                    "success": launch.get("success"),
                    "rocket_id": launch.get("rocket"),
                    "webcast": links.get("webcast"),
                    "wikipedia": links.get("wikipedia"),
                    "article": links.get("article"),
                    "reddit_campaign": reddit.get("campaign"),
                    "image_urls": image_urls,
                }
            )

        if not data.get("hasNextPage"):
            break
        print(
            f"[ingestion] SpaceX imágenes página {page}: "
            f"acumulado={len(launches_with_images)}"
        )
        page += 1

    return launches_with_images


def derive_mission_profile(launch_name: str, variant_index: int) -> tuple[str, str]:
    normalized_name = launch_name.lower()

    if "starlink" in normalized_name:
        return "Satellite Deployment", "LEO"
    if "crew" in normalized_name or "dragon" in normalized_name:
        return "Crewed Mission", "LEO"
    if "crs" in normalized_name or "cargo" in normalized_name:
        return "Cargo Resupply", "LEO"
    if "transport" in normalized_name:
        return "Ride Share", "LEO"
    if "starship" in normalized_name or "booster" in normalized_name:
        return "Test Flight", "Suborbital"
    if "gps" in normalized_name or "nrol" in normalized_name or "military" in normalized_name:
        return "Government Payload", "MEO"
    if (
        "planet" in normalized_name
        or "eutelsat" in normalized_name
        or "intelsat" in normalized_name
        or "communications" in normalized_name
    ):
        return "Communications", "GTO"
    if variant_index % 5 == 0:
        return "Technology Demonstration", "LEO"
    return "Orbital Launch", "LEO"


def build_synthetic_launch_record(
    seed_launch: dict[str, Any],
    seed_index: int,
    variant_index: int,
    launchpads_by_id: dict[str, dict[str, Any]],
    rockets_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    seed_id = str(seed_launch.get("id") or f"seed-{seed_index}")
    seed_name = str(seed_launch.get("name") or "Synthetic Launch")
    seed_date = parse_datetime(seed_launch.get("date_utc")) or datetime.now(tz=timezone.utc)
    launchpad_id = str(seed_launch.get("launchpad") or "")
    rocket_id = str(seed_launch.get("rocket") or "")
    launchpad = launchpads_by_id.get(launchpad_id, {})
    rocket = rockets_by_id.get(rocket_id, {})
    links = seed_launch.get("links") or {}
    patch = links.get("patch") or {}
    flickr = links.get("flickr") or {}
    image_candidates = [patch.get("small"), patch.get("large")]
    image_candidates.extend(flickr.get("original") or [])
    image_candidates = [candidate for candidate in image_candidates if candidate]

    synthetic_date = seed_date + timedelta(days=(variant_index * 14) + (seed_index % 11), hours=seed_index % 24)
    synthetic_date = synthetic_date.astimezone(timezone.utc)
    synthetic_name = f"{seed_name} Synthetic Batch {variant_index:03d}"
    mission_type, mission_orbit = derive_mission_profile(synthetic_name, variant_index)
    synthetic_success = seed_launch.get("success")
    if synthetic_success is None:
        synthetic_success = variant_index % 4 != 0

    pad_latitude = launchpad.get("latitude")
    pad_longitude = launchpad.get("longitude")
    if pad_latitude is None or pad_longitude is None:
        pad_latitude = 25.997
        pad_longitude = -97.155

    return {
        "id": f"synthetic-{seed_id}-{variant_index:04d}",
        "name": synthetic_name,
        "net": synthetic_date.isoformat().replace("+00:00", "Z"),
        "type": "launch",
        "image": image_candidates[0] if image_candidates else None,
        "infographic": image_candidates[1] if len(image_candidates) > 1 else None,
        "status": {
            "id": 3 if synthetic_success else 4,
            "name": "Launch Successful" if synthetic_success else "Launch Failure",
            "abbrev": "Success" if synthetic_success else "Failure",
        },
        "launch_service_provider": {
            "id": 121,
            "name": "SpaceX",
        },
        "rocket": {
            "id": stable_int(rocket_id or seed_id, 2000, 800000),
            "configuration": {
                "id": stable_int(f"{rocket_id or seed_id}:configuration", 2000, 800000),
                "name": rocket.get("name") or seed_name,
                "family": rocket.get("type") or rocket.get("name") or "Falcon",
            },
        },
        "mission": {
            "id": stable_int(f"{seed_id}:{variant_index}:mission", 2000, 800000),
            "name": synthetic_name,
            "type": mission_type,
            "orbit": {"name": mission_orbit},
        },
        "pad": {
            "id": stable_int(launchpad_id or seed_id, 2000, 800000),
            "name": launchpad.get("name") or "SpaceX Launch Site",
            "country_code": launchpad.get("country_code") or "US",
            "latitude": pad_latitude,
            "longitude": pad_longitude,
            "location": {
                "name": launchpad.get("name") or "SpaceX Launch Site",
                "country_code": launchpad.get("country_code") or "US",
            },
        },
    }


def build_synthetic_launch_library_records(
    real_launches: list[dict[str, Any]],
    seed_launches: list[dict[str, Any]],
    launchpads_by_id: dict[str, dict[str, Any]],
    rockets_by_id: dict[str, dict[str, Any]],
    target_count: int,
) -> list[dict[str, Any]]:
    if target_count <= len(real_launches):
        return real_launches

    if not seed_launches:
        return real_launches

    launches = list(real_launches)
    extra_needed = target_count - len(real_launches)

    for synthetic_index in range(extra_needed):
        seed_launch = seed_launches[synthetic_index % len(seed_launches)]
        variant_index = synthetic_index // len(seed_launches) + 1
        launches.append(
            build_synthetic_launch_record(
                seed_launch,
                synthetic_index,
                variant_index,
                launchpads_by_id,
                rockets_by_id,
            )
        )

    return launches


def build_spacex_weather_targets(
    session: requests.Session,
    timeout_seconds: int,
    launches_query_url: str,
    launchpads_url: str,
    page_size: int,
    max_pages: int,
) -> list[dict[str, Any]]:
    launchpads_coords = fetch_spacex_launchpads(session, timeout_seconds, launchpads_url)
    weather_targets: list[dict[str, Any]] = []

    page = 1
    while True:
        if max_pages > 0 and page > max_pages:
            break

        if page > 1:
            time.sleep(1.0)

        payload = {
            "query": {},
            "options": {
                "page": page,
                "limit": page_size,
                "sort": {"date_utc": "asc"},
                "pagination": True,
                "select": ["id", "date_utc", "launchpad"],
            },
        }

        response = session.post(launches_query_url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()

        docs = data.get("docs", [])
        if not docs:
            break

        for launch in docs:
            launchpad_id = launch.get("launchpad")
            coords = launchpads_coords.get(launchpad_id or "", {})

            weather_targets.append(
                {
                    "id": launch.get("id"),
                    "net": launch.get("date_utc"),
                    "pad": {
                        "latitude": coords.get("latitude"),
                        "longitude": coords.get("longitude"),
                    },
                }
            )

        if not data.get("hasNextPage"):
            break
        page += 1

    print(f"[ingestion] SpaceX targets para clima: {len(weather_targets)}")
    return weather_targets


def build_launch_library_images(launches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    image_rows: list[dict[str, Any]] = []

    for launch in launches:
        image = launch.get("image")
        infographic = launch.get("infographic")
        if not image and not infographic:
            continue

        image_rows.append(
            {
                "launch_library_id": launch.get("id"),
                "name": launch.get("name"),
                "net": launch.get("net"),
                "image": image,
                "infographic": infographic,
            }
        )

    return image_rows


def fetch_open_meteo_samples(
    session: requests.Session,
    timeout_seconds: int,
    open_meteo_url: str,
    launches: list[dict[str, Any]],
    max_requests: int,
) -> list[dict[str, Any]]:
    weather_samples: list[dict[str, Any]] = []
    weather_index = 0

    for launch in launches:
        if max_requests > 0 and weather_index >= max_requests:
            break

        # Add delay between requests to respect rate limiting
        if weather_index > 0:
            time.sleep(0.5)  # 0.5 seconds between requests

        launch_id = launch.get("id")
        net = launch.get("net")
        pad = launch.get("pad") or {}
        latitude = pad.get("latitude")
        longitude = pad.get("longitude")

        if not net or latitude is None or longitude is None:
            continue

        date = normalize_date(net)
        if not date:
            continue

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": date,
            "end_date": date,
            "daily": "temperature_2m_mean,wind_speed_10m_max",
            "timezone": "UTC",
        }

        try:
            response = session.get(open_meteo_url, params=params, timeout=timeout_seconds)
            response.raise_for_status()
        except HTTPError:
            if response.status_code == 429:
                print(
                    f"[ingestion] ⚠️  Open-Meteo respondió 429 Too Many Requests. "
                    f"Se detiene extracción de clima (acumulado={weather_index} muestras)."
                )
                break
            raise

        weather_samples.append(
            {
                "launch_id": launch_id,
                "date": date,
                "latitude": latitude,
                "longitude": longitude,
                "weather": response.json(),
            }
        )
        weather_index += 1

        if weather_index % 25 == 0:
            print(f"[ingestion] Open-Meteo progreso: {weather_index} muestras")

    return weather_samples


def normalize_date(net_value: str) -> str | None:
    try:
        dt = datetime.fromisoformat(net_value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    launch_library_base_url = os.getenv(
        "LAUNCH_LIBRARY_BASE_URL", "https://ll.thespacedevs.com/2.2.0/launch/"
    )
    spacex_rockets_url = os.getenv(
        "SPACEX_ROCKETS_URL", "https://api.spacexdata.com/v4/rockets"
    )
    spacex_launches_query_url = os.getenv(
        "SPACEX_LAUNCHES_QUERY_URL", "https://api.spacexdata.com/v5/launches/query"
    )
    spacex_launchpads_url = os.getenv(
        "SPACEX_LAUNCHPADS_URL", "https://api.spacexdata.com/v4/launchpads"
    )
    spacex_payloads_url = os.getenv(
        "SPACEX_PAYLOADS_URL", "https://api.spacexdata.com/v4/payloads"
    )
    spacex_cores_url = os.getenv(
        "SPACEX_CORES_URL", "https://api.spacexdata.com/v4/cores"
    )
    spacex_ships_url = os.getenv(
        "SPACEX_SHIPS_URL", "https://api.spacexdata.com/v4/ships"
    )
    open_meteo_archive_url = os.getenv(
        "OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive"
    )
    output_dir = os.getenv("OUTPUT_DIR", "/app/data/raw")
    launch_library_batch_mode = env_bool("LAUNCH_LIBRARY_BATCH_MODE", True)
    launch_library_reset_cursor = env_bool("LAUNCH_LIBRARY_RESET_CURSOR", False)
    launch_library_synthetic_mode = env_bool("LAUNCH_LIBRARY_SYNTHETIC_MODE", True)
    launch_library_cursor_file = Path(
        os.getenv("LAUNCH_LIBRARY_CURSOR_FILE", f"{output_dir}/.launch_library_cursor.json")
    )

    launch_library_limit = env_int("LAUNCH_LIBRARY_LIMIT", 100)
    launch_library_max_pages = env_int("LAUNCH_LIBRARY_MAX_PAGES", 200)
    launch_library_synthetic_target = env_int("LAUNCH_LIBRARY_SYNTHETIC_TARGET", 1000)
    spacex_launches_page_size = env_int("SPACEX_LAUNCHES_PAGE_SIZE", 100)
    spacex_launches_max_pages = env_int("SPACEX_LAUNCHES_MAX_PAGES", 200)
    weather_max_requests = env_int("WEATHER_MAX_REQUESTS", 500)
    timeout_seconds = env_int("REQUEST_TIMEOUT_SECONDS", 30)

    session, timeout = create_session(timeout_seconds)
    run_path = ensure_output_dir(output_dir)

    print("[ingestion] Iniciando extracción de datos...")

    # Try Launch Library with fallback
    launches = []
    launch_library_images = []
    launch_library_next_url: str | None = launch_library_base_url
    launch_library_was_rate_limited = False
    launch_library_pages_fetched = 0
    launch_library_real_launches: list[dict[str, Any]] = []

    launch_library_start_url = launch_library_base_url
    if launch_library_batch_mode:
        launch_library_start_url = load_launch_library_cursor(
            launch_library_cursor_file,
            launch_library_base_url,
            launch_library_reset_cursor,
        )
        print(f"[ingestion] Launch Library cursor inicial: {launch_library_start_url}")

    try:
        (
            launch_library_real_launches,
            launch_library_next_url,
            launch_library_was_rate_limited,
            launch_library_pages_fetched,
        ) = fetch_launch_library(
            session,
            timeout,
            launch_library_start_url,
            launch_library_limit,
            launch_library_max_pages,
        )
        print(
            f"[ingestion] Launch Library extraído: {len(launch_library_real_launches)} lanzamientos"
        )
    except Exception as e:
        print(f"[ingestion] ⚠️  Launch Library falló (saltando): {e}")
        launch_library_real_launches = []
    finally:
        if launch_library_batch_mode:
            save_launch_library_cursor(
                launch_library_cursor_file,
                launch_library_next_url,
                launch_library_base_url,
                launch_library_pages_fetched,
                len(launch_library_real_launches),
                launch_library_was_rate_limited,
            )

    rockets = fetch_spacex_rockets(session, timeout, spacex_rockets_url)
    rockets_by_id = {str(rocket.get("id")): rocket for rocket in rockets if rocket.get("id") is not None}

    payloads = fetch_spacex_generic(session, timeout, spacex_payloads_url, "SpaceX payloads")
    cores = fetch_spacex_generic(session, timeout, spacex_cores_url, "SpaceX cores")
    ships = fetch_spacex_generic(session, timeout, spacex_ships_url, "SpaceX ships")

    launchpads_by_id = fetch_spacex_launchpads(session, timeout, spacex_launchpads_url)

    if launch_library_synthetic_mode:
        spacex_launch_catalog = fetch_spacex_launch_catalog(
            session,
            timeout,
            spacex_launches_query_url,
            spacex_launches_page_size,
            spacex_launches_max_pages,
        )
        launches = build_synthetic_launch_library_records(
            launch_library_real_launches,
            spacex_launch_catalog,
            launchpads_by_id,
            rockets_by_id,
            launch_library_synthetic_target,
        )
        synthetic_added = len(launches) - len(launch_library_real_launches)
        print(
            f"[ingestion] Synthetic mode activo: +{synthetic_added} lanzamientos "
            f"(objetivo={launch_library_synthetic_target})"
        )
    else:
        launches = list(launch_library_real_launches)

    launch_library_images = build_launch_library_images(launches)
    print(f"[ingestion] Launch Library imágenes: {len(launch_library_images)}")
    
    spacex_launches_images = fetch_spacex_launches_with_images(
        session,
        timeout,
        spacex_launches_query_url,
        spacex_launches_page_size,
        spacex_launches_max_pages,
    )
    print(
        f"[ingestion] SpaceX lanzamientos con imágenes: {len(spacex_launches_images)}"
    )

    weather_samples = fetch_open_meteo_samples(
        session,
        timeout,
        open_meteo_archive_url,
        launches
        if launches
        else build_spacex_weather_targets(
            session,
            timeout,
            spacex_launches_query_url,
            spacex_launchpads_url,
            spacex_launches_page_size,
            spacex_launches_max_pages,
        ),
        weather_max_requests,
    )
    print(f"[ingestion] Open-Meteo extraído: {len(weather_samples)} muestras")

    # Write outputs
    if launches:
        write_jsonl(run_path / "launch_library_launches.jsonl", launches)
    if launch_library_images:
        write_jsonl(run_path / "launch_library_images.jsonl", launch_library_images)
    write_json(run_path / "spacex_rockets.json", rockets)
    write_json(run_path / "spacex_payloads.json", payloads)
    write_json(run_path / "spacex_cores.json", cores)
    write_json(run_path / "spacex_ships.json", ships)
    write_jsonl(run_path / "spacex_launches_images.jsonl", spacex_launches_images)
    if weather_samples:
        write_jsonl(run_path / "open_meteo_samples.jsonl", weather_samples)

    manifest = {
        "executed_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "files": {
            "launch_library_launches.jsonl": len(launches),
            "launch_library_images.jsonl": len(launch_library_images),
            "spacex_rockets.json": len(rockets),
            "spacex_payloads.json": len(payloads),
            "spacex_cores.json": len(cores),
            "spacex_ships.json": len(ships),
            "spacex_launches_images.jsonl": len(spacex_launches_images),
            "open_meteo_samples.jsonl": len(weather_samples),
        },
        "config": {
            "launch_library_limit": launch_library_limit,
            "launch_library_max_pages": launch_library_max_pages,
            "launch_library_batch_mode": launch_library_batch_mode,
            "launch_library_synthetic_mode": launch_library_synthetic_mode,
            "launch_library_synthetic_target": launch_library_synthetic_target,
            "spacex_launches_page_size": spacex_launches_page_size,
            "spacex_launches_max_pages": spacex_launches_max_pages,
            "weather_max_requests": weather_max_requests,
            "request_timeout_seconds": timeout_seconds,
        },
    }

    write_json(run_path / "manifest.json", manifest)
    print(f"[ingestion] Finalizado. Salida en: {run_path}")


if __name__ == "__main__":
    main()
