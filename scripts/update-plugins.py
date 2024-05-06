#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3.pkgs.requests python3.pkgs.json5 nix.out

# This script updates the plugins plugins-latest.json with all plugins provided in the plugins.json config.


from json import load
import os
from pathlib import Path
from requests import get
from argparse import ArgumentParser
from common import read_plugins_config, get_plugin_info, get_plugin_updates, serialize_to_file, deserialize_from_file
from nixpkgslib import get_hash, get_nixpkgs_ides_versions, get_ide_versions, print_file_diff, pick_newest, is_compatible
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging


CONCURRENCY = 25
PLUGINS_LIST = Path(__file__).parent.parent.joinpath("./data/plugins.json").resolve()
PLUGINS_FILE = Path(__file__).parent.parent.joinpath("./data/cache/plugins-latest.json").resolve()
NIXPKGS_IDES_FILE = Path(__file__).parent.parent.joinpath("./data/cache/nixpkgs-ides-latest.json").resolve()
NIXOS_IDES_FILE = Path(__file__).parent.parent.joinpath("./data/cache/nixos-ides-latest.json").resolve()
FLAKE_LOCK_FILE = Path(__file__).parent.parent.joinpath("./flake.lock").resolve()

# The plugin compatibility system uses a different naming scheme to the ide update system.
# These dicts convert between them
FRIENDLY_TO_PLUGIN = {
    "clion": "CLION",
    "datagrip": "DBE",
    "goland": "GOLAND",
    "idea-community": "IDEA_COMMUNITY",
    "idea-ultimate": "IDEA",
    "mps": "MPS",
    "phpstorm": "PHPSTORM",
    "pycharm-community": "PYCHARM_COMMUNITY",
    "pycharm-professional": "PYCHARM",
    "rider": "RIDER",
    "ruby-mine": "RUBYMINE",
    "webstorm": "WEBSTORM",
    "rust-rover": "RUST",
}
PLUGIN_TO_FRIENDLY = {j: i for i, j in FRIENDLY_TO_PLUGIN.items()}


def get_newest_compatible(pid: str, build: str, plugin_infos: dict) -> [None, str]:
    newest_ver = None
    newest_index = None
    for index, info in enumerate(plugin_infos):
        if pick_newest(newest_ver, info["version"]) != newest_ver and is_compatible(build, info["since"], info["until"]):
            newest_ver = info["version"]
            newest_index = index

    if newest_ver is not None:
        return "https://plugins.jetbrains.com/files/" + plugin_infos[newest_index]["file"]
    else:
        logging.debug(f"Could not find version of plugin {pid} compatible with build {build}")
        return None


def flatten(main_list: list[list]) -> list:
    return [item for sublist in main_list for item in sublist]


def get_compatible_ides(pid: int) -> list[str]:
    url = f"https://plugins.jetbrains.com/api/plugins/{pid}/compatible-products"
    result = get(url).json()
    return sorted([PLUGIN_TO_FRIENDLY[i] for i in result if i in PLUGIN_TO_FRIENDLY])


def sort_dict(to_sort: dict) -> dict:
    return {i: to_sort[i] for i in sorted(to_sort.keys())}


def process_plugin(plugin, plugin_infos, ide_versions, extra_builds):
    try:
        pid = plugin["id"]
        plugin_versions = {
            "compatible": get_compatible_ides(pid),
            "builds": {},
            "key": plugin["key"],
            "name": plugin["name"],
            "slug": plugin["slug"],
        }

        if pid not in plugin_infos:
            logging.warning(f"Could not find plugin info for plugin {pid} [{plugin['key']}]")
            return pid, None

        relevant_builds = [builds for ide, builds in ide_versions.items() if ide in plugin_versions["compatible"]] + [extra_builds]
        relevant_builds = sorted(list(set(flatten(relevant_builds))))  # Flatten, remove duplicates and sort
        for build in relevant_builds:
            plugin_versions["builds"][build] = get_newest_compatible(pid, build, plugin_infos[pid])

        if not plugin_versions["builds"]:
            logging.warning(f"Could not find any compatible builds for plugin {pid} [{plugin['key']}]")
            return pid, None
        if not any(build is not None for build in plugin_versions["builds"].values()):
            logging.warning(f"Could not find any compatible builds for plugin {pid} [{plugin['key']}]")
            return pid, None
    except Exception as e:
        logging.error(f"Failed to process plugin {pid} [{plugin['key']}]: {e}")
        return pid, None

    return pid, plugin_versions


