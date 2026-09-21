#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""Small named value types shared by the Ztt generator modules."""

from __future__ import annotations

from typing import NamedTuple, NewType


class DType(NamedTuple):
    """AME datatype descriptor name and its element width in bits."""

    name: str
    bits: int


MRegister = NewType("MRegister", int)


__all__ = ["DType", "MRegister"]
