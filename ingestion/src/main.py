import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError:
        return default


def create_session(timeout_seconds: int) -> tuple[requests.Session, int]:
    session = requests.Session()
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=2.0,  # Exponential backoff: 2s, 4s, 8s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
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


def fetch_launch_library(
    session: requests.Session,
    timeout_seconds: int,
    base_url: str,
    page_limit: int,
    max_pages: int,
) -> list[dict[str, Any]]:
    launches: list[dict[str, Any]] = []
    next_url = base_url
    current_page = 0

    while next_url:
        if max_pages > 0 and current_page >= max_pages:
            break

        # Add delay between requests to respect rate limiting
        if current_page > 0:
            time.sleep(5.0)  # 5 seconds between requests (aggressive rate limiting)

        params = {"limit": page_limit}
        response = session.get(next_url, params=params, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results", [])
        if not results:
            break

        launches.extend(results)
        next_url = payload.get("next")
        current_page += 1

    return launches


def fetch_spacex_rockets(
    session: requests.Session,
    timeout_seconds: int,
    rockets_url: str,
) -> list[dict[str, Any]]:
    response = session.get(rockets_url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()


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
        page += 1

    return launches_with_images


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

        response = session.get(open_meteo_url, params=params, timeout=timeout_seconds)
        response.raise_for_status()

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
    open_meteo_archive_url = os.getenv(
        "OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive"
    )
    output_dir = os.getenv("OUTPUT_DIR", "/app/data/raw")

    launch_library_limit = env_int("LAUNCH_LIBRARY_LIMIT", 100)
    launch_library_max_pages = env_int("LAUNCH_LIBRARY_MAX_PAGES", 200)
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
    try:
        launches = fetch_launch_library(
            session,
            timeout,
            launch_library_base_url,
            launch_library_limit,
            launch_library_max_pages,
        )
        print(f"[ingestion] Launch Library extraído: {len(launches)} lanzamientos")
        launch_library_images = build_launch_library_images(launches)
        print(f"[ingestion] Launch Library imágenes: {len(launch_library_images)}")
    except Exception as e:
        print(f"[ingestion] ⚠️  Launch Library falló (saltando): {e}")
        launches = []

    rockets = fetch_spacex_rockets(session, timeout, spacex_rockets_url)
    print(f"[ingestion] SpaceX cohetes extraído: {len(rockets)}")
    
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
        launches if launches else spacex_launches_images,  # Use SpaceX as fallback
        weather_max_requests,
    )
    print(f"[ingestion] Open-Meteo extraído: {len(weather_samples)} muestras")

    # Write outputs
    if launches:
        write_jsonl(run_path / "launch_library_launches.jsonl", launches)
    if launch_library_images:
        write_jsonl(run_path / "launch_library_images.jsonl", launch_library_images)
    write_json(run_path / "spacex_rockets.json", rockets)
    write_jsonl(run_path / "spacex_launches_images.jsonl", spacex_launches_images)
    write_jsonl(run_path / "open_meteo_samples.jsonl", weather_samples)

    manifest = {
        "executed_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "files": {
            "launch_library_launches.jsonl": len(launches),
            "launch_library_images.jsonl": len(launch_library_images),
            "spacex_rockets.json": len(rockets),
            "spacex_launches_images.jsonl": len(spacex_launches_images),
            "open_meteo_samples.jsonl": len(weather_samples),
        },
        "config": {
            "launch_library_limit": launch_library_limit,
            "launch_library_max_pages": launch_library_max_pages,
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
