#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3.pkgs.requests python3.pkgs.json5 nix.out

# Fetches the latest plugin metadata and hash for each plugin in the curated list.

from pathlib import Path
from requests import get
from argparse import ArgumentParser
from lib.util import serialize_to_file, deserialize_from_file
from concurrent.futures import ThreadPoolExecutor, as_completed
import json5
import logging
import subprocess

CONCURRENCY = 25
PLUGIN_IDS_FILE = Path(__file__).parent.parent.joinpath("./data/plugin-ids.jsonc").resolve()
PLUGINS_FILE = Path(__file__).parent.parent.joinpath("./data/cache/plugins.json").resolve()

FRIENDLY_TO_PLUGIN = {
    "clion": "CLION",
    "datagrip": "DBE",
    "goland": "GOLAND",
    "idea": "IDEA",
    "mps": "MPS",
    "phpstorm": "PHPSTORM",
    "pycharm": "PYCHARM",
    "pycharm-community": "PYCHARM_COMMUNITY",
    "rider": "RIDER",
    "ruby-mine": "RUBYMINE",
    "webstorm": "WEBSTORM",
    "rust-rover": "RUST",
    "dataspell": "DATASPELL",
}
PLUGIN_TO_FRIENDLY = {j: i for i, j in FRIENDLY_TO_PLUGIN.items()}


def get_latest_stable_platform():
    """Fetch the latest stable IDEA build and return its platform number."""
    resp = get(
        "https://data.services.jetbrains.com/products/releases",
        params={"code": "IU", "latest": "true", "type": "release"},
    )
    if resp.status_code != 200:
        logging.warning("Failed to fetch latest stable IDEA build, skipping platform check")
        return None
    data = resp.json()
    releases = data.get("IIU", [])
    if not releases:
        logging.warning("No stable IDEA releases found, skipping platform check")
        return None
    build = releases[0].get("build", "")
    platform = int(build.split(".")[0])
    logging.info("Latest stable IDEA platform: %d (build %s)", platform, build)
    return platform


def is_compatible_with_stable(since_build: str, latest_platform: int) -> bool:
    """Check if the plugin's minimum build is <= the latest stable platform."""
    try:
        since_platform = int(since_build.split(".")[0])
    except (ValueError, IndexError):
        return True
    return since_platform <= latest_platform


def read_plugin_ids() -> list[int]:
    with open(PLUGIN_IDS_FILE) as f:
        return json5.load(f)


def get_nix_hash(url: str) -> str:
    print(f"Downloading {url}")
    args = ["nix-prefetch-url", url, "--print-path"]
    if url.endswith(".zip"):
        args.append("--unpack")
    else:
        args.append("--executable")
    result = subprocess.run(args, capture_output=True, check=True)
    lines = result.stdout.decode().split("\n")
    if len(lines) < 2:
        raise ValueError("Unexpected output from nix-prefetch-url")
    path = lines[1].strip()
    hash_result = subprocess.run(
        ["nix", "--extra-experimental-features", "nix-command", "hash", "path", path],
        capture_output=True, check=True,
    )
    return hash_result.stdout.decode().strip()


def process_plugin(pid: int, old_data: dict, latest_platform: int | None) -> tuple[int, dict | None]:
    try:
        resp = get(f"https://plugins.jetbrains.com/api/plugins/{pid}")
        if resp.status_code != 200:
            logging.warning(f"Plugin {pid}: HTTP {resp.status_code}")
            return pid, None
        metadata = resp.json()
    except Exception as e:
        logging.error(f"Plugin {pid}: failed to fetch metadata: {e}")
        return pid, None

    try:
        resp = get(f"https://plugins.jetbrains.com/api/plugins/{pid}/updates")
        if resp.status_code != 200:
            logging.warning(f"Plugin {pid} updates: HTTP {resp.status_code}")
            return pid, None
        updates = resp.json()
    except Exception as e:
        logging.error(f"Plugin {pid}: failed to fetch updates: {e}")
        return pid, None

    if not updates:
        logging.warning(f"Plugin {pid}: no updates found")
        return pid, None

    if latest_platform is not None:
        for candidate in updates:
            since_build = candidate.get("since", "")
            if not since_build or is_compatible_with_stable(since_build, latest_platform):
                latest = candidate
                break
        else:
            logging.info(f"Plugin {pid}: no version compatible with platform {latest_platform}")
            return pid, None
    else:
        latest = updates[0]

    file_path = latest.get("file")
    if not file_path:
        logging.warning(f"Plugin {pid}: no download file")
        return pid, None

    url = f"https://plugins.jetbrains.com/files/{file_path}"

    try:
        resp = get(f"https://plugins.jetbrains.com/api/plugins/{pid}/compatible-products")
        if resp.status_code != 200:
            compatible = []
        else:
            codes = resp.json()
            compatible = sorted([PLUGIN_TO_FRIENDLY[c] for c in codes if c in PLUGIN_TO_FRIENDLY])
    except Exception:
        compatible = []

    if not compatible:
        logging.warning(f"Plugin {pid}: no compatible IDEs found")
        return pid, None

    # Reuse hash from old data if the URL hasn't changed
    existing = old_data.get(str(pid), {})
    existing_url = existing.get("url", "")
    existing_hash = existing.get("hash", "")

    if existing_url == url and existing_hash:
        fileHash = existing_hash
    else:
        try:
            fileHash = get_nix_hash(url)
        except Exception as e:
            logging.error(f"Plugin {pid}: failed to hash {url}: {e}")
            return pid, None

    return pid, {
        "id": pid,
        "key": metadata.get("xmlId", ""),
        "name": metadata.get("name", ""),
        "compatible": compatible,
        "version": latest.get("version", ""),
        "url": url,
        "hash": fileHash,
    }


def main():
    parser = ArgumentParser(description="Update plugin metadata and hashes")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    plugin_ids = read_plugin_ids()
    logging.info("Processing %d plugins", len(plugin_ids))

    latest_platform = get_latest_stable_platform()

    old_data = deserialize_from_file(PLUGINS_FILE) or {}

    result = {}
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(process_plugin, pid, old_data, latest_platform): pid for pid in plugin_ids}
        for future in as_completed(futures):
            pid, data = future.result()
            if data:
                result[str(pid)] = data

    reused = sum(1 for pid in plugin_ids if old_data.get(str(pid), {}).get("url", "") ==
                  result.get(str(pid), {}).get("url", "") and old_data.get(str(pid), {}).get("hash"))

    # Remove stale entries for plugins no longer in the curated list
    plugin_id_set = {str(pid) for pid in plugin_ids}
    stale_ids = [pid for pid in old_data if pid not in plugin_id_set]
    if stale_ids:
        logging.info("Removing %d stale plugin entries: %s", len(stale_ids), stale_ids)
        for pid in stale_ids:
            del old_data[pid]

    logging.info("Fetched %d/%d plugins (%d hashes reused)", len(result), len(plugin_ids), reused)
    sorted_result = dict(sorted(result.items(), key=lambda item: int(item[0])))
    serialize_to_file(sorted_result, PLUGINS_FILE)
    logging.info("Wrote %d plugins to %s", len(result), PLUGINS_FILE)


if __name__ == "__main__":
    main()
