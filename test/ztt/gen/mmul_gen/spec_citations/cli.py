#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The command line: same options, same exit codes as the documented tool.

``python3 -B -m mmul_gen.tests.test_spec_citations ...`` and
``python3 -B -m mmul_gen.spec_citations ...`` both land in :func:`main`, so the
gate keeps one entry point and one set of options while the unittest module stays
the place discovery collects from.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from mmul_gen.spec_citations.constants import (
    DEFAULT_MANIFEST,
    DEFAULT_SPEC_ROOT,
    DEFAULT_TEMPLATES,
    MANIFEST_NAME,
    SPEC_ROOT_ENV_VAR,
)
from mmul_gen.spec_citations.environment import (
    resolve_spec_root,
    resolve_spec_root_optional,
    resolve_templates,
)
from mmul_gen.spec_citations.manifest import emit_manifest
from mmul_gen.spec_citations.model import SpecEnvironmentError
from mmul_gen.spec_citations.rules import format_report, run_validation


def build_parser() -> argparse.ArgumentParser:
    """CLI definition (kept separate so tests can call the entry point)."""
    parser = argparse.ArgumentParser(description="Check that every Ztt template quotes the AME specification verbatim.")
    parser.add_argument(
        "--templates",
        type=Path,
        default=DEFAULT_TEMPLATES,
        metavar="DIR",
        help=f"template directory (default: {DEFAULT_TEMPLATES})",
    )
    parser.add_argument(
        "--spec-root",
        type=Path,
        default=None,
        metavar="DIR",
        help=(f"specification checkout; default: ${SPEC_ROOT_ENV_VAR} if set, otherwise {DEFAULT_SPEC_ROOT}"),
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        metavar="GLOB",
        help="only validate template file names matching GLOB, repeatable",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        metavar="FILE",
        help=f"frozen excerpt set used when no specification checkout is present (default: {MANIFEST_NAME})",
    )
    parser.add_argument(
        "--emit-manifest",
        type=Path,
        default=None,
        metavar="FILE",
        help="freeze every template quote with its source position into FILE, then exit",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="also print each compliant quote")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: 0 compliant, 1 violations, 2 environment error."""
    args = build_parser().parse_args(argv)
    try:
        templates = resolve_templates(args.templates)
        if args.emit_manifest is not None:
            return emit_manifest(templates, resolve_spec_root(args.spec_root), args.emit_manifest)
        spec_root = resolve_spec_root_optional(args.spec_root)
        if spec_root is None:
            print(
                f"NOTE: no specification checkout (${SPEC_ROOT_ENV_VAR} unset, {DEFAULT_SPEC_ROOT} absent); "
                f"validating against the frozen manifest {args.manifest or DEFAULT_MANIFEST}",
                file=sys.stderr,
            )
        report = run_validation(templates, spec_root, args.only or (), args.manifest)
    except SpecEnvironmentError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(format_report(report, verbose=args.verbose))
    return 1 if report.violations else 0
