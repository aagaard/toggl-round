#!/bin/bash

# Run poetry from the project root directory
pushd $(dirname $0)/
poetry run python time_entry_rounding.py
popd
