#!/usr/bin/env bash
# Run the checked-in minimal regression tests for AME instruction behaviour.
#
# The script reports PASS/FAIL per test/simulator.
#
# Usage:
#   ./run_repro.sh [path/to/sail_riscv_sim]
#
# Environment:
#   ZTT_RISCV_GCC   cross compiler (default riscv64-unknown-elf-gcc)
#   SPIKE_ZTT       path to spike_ztt_runner.py (the AME-enabled spike binary
#                   must already be wired inside that script)

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
SAIL_SIM="${1:-}"
SPIKE_RUNNER="${SPIKE_ZTT:-}"
GCC="${ZTT_RISCV_GCC:-riscv64-unknown-elf-gcc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

check() { # name, cmd...
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then echo "PASS $name"; else echo "FAIL $name"; fi
}

for t in spike_int128_mhdiff_x_m32; do
    "$GCC" -nostdlib -nostartfiles -static -mno-relax -mcmodel=medany \
        -T "$HERE/../src/link.ld" -I "$HERE/../src" \
        "$HERE/$t.S" -o "$WORK/$t.elf" 2>/dev/null || { echo "BUILD-ERROR $t"; continue; }

    if [ -x "$SAIL_SIM" ]; then
        check "sail/$t (regression guard: must PASS)" \
            "$SAIL_SIM" --config "$HERE/configs/n8_u16_m32.json" \
            --enable-experimental-extensions "$WORK/$t.elf"
    else
        echo "SKIP sail/$t (simulator not found)"
    fi

    if [ -f "$SPIKE_RUNNER" ]; then
        check "spike/$t (regression guard: must PASS)" \
            python3 "$SPIKE_RUNNER" --config "$HERE/configs/n8_u16_m32.json" \
            --enable-experimental-extensions "$WORK/$t.elf"
    else
        echo "SKIP spike/$t (runner not found)"
    fi
done
