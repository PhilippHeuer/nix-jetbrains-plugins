"""
These functions are copied from nixpkgs and reused here.

URL: https://github.com/NixOS/nixpkgs/blob/master/pkgs/applications/editors/jetbrains/plugins/update_plugins.py
License: MIT
"""

from json import load
from pathlib import Path
from subprocess import run
from requests import get


NIXPKGS_IDES_FILE = Path(__file__).parent.parent.joinpath("./data/cache/nixpkgs-ides-latest.json").resolve()
NIXOS_IDES_FILE = Path(__file__).parent.parent.joinpath("./data/cache/nixos-ides-latest.json").resolve()
MASTER_IDES_FILE = Path(__file__).parent.parent.joinpath("./data/cache/master-ides-latest.json").resolve()
FLAKE_LOCK_FILE = Path(__file__).parent.parent.joinpath("./flake.lock").resolve()

# Token priorities for version checking
# From https://github.com/JetBrains/intellij-community/blob/94f40c5d77f60af16550f6f78d481aaff8deaca4/platform/util-rt/src/com/intellij/util/text/VersionComparatorUtil.java#L50
TOKENS = {
    "snap": 10, "snapshot": 10,
    "m": 20,
    "eap": 25, "pre": 25, "preview": 25,
    "alpha": 30, "a": 30,
    "beta": 40, "betta": 40, "b": 40,
    "rc": 50,
    "sp": 70,
    "rel": 80, "release": 80, "r": 80, "final": 80
}
SNAPSHOT_VALUE = 99999


def get_hash(url):
    print(f"Downloading {url}")
    args = ["nix-prefetch-url", url, "--print-path"]
    if url.endswith(".zip"):
        args.append("--unpack")
    else:
        args.append("--executable")
    path_process = run(args, capture_output=True, check=True)
    output_lines = path_process.stdout.decode().split("\n")
    if len(output_lines) < 2:
        raise ValueError("Unexpected output format from nix-prefetch-url")
    path = output_lines[1].strip()
    if not path:
        raise ValueError("No path found in the output of nix-prefetch-url")

    hash_process = run(["nix", "--extra-experimental-features", "nix-command", "hash", "path", path], capture_output=True, check=True)
    result_contents = hash_process.stdout.decode()[:-1]
    if not result_contents:
        raise RuntimeError(f"Failed to compute hash: {hash_process.stderr.decode()}")
    return result_contents


def get_nixpkgs_ides_versions():
    rev = load(open(FLAKE_LOCK_FILE))["nodes"]["nixpkgs-unstable"]["locked"]["rev"]
    url = f"https://raw.githubusercontent.com/NixOS/nixpkgs/{rev}/pkgs/applications/editors/jetbrains/bin/versions.json"
    resp = get(url)
    if resp.status_code != 200:
        print(f"Server gave non-200 code {resp.status_code} with message " + resp.text)
        exit(1)
    with open(NIXPKGS_IDES_FILE, "w") as file:
        file.write(resp.text)

    rev = load(open(FLAKE_LOCK_FILE))["nodes"]["nixos-unstable"]["locked"]["rev"]
    url = f"https://raw.githubusercontent.com/NixOS/nixpkgs/{rev}/pkgs/applications/editors/jetbrains/bin/versions.json"
    resp = get(url)
    if resp.status_code != 200:
        print(f"Server gave non-200 code {resp.status_code} with message " + resp.text)
        exit(1)
    with open(NIXOS_IDES_FILE, "w") as file:
        file.write(resp.text)

    rev = load(open(FLAKE_LOCK_FILE))["nodes"]["nixos-master"]["locked"]["rev"]
    url = f"https://raw.githubusercontent.com/NixOS/nixpkgs/{rev}/pkgs/applications/editors/jetbrains/bin/versions.json"
    resp = get(url)
    if resp.status_code != 200:
        print(f"Server gave non-200 code {resp.status_code} with message " + resp.text)
        exit(1)
    with open(MASTER_IDES_FILE, "w") as file:
        file.write(resp.text)


def get_ide_versions() -> dict:
    result = {}

    for file_path in [NIXPKGS_IDES_FILE, NIXOS_IDES_FILE, MASTER_IDES_FILE]:
        ide_data = load(open(file_path))
        for platform in ide_data:
            for product in ide_data[platform]:
                version = ide_data[platform][product]["build_number"]
                if product not in result:
                    result[product] = [version]
                elif version not in result[product]:
                    result[product].append(version)

    # Gateway isn't a normal IDE, so it doesn't use the same plugins system
    del result["gateway"]

    return result


def print_file_diff(old, new):
    added = new.copy()
    removed = old.copy()
    to_delete = []

    for file in added:
        if file in removed:
            to_delete.append(file)

    for file in to_delete:
        added.remove(file)
        removed.remove(file)

    if removed:
        print("\nRemoved:")
        for file in removed:
            print(" - " + file)
        print()

    if added:
        print("\nAdded:")
        for file in added:
            print(" + " + file)
        print()

def tokenize_stream(stream):
    for item in stream:
        if item in TOKENS:
            yield TOKENS[item], 0
        elif item.isalpha():
            for char in item:
                yield 90, ord(char) - 96
        elif item.isdigit():
            yield 100, int(item)


def split(version_string: str):
    prev_type = None
    block = ""
    for char in version_string:

        if char.isdigit():
            cur_type = "number"
        elif char.isalpha():
            cur_type = "letter"
        else:
            cur_type = "other"

        if cur_type != prev_type and block:
            yield block.lower()
            block = ""

        if cur_type in ("letter", "number"):
            block += char

        prev_type = cur_type

    if block:
        yield block


def tokenize_string(version_string: str):
    return list(tokenize_stream(split(version_string)))


def pick_newest(ver1: str, ver2: str) -> str:
    if ver1 is None or ver1 == ver2:
        return ver2

    if ver2 is None:
        return ver1

    presort = [tokenize_string(ver1), tokenize_string(ver2)]
    postsort = sorted(presort)
    if presort == postsort:
        return ver2
    else:
        return ver1


def is_build_older(ver1: str, ver2: str) -> int:
    ver1 = [int(i) for i in ver1.replace("*", str(SNAPSHOT_VALUE)).split(".")]
    ver2 = [int(i) for i in ver2.replace("*", str(SNAPSHOT_VALUE)).split(".")]

    for i in range(min(len(ver1), len(ver2))):
        if ver1[i] == ver2[i] and ver1[i] == SNAPSHOT_VALUE:
            return 0
        if ver1[i] == SNAPSHOT_VALUE:
            return 1
        if ver2[i] == SNAPSHOT_VALUE:
            return -1
        result = ver1[i] - ver2[i]
        if result != 0:
            return result

    return len(ver1) - len(ver2)


def is_compatible(build, since, until) -> bool:
    return (not since or is_build_older(since, build) < 0) and (not until or 0 < is_build_older(until, build))
