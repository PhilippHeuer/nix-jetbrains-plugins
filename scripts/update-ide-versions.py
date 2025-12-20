#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3.pkgs.requests python3.pkgs.json5 nix.out

# This script checks for new ide versions in nixpkgs, and adds them to the ides.json file.

from argparse import ArgumentParser
import logging
from lib.nixpkgslib import fetch_nixpkgs_ide_versions, merge_nixpkgs_ide_versions


FLAKE_INPUTS = [
    "nixpkgs",
    "nixos-unstable",
    "nixos-master"
]


def main():
    parser = ArgumentParser(description="Add missing plugins to ide-version.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info("fetching ide versions from nixpkgs, inputs: %s", FLAKE_INPUTS)
    ide_versions = fetch_nixpkgs_ide_versions(FLAKE_INPUTS)
    merge_nixpkgs_ide_versions("data/ide-version.json", ide_versions)
    logging.info("successfully updated ide versions")


if __name__ == '__main__':
    main()
