#!/usr/bin/env bash
# Verify a Ztt macro include file against the current prose specification.
set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -ne 1 ]; then
    echo "Usage: $(basename -- "$0") EXPECTED_MACROS_FILE" >&2
    exit 2
fi

expected_file=$1
if [ ! -f "$expected_file" ]; then
    echo "Macro include file does not exist: $expected_file" >&2
    exit 2
fi

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

ruby "${script_dir}/gen_ztt_macros.rb" > "$tmp"

if ! diff -q "$tmp" "$expected_file" > /dev/null 2>&1; then
    echo "$expected_file does not match manual-main/instructions.json."
    echo "Regenerate it with generators/gen_ztt_macros.rb."
    exit 1
fi
