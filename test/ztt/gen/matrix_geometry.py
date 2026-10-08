#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""Legal AME configuration values, and the default test-matrix sweep.

``riscv-attached-matrix-extension/src/parameters.adoc`` is the authority for
what an implementation may report, and every Ztt command-line front end
validates against exactly these rules:

* ``AME_NELEM`` is a power of four, so ``N = sqrt(AME_NELEM)`` -- the value
  ``amenlen`` reports -- is a power of two.  The manual sets no upper bound, so
  neither does this module: N = 128 (``AME_NELEM = 16384``) is a legal
  configuration, as ``test/ztt/cfg/rv64-ztt-16k-8.yaml`` shows.
* ``AME_UNIT_DATATYPE_SIZE`` is a positive power of two.  The generators emit
  data tables for the datatypes in ``ame_macros.inc`` and are exercised from 8
  bits up, so 8 is the supported floor.
* ``AME_NUM_M_REGS`` is 16 or 32.
* ``AME_NUM_ACC_REGS`` is 1, 2, 4, 8 or 16.

This module owns the legal values only.  Which of them a sweep actually walks
is the driver's choice, so it lives in ``test/ztt/run_ztt_tests.py``.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

M_REG_VALUES = (16, 32)
ACC_REG_VALUES = (1, 2, 4, 8, 16)
UDS_FLOOR = 8


def _integer(text: str, *, what: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{what} must be an integer, got {text!r}") from None


def _power_of_two(text: str, *, what: str, floor: int) -> int:
    value = _integer(text, what=what)
    if value < floor or value & (value - 1):
        raise argparse.ArgumentTypeError(f"{what} must be a power of two >= {floor}, got {value}")
    return value


def _one_of(text: str, *, what: str, allowed: tuple[int, ...]) -> int:
    value = _integer(text, what=what)
    if value not in allowed:
        choices = ", ".join(str(choice) for choice in allowed)
        raise argparse.ArgumentTypeError(f"{what} must be one of {choices}, got {value}")
    return value


def matrix_n(text: str) -> int:
    """``amenlen``: a power of two, because ``AME_NELEM`` is a power of four."""
    return _power_of_two(text, what="N (amenlen)", floor=2)


def unit_dtype_size(text: str) -> int:
    """``AME_UNIT_DATATYPE_SIZE``: a power of two at or above the supported floor."""
    return _power_of_two(text, what="UDS (AME_UNIT_DATATYPE_SIZE)", floor=UDS_FLOOR)


def num_m_regs(text: str) -> int:
    """``AME_NUM_M_REGS``: 16 or 32."""
    return _one_of(text, what="M/Md register count", allowed=M_REG_VALUES)


def num_acc_regs(text: str) -> int:
    """``AME_NUM_ACC_REGS``: 1, 2, 4, 8 or 16."""
    return _one_of(text, what="Acc/Ad register count", allowed=ACC_REG_VALUES)


def comma_separated(parse: Callable[[str], int]) -> Callable[[str], list[int]]:
    """Adapt a single-value parser to a comma-separated list (``--n 4,8``).

    Repeats are dropped and the written order is kept.
    """

    def parse_list(text: str) -> list[int]:
        parts = [part.strip() for part in text.split(",") if part.strip()]
        if not parts:
            raise argparse.ArgumentTypeError(f"expected at least one value, got {text!r}")
        return list(dict.fromkeys(parse(part) for part in parts))

    return parse_list
