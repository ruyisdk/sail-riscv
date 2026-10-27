#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Input resolution (R4): which templates, which specification, which corpus.

A run never degrades silently.  If the template directory is absent, or the
specification checkout has no ``src/*.adoc``, or a selection is empty, the caller
gets one :class:`~mmul_gen.spec_citations.model.SpecEnvironmentError` and the
command line exits 2.  Nothing is skipped and no run may report ``0/0``.

:func:`resolve_spec_root_optional` is the one deliberate exception: the *gate*
may run without a specification checkout, and it says so on stderr before using
the frozen manifest instead.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Mapping, Sequence

from mmul_gen.spec_citations.constants import DEFAULT_SPEC_ROOT, SPEC_ROOT_ENV_VAR
from mmul_gen.spec_citations.model import SpecEnvironmentError


def resolve_templates(directory: Path) -> Path:
    """Return the template directory, or raise :class:`SpecEnvironmentError`."""
    resolved = directory.expanduser()
    if not resolved.exists():
        raise SpecEnvironmentError(
            f"template directory does not exist: {resolved}\n"
            f"  pass --templates DIR, or check that the checkout is present"
        )
    if not resolved.is_dir():
        raise SpecEnvironmentError(f"template path is not a directory: {resolved}")
    if not any(resolved.glob("*.py")):
        raise SpecEnvironmentError(f"template directory holds no *.py file: {resolved}")
    return resolved


def resolve_spec_root(directory: Path | None, env: Mapping[str, str] | None = None) -> Path:
    """Return the specification checkout, or raise :class:`SpecEnvironmentError`.

    Order: an explicit ``--spec-root``, then ``$AME_SPEC_ROOT``, then
    :data:`~mmul_gen.spec_citations.constants.DEFAULT_SPEC_ROOT`.
    """
    environ = os.environ if env is None else env
    if directory is not None:
        source = "--spec-root"
        candidate = directory.expanduser()
    elif environ.get(SPEC_ROOT_ENV_VAR):
        source = f"${SPEC_ROOT_ENV_VAR}"
        candidate = Path(environ[SPEC_ROOT_ENV_VAR]).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
    else:
        source = f"default ({DEFAULT_SPEC_ROOT})"
        candidate = DEFAULT_SPEC_ROOT

    if not candidate.exists():
        raise SpecEnvironmentError(
            f"cannot locate the AME specification sources ({source}).\n"
            f"  expected a directory containing src/*.adoc at:\n"
            f"    {candidate}\n"
            f"  fix one of:\n"
            f"    export {SPEC_ROOT_ENV_VAR}=/path/to/riscv-attached-matrix-extension\n"
            f"    git clone <spec-url> riscv-attached-matrix-extension\n"
            f"    git -C riscv-attached-matrix-extension checkout v0.6   # targets v0.6"
        )
    sources = candidate / "src"
    if not sources.is_dir() or not any(sources.glob("*.adoc")):
        raise SpecEnvironmentError(
            f"specification checkout at {candidate} has no src/*.adoc "
            f"(looked in {sources}); this suite targets riscv-attached-matrix-extension v0.6"
        )
    return candidate


def resolve_spec_root_optional(directory: Path | None = None) -> Path | None:
    """Like :func:`resolve_spec_root`, but ``None`` when no checkout is present."""
    try:
        return resolve_spec_root(directory)
    except SpecEnvironmentError:
        return None


def select_templates(directory: Path, patterns: Sequence[str]) -> list[Path]:
    """Return the templates to visit, in file-name order (R7)."""
    paths = sorted(directory.glob("*.py"), key=lambda path: path.name)
    if patterns:
        paths = [path for path in paths if any(fnmatch.fnmatchcase(path.name, pattern) for pattern in patterns)]
        if not paths:
            raise SpecEnvironmentError(f"--only {list(patterns)} matched no template in {directory}")
    return paths
