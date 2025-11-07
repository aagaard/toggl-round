#!/bin/bash

# Execute the script using uv (PEP 582 style environment management)
# Usage: ./run.sh [arg]

pushd $(dirname "$0")/ >/dev/null || exit 1
uv run python time_entry_rounding.py "$1"
popd >/dev/null || exit 1
