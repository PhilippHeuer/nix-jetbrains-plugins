from json import load, dumps
import json
import os
import json5
from pathlib import Path
from requests import get


PLUGINS_LIST = Path(__file__).parent.parent.joinpath("./data/plugins.json").resolve()


def read_plugins_config() -> list[dict]:
    plugins_data = json5.load(open(PLUGINS_LIST))["plugins"]
    return sort_plugins(plugins_data)


def write_plugins_config(plugins: list[dict]):
    data = {"plugins": sort_plugins(plugins)}
    with open(PLUGINS_LIST, "w") as f:
        f.write(dumps(data, indent=2))
        f.write("\n")


def sort_plugins(plugins: list[dict]) -> list[dict]:
    return sorted(plugins, key=lambda x: int(x["id"]))


def get_plugin_info(pid: str, channel: str) -> dict:
    url = f"https://plugins.jetbrains.com/api/plugins/{pid}"
    resp = get(url)
    decoded = resp.json()

    if resp.status_code != 200:
        raise Exception(f"Server gave non-200 code {resp.status_code} with message " + decoded["message"])

    return decoded


def get_plugin_updates(pid: str, channel: str) -> dict:
    url = f"https://plugins.jetbrains.com/api/plugins/{pid}/updates?channel={channel}"
    resp = get(url)
    decoded = resp.json()

    if resp.status_code != 200:
        print(f"Server gave non-200 code {resp.status_code} with message " + decoded["message"])
        exit(1)

    return decoded


def serialize_to_file(data, filename):
    with open(filename, 'w') as file:
        file.write(json.dumps(data, indent=2))
        file.write("\n")


def deserialize_from_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json5.load(file)
    return None
