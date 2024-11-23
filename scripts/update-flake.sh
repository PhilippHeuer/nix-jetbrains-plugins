#!/usr/bin/env bash

# update flake.lock
nix flake update --accept-flake-config --experimental-features 'nix-command flakes'

# print metadata
nix flake metadata --accept-flake-config --experimental-features 'nix-command flakes'
