#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Parse the datatype descriptors out of the generated GAS macro include.

The low byte of every ``AME_*_DTYPE`` descriptor value is its element width in
bits, so the include is the single source of truth for which datatypes a
configuration supports and how wide they are.
"""

from __future__ import annotations

import re
from pathlib import Path

from mmul_gen.machine import DType


_DESCRIPTOR = re.compile(
    r"\.equ\s+(AME_[A-Z0-9_]+_DTYPE)\s*,\s*(0x[0-9a-fA-F]+|[0-9]+)"
)


def parse_dtypes(path: Path) -> tuple[DType, ...]:
    """Datatype descriptors in file order, first definition wins."""

    text = path.read_text()
    dtypes: list[DType] = []
    seen: set[str] = set()
    for name, value_text in _DESCRIPTOR.findall(text):
        if name in seen:
            continue
        dtypes.append(DType(name, int(value_text, 0) & 0xFF))
        seen.add(name)
    if not dtypes:
        raise ValueError(f"no AME datatype constants found in {path}")
    return tuple(dtypes)


__all__ = ["parse_dtypes"]
