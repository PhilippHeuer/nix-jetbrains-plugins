#!/usr/bin/env bash

docker run --rm -v $(pwd):$(pwd) -w $(pwd) docker.io/nixos/nix:2.33.0 $@
