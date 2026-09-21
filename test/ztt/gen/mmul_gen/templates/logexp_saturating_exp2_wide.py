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

DOC_ZH = """\
128 位描述符的饱和用例。

主体与窄用例相同；只有 datatype 域和组内用例编号不同，因此这是域特化而不是第二份实现。
"""

from mmul_gen.machine import SATURATING_INTEGER128
from mmul_gen.templates.logexp_saturating_exp2 import Exp2SaturatingBoundary


class Exp2Saturating128(Exp2SaturatingBoundary):
    """Raise two to a power a 128-bit descriptor cannot hold."""

    summary_zh = "对 128 位描述符无法容纳的指数求 2 的幂。"
    name = "exp2_saturating_128"
    dtypes = SATURATING_INTEGER128


__all__ = ["Exp2Saturating128"]
