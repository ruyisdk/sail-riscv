#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Saturating case for the 128-bit descriptors.

Same body as the narrow case; only the datatype domain and the group-local case
numbering differ, which is why this is a domain specialisation rather than a
second implementation.
"""

from __future__ import annotations

from mmul_gen.machine import SATURATING_INTEGER128
from mmul_gen.templates.logexp_saturating_exp2 import Exp2SaturatingBoundary


class Exp2Saturating128(Exp2SaturatingBoundary):
    """Raise two to a power a 128-bit descriptor cannot hold."""

    name = "exp2_saturating_128"
    dtypes = SATURATING_INTEGER128


__all__ = ["Exp2Saturating128"]
