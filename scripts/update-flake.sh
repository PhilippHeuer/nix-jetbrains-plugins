#!/usr/bin/env bash

# update flake.lock
nix flake update --accept-flake-config

# print metadata
nix flake metadata --accept-flake-config
