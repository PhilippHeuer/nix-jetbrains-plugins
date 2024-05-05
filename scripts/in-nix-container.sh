#!/usr/bin/env bash

docker run --rm -v $(pwd):/mnt -w /mnt docker.io/nixos/nix:2.22.0 $@
