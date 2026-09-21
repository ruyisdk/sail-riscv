#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Compare Ztt test inputs with an explicit machine-readable manual snapshot.

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SAIL_ZTT_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_MACROS = SAIL_ZTT_ROOT / "test/ztt/src/ame_macros.inc"
MACRO_PATTERN = re.compile(r"^\s*\.macro\s+([A-Za-z0-9._]+)(?:\s|$)", re.MULTILINE)
MACRO_BLOCK_PATTERN = re.compile(
    r"^\s*\.macro\s+(?P<name>[A-Za-z0-9._]+)(?:[^\n]*)\n(?P<body>.*?)^\s*\.endm\s*$",
    re.MULTILINE | re.DOTALL,
)
SAIL_EXECUTE_PATTERN = re.compile(r"^function clause execute (?P<name>AME_[A-Z0-9_]+)\(", re.MULTILINE)
SAIL_FAMILY_CASE_PATTERN = re.compile(
    r"^\s*(?P<name>AME_[A-Z0-9_]+)\s*=>",
)
SAIL_STUB_PATTERN = re.compile(r'Ztt execute (?:stub|implementation missing): (?P<name>[A-Za-z0-9._]+)')


def read_manual_instruction_names(path: Path) -> set[str]:
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read instruction data {path}: {exc}") from exc

    instructions = document.get("instructions") if isinstance(document, dict) else None
    if not isinstance(instructions, list):
        raise ValueError(f"{path}: expected an object containing an instructions array")

    names: set[str] = set()
    for index, instruction in enumerate(instructions):
        name = instruction.get("name") if isinstance(instruction, dict) else None
        if not isinstance(name, str) or not name:
            raise ValueError(f"{path}: instructions[{index}] has no instruction name")
        if name in names:
            raise ValueError(f"{path}: duplicate instruction name: {name}")
        names.add(name)
    return names


def read_macro_instruction_names(path: Path) -> set[str]:
    try:
        names = MACRO_PATTERN.findall(path.read_text())
    except OSError as exc:
        raise ValueError(f"cannot read Ztt macro include {path}: {exc}") from exc

    if not names:
        raise ValueError(f"{path}: no Ztt macro definitions found")
    if len(names) != len(set(names)):
        duplicates = sorted(name for name in set(names) if names.count(name) > 1)
        raise ValueError(f"{path}: duplicate Ztt macro definitions: {', '.join(duplicates)}")
    return set(names)


def read_macro_blocks(path: Path) -> dict[str, str]:
    try:
        blocks = {
            match.group("name"): match.group(0).strip()
            for match in MACRO_BLOCK_PATTERN.finditer(path.read_text())
        }
    except OSError as exc:
        raise ValueError(f"cannot read Ztt macro include {path}: {exc}") from exc

    if not blocks:
        raise ValueError(f"{path}: no Ztt macro definitions found")
    return blocks


def sail_constructor(name: str) -> str:
    constructor = re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_").upper()
    return f"AME_{constructor}"


def read_sail_execute_names(path: Path) -> tuple[set[str], set[str]]:
    try:
        if path.is_dir():
            sail_files = sorted(path.glob("ztt_*.sail"))
            if not sail_files:
                raise ValueError(f"{path}: no Ztt Sail files found")
            text = "\n".join(source.read_text() for source in sail_files)
        else:
            text = path.read_text()
    except OSError as exc:
        raise ValueError(f"cannot read Sail model {path}: {exc}") from exc

    execute_names = set(SAIL_EXECUTE_PATTERN.findall(text))

    # Family implementations contain a single execute clause with an
    # instruction-selector match.  Restrict case discovery to those clause
    # bodies so enums used by semantic helper functions (AME_INT_*,
    # AME_FLOAT_*, ...) are not mistaken for instruction constructors.
    lines = text.splitlines()
    execute_start = re.compile(r"^function clause execute [A-Z0-9_]+\(")
    brace_depth = 0
    in_execute = False
    for line in lines:
        if not in_execute and execute_start.match(line):
            in_execute = True
            brace_depth = 0
        if in_execute:
            brace_depth += line.count("{") - line.count("}")
            case = SAIL_FAMILY_CASE_PATTERN.match(line)
            if case:
                execute_names.add(case.group("name"))
            if brace_depth <= 0:
                in_execute = False
    stubs = {match.group("name") for match in SAIL_STUB_PATTERN.finditer(text)}
    if not execute_names:
        raise ValueError(f"{path}: no Ztt execute clauses found")
    return execute_names, stubs


