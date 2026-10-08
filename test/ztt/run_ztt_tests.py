#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Standalone Ztt test driver: generate, compile, and run the full
# N/UDS/M/ACC configuration matrix without CMake.
#
# The matrix is the product of:
#   N   in 4, 8, 16, 32        (matrix square dimension, amenlen)
#   UDS in 8, 16, 32           (unit datatype size in bits)
#   M   in 16, 32              (architectural M/Md registers)
#   ACC in 1, 2, 4, 8, 16      (architectural Acc/Ad registers)
#
# Those four axes are the default sweep; each one can be narrowed with a
# comma-separated list, and legal values are validated against the manual:
#   python3 test/ztt/run_ztt_tests.py --n 16,32 --uds 16 --acc 1
#
# Usage:
#   python3 test/ztt/run_ztt_tests.py --sim ../../build/c_emulator/sail_riscv_sim
#   python3 test/ztt/run_ztt_tests.py --list
#   python3 test/ztt/run_ztt_tests.py --combo n8_u8_m32_a4
#   python3 test/ztt/run_ztt_tests.py --jobs 16

from __future__ import annotations

import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SAIL_AME_ROOT = SCRIPT_DIR.parents[1]

# The legal configuration values live with the generators; the driver sweeps exactly
# what their command lines accept.
GEN_DIR = SCRIPT_DIR / "gen"
if str(GEN_DIR) not in sys.path:
    sys.path.insert(0, str(GEN_DIR))

import matrix_geometry  # noqa: E402

# The sweep: which legal values a run walks when the user does not narrow it.
# M and ACC sweep every value the manual allows; N and UDS sweep the sizes the
# generated suites are exercised at.
N_VALUES = (4, 8, 16, 32)
UDS_VALUES = (8, 16, 32)
MREG_VALUES = matrix_geometry.M_REG_VALUES
ACC_VALUES = matrix_geometry.ACC_REG_VALUES

# Runtime JSON template: a fully rendered Ztt configuration whose Ztt block
# gets rewritten per configuration.  Any rendered matrix JSON works; the
# committed default keeps the script self-contained.
DEFAULT_CONFIG_TEMPLATE = SCRIPT_DIR / "cfg" / "rv64d_v256_e64_ztt.json.in"

GCC = os.environ.get("ZTT_RISCV_GCC", "riscv64-unknown-elf-gcc")
GCC_FLAGS = [
    "-nostdlib",
    "-nostartfiles",
    "-static",
    "-mno-relax",
    "-mcmodel=medany",
]


def default_jobs() -> int:
    """Return the number of CPUs available to this process, like nproc."""

    try:
        return max(1, len(os.sched_getaffinity(0)))
    except AttributeError:
        # sched_getaffinity is not available on every supported platform.
        return os.cpu_count() or 1


def all_combos(
    n_values: Sequence[int] = N_VALUES,
    uds_values: Sequence[int] = UDS_VALUES,
    m_values: Sequence[int] = MREG_VALUES,
    acc_values: Sequence[int] = ACC_VALUES,
) -> list[tuple[int, int, int, int]]:
    return [
        (n, uds, m, acc)
        for n in n_values
        for uds in uds_values
        for m in m_values
        for acc in acc_values
    ]


def combo_name(combo: tuple[int, int, int, int]) -> str:
    n, uds, m, acc = combo
    return f"n{n}_u{uds}_m{m}_a{acc}"


def render_config(template: Path, out_path: Path, combo: tuple[int, int, int, int]) -> None:
    n, uds, m, acc = combo
    text = template.read_text()
    replacements = {
        r'"ame_nlen_pow"\s*:\s*[0-9]+': f'"ame_nlen_pow": {n.bit_length() - 1}',
        r'"ame_unit_dtype_size_pow"\s*:\s*[0-9]+': f'"ame_unit_dtype_size_pow": {uds.bit_length() - 1}',
        r'"ame_num_m_regs"\s*:\s*[0-9]+': f'"ame_num_m_regs": {m}',
        r'"ame_num_acc_regs"\s*:\s*[0-9]+': f'"ame_num_acc_regs": {acc}',
    }
    for pattern, value in replacements.items():
        text, count = re.subn(pattern, value, text)
        if count != 1:
            raise RuntimeError(
                f"config template {template}: expected exactly one {pattern}, found {count}"
            )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)


def generate_one(
    combo: tuple[int, int, int, int],
    out_root: Path,
    macro_file: Path,
) -> Path:
    n, uds, m, acc = combo
    out_dir = out_root / combo_name(combo)
    if not out_dir.is_dir() or not any(out_dir.glob("*.S")):
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "gen" / "mmul_gen" / "__main__.py"),
            "--n",
            str(n),
            "--uds",
            str(uds),
            "--m",
            str(m),
            "--acc",
            str(acc),
            "--macro-file",
            str(macro_file),
            "--out-dir",
            str(out_dir),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    return out_dir


