#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Command-line entry point: ``python3 -m mmul_gen``."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

# Support both ``python3 -m mmul_gen`` (package root already on sys.path) and
# ``python3 mmul_gen/__main__.py`` (only this directory is on sys.path).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matrix_geometry  # noqa: E402
from mmul_gen.asm import GENERATOR_MARKER  # noqa: E402
from mmul_gen.catalog import (  # noqa: E402
    ALL_INSTRUCTIONS,
    INSTRUCTION_FAMILIES,
    describe_instructions,
    select_instructions,
)
from mmul_gen.instruction import GeneratedSource  # noqa: E402
from mmul_gen.macros import parse_dtypes  # noqa: E402
from mmul_gen.machine import MachineConfig  # noqa: E402


DEFAULT_MACRO_FILE = Path(__file__).resolve().parents[2] / "src" / "ame_macros.inc"
DEFAULT_N = 8


def write_source(out_dir: Path, source: GeneratedSource) -> None:
    """Write one source atomically so an interrupted run leaves no partial file."""

    text = source.text if source.text.endswith("\n") else source.text + "\n"
    destination = out_dir / source.name
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=out_dir,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = temporary.name
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            Path(temporary_path).unlink(missing_ok=True)


def remove_stale_sources(out_dir: Path, sources: list[GeneratedSource]) -> None:
    """Delete this generator's own sources that no pass would produce.

    A file is stale only when it belongs to no instruction in the inventory --
    one whose instruction was renamed or removed.  A family this pass did not
    select is kept, because ``--family`` makes the run partial and another
    family's output is not stale.  Only files carrying
    :data:`~mmul_gen.asm.GENERATOR_MARKER` are candidates at all, so pointing
    ``--out-dir`` at a directory shared with another generator never deletes
    that generator's output.
    """

    producible = {source.name for source in sources}
    producible.update(instruction.file_name for instruction in ALL_INSTRUCTIONS)
    duplicates = sorted(
        name
        for name, count in Counter(source.name for source in sources).items()
        if count > 1
    )
    if duplicates:
        raise ValueError(f"duplicate generated test file name(s): {', '.join(duplicates)}")
    for path in out_dir.glob("*.S"):
        if path.name not in producible and _is_our_output(path):
            path.unlink()


def _is_our_output(path: Path) -> bool:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return GENERATOR_MARKER in handle.read(1024)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Ztt tests")
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="output directory for generated test sources",
    )
    parser.add_argument(
        "--macro-file",
        type=Path,
        default=DEFAULT_MACRO_FILE,
        help=f"GAS macro include used to derive the datatypes (default: {DEFAULT_MACRO_FILE})",
    )
    parser.add_argument(
        "--n",
        type=matrix_geometry.matrix_n,
        default=DEFAULT_N,
        help="matrix dimension N (amenlen) for this generation pass",
    )
    parser.add_argument(
        "--uds",
        type=matrix_geometry.unit_dtype_size,
        default=8,
        help="unit datatype size in bits for this generation pass",
    )
    parser.add_argument(
        "--m",
        type=matrix_geometry.num_m_regs,
        default=32,
        help="number of architectural M/Md registers",
    )
    parser.add_argument(
        "--acc",
        type=matrix_geometry.num_acc_regs,
        default=4,
        help="number of architectural Acc/Ad registers",
    )
    parser.add_argument(
        "--family",
        action="append",
        choices=[family.name for family in INSTRUCTION_FAMILIES],
        help=(
            "generate only this instruction family; repeatable, and omitting it "
            "generates every family (default: every family)"
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the instruction inventory for this configuration and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    machine = MachineConfig(
        dtypes=parse_dtypes(args.macro_file),
        n=args.n,
        uds=args.uds,
        num_m_regs=args.m,
        num_acc_regs=args.acc,
    )

    instructions = select_instructions(args.family or ())

    if args.list:
        print(json.dumps(describe_instructions(machine, instructions), indent=2))
        return 0

    if args.out_dir is None:
        raise SystemExit("--out-dir is required unless --list is given")

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = [
        source
        for instruction in instructions
        if (source := instruction.gen(machine)) is not None
    ]
    remove_stale_sources(out_dir, sources)
    for source in sources:
        write_source(out_dir, source)
    print(f"Generated {len(sources)} test files in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