def macro_files_match(actual_path: Path, expected_path: Path) -> tuple[bool, str, str]:
    try:
        actual = actual_path.read_bytes()
        expected = expected_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot compare Ztt macro includes: {exc}") from exc
    return (
        actual == expected,
        hashlib.sha256(actual).hexdigest(),
        hashlib.sha256(expected).hexdigest(),
    )


def print_names(label: str, names: set[str]) -> None:
    if names:
        print(f"{label} ({len(names)}): {', '.join(sorted(names))}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Ztt generated artifacts with a manual instruction snapshot"
    )
    parser.add_argument("--instruction-data", type=Path, required=True, help="manual-main/instructions.json")
    parser.add_argument(
        "--macros",
        "--macro-file",
        dest="macros",
        type=Path,
        default=DEFAULT_MACROS,
        help="Ztt macro include file",
    )
    parser.add_argument(
        "--expected-macros",
        type=Path,
        help="macro include generated from the same manual snapshot; enables encoding-level validation",
    )
    parser.add_argument(
        "--sail-model",
        type=Path,
        help="current Ztt Sail model; enables execute-clause and stub validation",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail if generated macros or the Sail inventory are stale with respect to the manual",
    )
    parser.add_argument(
        "--check-instructions",
        nargs="+",
        metavar="INSTRUCTION",
        help="limit presence and encoding checks to an explicitly migrated instruction tranche",
    )
    parser.add_argument(
        "--strict-selected",
        action="store_true",
        help="fail when the instruction tranche named by --check-instructions is inconsistent",
    )
    args = parser.parse_args()

    if args.strict_selected and not args.check_instructions:
        parser.error("--strict-selected requires --check-instructions")

    manual = read_manual_instruction_names(args.instruction_data.resolve())
    macro_path = args.macros.resolve()
    macros = read_macro_instruction_names(macro_path)
    sail_execute: set[str] = set()
    sail_stubs: set[str] = set()
    if args.sail_model:
        sail_execute, sail_stubs = read_sail_execute_names(args.sail_model.resolve())

    manual_without_macros = manual - macros
    macros_without_manual = macros - manual
    manual_without_sail = {sail_constructor(name) for name in manual} - sail_execute if args.sail_model else set()
    sail_without_manual = (
        {name for name in sail_execute if name.startswith("AME_")} - {sail_constructor(name) for name in manual}
        if args.sail_model
        else set()
    )
    macros_match_expected = True
    actual_digest = ""
    expected_digest = ""
    if args.expected_macros:
        macros_match_expected, actual_digest, expected_digest = macro_files_match(
            macro_path, args.expected_macros.resolve()
        )

    selected = set(args.check_instructions or [])
    selected_absent_from_manual = selected - manual
    selected_missing_macros = selected - macros
    selected_macro_mismatches: set[str] = set()
    if selected and args.expected_macros:
        actual_blocks = read_macro_blocks(macro_path)
        expected_blocks = read_macro_blocks(args.expected_macros.resolve())
        selected_macro_mismatches = {
            name
            for name in selected & manual & macros
            if actual_blocks.get(name) != expected_blocks.get(name)
        }

    print(f"manual instructions: {len(manual)}")
    print(f"macro instructions: {len(macros)}")
    if args.sail_model:
        print(f"Sail execute clauses: {len(sail_execute)}")
        print_names("manual instructions missing Sail execute clauses", manual_without_sail)
        print_names("Sail execute clauses absent from manual", sail_without_manual)
        print_names("Sail execute stubs", {sail_constructor(name) for name in sail_stubs})
    print_names("manual instructions missing macros", manual_without_macros)
    print_names("macros absent from manual", macros_without_manual)
    if args.expected_macros:
        print(f"macro file matches expected snapshot: {'yes' if macros_match_expected else 'no'}")
        if not macros_match_expected:
            print(f"actual macro SHA-256: {actual_digest}")
            print(f"expected macro SHA-256: {expected_digest}")
    if selected:
        print_names("selected instructions absent from manual", selected_absent_from_manual)
        print_names("selected instructions missing macros", selected_missing_macros)
        if args.expected_macros:
            print_names("selected instruction macros with stale encodings", selected_macro_mismatches)
            print(
                "selected instruction macro blocks match expected snapshots: "
                f"{'yes' if not selected_macro_mismatches else 'no'}"
            )

    inconsistent = (
        manual_without_macros
        or macros_without_manual
        or not macros_match_expected
        or manual_without_sail
        or sail_without_manual
        or sail_stubs
    )
    if args.strict and inconsistent:
        return 1
    selected_inconsistent = (
        selected_absent_from_manual
        or selected_missing_macros
        or selected_macro_mismatches
    )
    if args.strict_selected and selected_inconsistent:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
