#!/bin/sh

set -e

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "${repo_root}"

: "${DOWNLOAD_GMP:=TRUE}"
: "${ENABLE_RISCV_TESTS:=FALSE}"
: "${FIRST_PARTY_TESTS:=FALSE}"
: "${ENABLE_RISCV_ZTT_TESTS:=TRUE}"
: "${GENERATE_RISCV_ZTT_TESTS:=TRUE}"
: "${ZTT_INSTRUCTION_DATA:=}"
: "${ZTT_EXPECTED_MACROS:=}"

set --
set -- "$@" "-DCMAKE_BUILD_TYPE=RelWithDebInfo"
set -- "$@" "-DDOWNLOAD_GMP=${DOWNLOAD_GMP}"
set -- "$@" "-DENABLE_RISCV_TESTS=${ENABLE_RISCV_TESTS}"
set -- "$@" "-DENABLE_RISCV_ZTT_TESTS=${ENABLE_RISCV_ZTT_TESTS}"
set -- "$@" "-DGENERATE_RISCV_ZTT_TESTS=${GENERATE_RISCV_ZTT_TESTS}"
set -- "$@" "-DFIRST_PARTY_TESTS=${FIRST_PARTY_TESTS}"

if [ -n "${ZTT_INSTRUCTION_DATA}" ]; then
  set -- "$@" "-DZTT_INSTRUCTION_DATA=${ZTT_INSTRUCTION_DATA}"
fi
if [ -n "${ZTT_EXPECTED_MACROS}" ]; then
  set -- "$@" "-DZTT_EXPECTED_MACROS=${ZTT_EXPECTED_MACROS}"
fi

cmake -S "${repo_root}" -B "${repo_root}/build" \
  "$@"
jobs=$( (nproc || sysctl -n hw.ncpu || echo 2) 2>/dev/null)
cmake --build "${repo_root}/build" -j${jobs}
ctest --test-dir "${repo_root}/build" -R '^ztt_' --output-on-failure