def make_plugin_files(plugins: list, plugin_infos: dict, ide_versions, extra_builds, old_plugins):
    plugins = [plugin for plugin in plugins if plugin["id"] in plugin_infos]

    result = {}
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(process_plugin, plugin, plugin_infos, ide_versions, extra_builds): plugin for plugin in plugins}
        for future in as_completed(futures):
            res = future.result()
            if res:
                plugin_id, plugin_versions = res
                if plugin_versions is not None:
                    result[plugin_id] = plugin_versions

    # keep old plugins
    for plugin_id, data in old_plugins.items():
        if plugin_id not in result and data is not None:
            result[plugin_id] = data

    return result


def get_file_hashes(file_list: list[str], old_hashes: dict[str, str], refetch_all: bool) -> dict[str, str]:
    old = {} if refetch_all else old_hashes
    print_file_diff(list(old.keys()), file_list)

    file_hashes = {}
    for file in sorted(file_list):
        if file in old:
            file_hashes[file] = old[file]
        else:
            file_hashes[file] = get_hash(file)
    return file_hashes


def get_args() -> tuple[list[str], list[str], bool, bool, list[str]]:
    parser = ArgumentParser(
        description="Add/remove/update entries in plugins.json",
        epilog="To update all plugins, run with no args.\n"
               "To add a version of a plugin from a different channel, append -[channel] to the id.\n"
               "The id of a plugin is the number before the name in the address of its page on https://plugins.jetbrains.com/"
    )
    parser.add_argument("-r", "--refetch-all", action="store_true",
                        help="don't use previously collected hashes, redownload all")
    parser.add_argument("-w", "--with-build", action="append", default=[],
                        help="append [builds] to the list of builds to fetch plugin versions for")
    args = parser.parse_args()

    return args.refetch_all, args.with_build


def get_file_names(plugins: dict[str, dict]) -> list[str]:
    result = []
    for plugin_info in plugins.values():
        if plugin_info is None:
            continue

        for url in plugin_info["builds"].values():
            if url is not None:
                result.append(url)

    return list(set(result))


def get_plugin_info(plugin):
    plugin_id = plugin["id"]  
    plugin_channel = plugin.get("channel", "")

    try:
        resp = get_plugin_updates(plugin_id, plugin_channel)
        return plugin_id, resp
    except Exception as e:
        logging.error(f"Failed to get plugin info for plugin {plugin_id}: {e}")
        return plugin_id, None


def get_plugin_infos(plugins: dict) -> dict:
    result = {}
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(get_plugin_info, plugin): plugin for plugin in plugins}
        for future in as_completed(futures):
            plugin_id, updates = future.result()
            if updates is not None:
                result[plugin_id] = updates
    return result


def process_chunk(result: dict, plugins, chunk, ide_versions, extra_builds, refetch_all: bool) -> dict:
    # plugin infoo
    plugin_infos = get_plugin_infos(chunk)

    # plugins file
    result["plugins"] = make_plugin_files(plugins, plugin_infos, ide_versions, extra_builds, result["plugins"])
    result["plugins"] = {int(k): v for k, v in sorted(result["plugins"].items(), key=lambda item: int(item[0]))}

    # file hashes
    logging.info("Calculating missing file hashes")
    file_list = get_file_names(result["plugins"])
    result["files"] = get_file_hashes(file_list, result["files"], refetch_all)

    return result


def main():
    refetch_all, extra_builds = get_args()
    result = deserialize_from_file(PLUGINS_FILE)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info("Downloading IDE versions from nixpkgs")
    get_nixpkgs_ides_versions()

    logging.info(f"Loading plugins from config")
    plugins = read_plugins_config()

    logging.info(f"Query IDEs for plugin compatibility")
    ide_versions = get_ide_versions()

    # process plugins in chunks to avoid losing all progress on a crash
    CHUNK_SIZE=250
    logging.info(f"Processing {len(plugins)} plugins in {len(plugins) // CHUNK_SIZE + 1} chunks")
    for i in range(0, len(plugins), CHUNK_SIZE):
        logging.info(f"Processing plugins {i} to {i + CHUNK_SIZE}")
        chunk = plugins[i:i + CHUNK_SIZE]
        result = process_chunk(result, plugins, chunk, ide_versions, extra_builds, refetch_all)

        # save progress
        logging.info("Writing progress to file")
        serialize_to_file(result, PLUGINS_FILE)


if __name__ == '__main__':
    main()