def compile_one(source: Path, elf: Path) -> None:
    elf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        GCC,
        *GCC_FLAGS,
        "-T",
        str(SCRIPT_DIR / "src" / "link.ld"),
        "-I",
        str(SCRIPT_DIR / "src"),
        "-o",
        str(elf),
        str(source),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def run_one(
    sim: str,
    config: Path,
    elf: Path,
    timeout: int,
) -> tuple[bool, str]:
    cmd = [
        sim,
        "--config",
        str(config),
        "--enable-experimental-extensions",
        str(elf),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()
        return False, tail[-1] if tail else f"exit {proc.returncode}"
    return True, ""


class MatrixRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.combos = self._select_combos(args)
        self.work_root = Path(args.work_dir).resolve()
        self.generated_root = self.work_root / "generated"
        self.config_root = self.work_root / "config"
        self.build_root = self.work_root / "build"
        self.sim = args.sim
        self.jobs = args.jobs
        self.timeout = args.timeout
        self.macro_file = Path(
            args.macro_file or SCRIPT_DIR / "src" / "ame_macros.inc"
        ).resolve()
        self.template = Path(args.config_template).resolve()

    def _select_combos(self, args: argparse.Namespace) -> list[tuple[int, int, int, int]]:
        combos = all_combos(
            args.n or N_VALUES,
            args.uds or UDS_VALUES,
            args.m or MREG_VALUES,
            args.acc or ACC_VALUES,
        )
        if args.list:
            for combo in combos:
                print(combo_name(combo))
            sys.exit(0)
        if args.combo:
            wanted = set(args.combo)
            selected = [c for c in combos if combo_name(c) in wanted]
            missing = wanted - {combo_name(c) for c in selected}
            if missing:
                unknown = sorted(missing - {combo_name(c) for c in all_combos()})
                if unknown:
                    sys.exit(f"unknown combos: {', '.join(unknown)}")
                sys.exit(
                    "combos outside the selected axes: " + ", ".join(sorted(missing))
                )
            return selected
        return combos

    def _phase(self, label: str, work, items, keep_going: bool) -> list:
        results: list = []
        failures: list[str] = []
        start = time.time()
        total = len(items)
        done = 0
        last_report = 0.0
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.jobs) as pool:
            futures = {pool.submit(work, item): item for item in items}
            for future in concurrent.futures.as_completed(futures):
                item = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    failures.append(f"{item}: {exc}")
                    if not keep_going:
                        raise SystemExit(f"{label} failed: {exc}")
                done += 1
                now = time.time()
                if now - last_report >= 2.0 or done == total:
                    rate = done / max(0.001, now - start)
                    eta = (total - done) / rate if rate > 0 else 0
                    print(
                        f"\r[{label}] {done}/{total} ({100 * done / total:.0f}%) "
                        f"{rate:.1f}/s eta {eta / 60:.0f}m",
                        end="",
                        flush=True,
                    )
                    last_report = now
        elapsed = time.time() - start
        print(
            f"\r[{label}] {total - len(failures)}/{total} ok in {elapsed / 60:.1f}m    ",
            flush=True,
        )
        for failure in failures:
            print(f"  {label} FAIL: {failure}", flush=True)
        return results

    def run(self) -> int:
        print(
            f"{len(self.combos)} combos, sim={self.sim or 'UNSET'}, jobs={self.jobs}, "
            f"work={self.work_root}",
            flush=True,
        )

        # Phase 0: the macro include is a generated artifact; refresh it when
        # its source snapshot is newer.  Everything else reads it read-only.
        self._refresh_macros()

        # Phase 1: generate per-combo runtime configs.
        def config_job(combo):
            path = self.config_root / f"{combo_name(combo)}.json"
            render_config(self.template, path, combo)
            return combo, path

        configs = dict(self._phase("config", config_job, self.combos, False))

        # Phase 2: generate test sources (skips up-to-date directories).
        def generate_job(combo):
            out_dir = generate_one(combo, self.generated_root, self.macro_file)
            return combo, out_dir

        generated = dict(self._phase("generate", generate_job, self.combos, False))

        # Phase 3: compile.
        sources = sorted(
            (combo, path)
            for combo, out_dir in generated.items()
            for path in out_dir.glob("*.S")
        )

        def compile_job(entry):
            combo, source = entry
            name = source.stem
            elf = self.build_root / combo_name(combo) / f"{name}.elf"
            if not elf.exists() or elf.stat().st_mtime < source.stat().st_mtime:
                compile_one(source, elf)
            return combo, elf

        elfs = self._phase("compile", compile_job, sources, not self.stop_fast)
        compile_failed = len(sources) - len(elfs)

        # Phase 4: run.  Results append to results.tsv so an interrupted run
        # resumes where it left off instead of repeating the whole matrix.
        if not self.sim:
            print("no --sim given; stopping after compile (sources + ELFs are ready)", flush=True)
            return 1 if compile_failed else 0

        results_path = self.work_root / "results.tsv"
        done: set[Path] = set()
        if results_path.exists():
            for line in results_path.read_text().splitlines():
                parts = line.split("\t")
                if len(parts) >= 2 and parts[0] == "pass":
                    done.add(Path(parts[1]))
        pending = [entry for entry in elfs if entry[1] not in done]
        if done:
            print(f"[run] resuming: {len(done)} already recorded, {len(pending)} pending", flush=True)

        def run_job(entry):
            combo, elf = entry
            # Record the start before launching so an externally killed run
            # leaves the in-flight test identifiable as the last start line.
            with open(results_path, "a") as results:
                results.write(f"start\t{elf}\n")
            ok, message = run_one(self.sim, configs[combo], elf, self.timeout)
            with open(results_path, "a") as results:
                results.write(f"{'pass' if ok else 'fail'}\t{elf}\t{message}\n")
            if not ok:
                raise RuntimeError(f"{elf.stem}: {message}")
            return elf

        ran = self._phase("run", run_job, pending, not self.stop_fast)
        failed = len(pending) - len(ran)
        total = len(elfs) + compile_failed
        passed = len(elfs) - failed
        print(
            f"RESULT: {passed}/{total} tests passed"
            + (f", {failed} FAILED" if failed else "")
            + (f", {compile_failed} COMPILE FAILED" if compile_failed else ""),
            flush=True,
        )
        return 1 if failed or compile_failed else 0

    def _refresh_macros(self) -> None:
        snapshot = SCRIPT_DIR / "manual-main" / "instructions.json"
        if not self.macro_file.exists() or self.macro_file.stat().st_mtime < snapshot.stat().st_mtime:
            print("[macros] refreshing ame_macros.inc from manual snapshot", flush=True)
            proc = subprocess.run(
                ["ruby", str(SCRIPT_DIR / "generators" / "gen_ztt_macros.rb")],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise SystemExit(f"macro generation failed: {proc.stderr}")
            self.macro_file.write_text(proc.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate, compile, and run the Ztt N/UDS/M/ACC matrix"
    )
    parser.add_argument(
        "--sim",
        help="simulator executable (e.g. build/c_emulator/sail_riscv_sim); "
        "omit to stop after compiling",
    )
    parser.add_argument(
        "--config-template",
        type=Path,
        default=DEFAULT_CONFIG_TEMPLATE,
        help="rendered Ztt runtime JSON used as the per-combo template",
    )
    parser.add_argument(
        "--macro-file",
        type=Path,
        help="GAS macro include (default: test/ztt/src/ame_macros.inc)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=SAIL_AME_ROOT / "build" / "ztt-matrix",
        help="root for generated/config/build outputs",
    )
    parser.add_argument(
        "--combo",
        action="append",
        help="run one configuration (e.g. n8_u8_m32_a4); repeatable",
    )
    parser.add_argument(
        "--n",
        type=matrix_geometry.comma_separated(matrix_geometry.matrix_n),
        metavar="N[,N...]",
        help="matrix dimension N (amenlen) to sweep, comma separated "
        f"(default: {' '.join(str(v) for v in N_VALUES)})",
    )
    parser.add_argument(
        "--uds",
        type=matrix_geometry.comma_separated(matrix_geometry.unit_dtype_size),
        metavar="BITS[,BITS...]",
        help="unit datatype size in bits to sweep, comma separated "
        f"(default: {' '.join(str(v) for v in UDS_VALUES)})",
    )
    parser.add_argument(
        "--m",
        type=matrix_geometry.comma_separated(matrix_geometry.num_m_regs),
        metavar="COUNT[,COUNT...]",
        help="architectural M/Md register count to sweep, comma separated "
        f"(default: {' '.join(str(v) for v in MREG_VALUES)})",
    )
    parser.add_argument(
        "--acc",
        type=matrix_geometry.comma_separated(matrix_geometry.num_acc_regs),
        metavar="COUNT[,COUNT...]",
        help="architectural Acc/Ad register count to sweep, comma separated "
        f"(default: {' '.join(str(v) for v in ACC_VALUES)})",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=default_jobs(),
        metavar="N",
        help="parallel worker count (default: CPUs available to this process, like nproc)",
    )
    parser.add_argument("--timeout", type=int, default=300, help="per-test simulator timeout")
    parser.add_argument("--list", action="store_true", help="list all configurations and exit")
    parser.add_argument("--stop-fast", action="store_true", help="abort on first failure")
    args = parser.parse_args()

    if args.sim:
        args.sim = shutil.which(args.sim) or str(Path(args.sim).resolve())
    runner = MatrixRunner(args)
    runner.stop_fast = args.stop_fast
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
