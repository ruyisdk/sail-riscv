#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The extra-permute case of a zip or unzip operation.

Same emission as the dual-source case; only the datatype domain and the group of
registers the operation works in differ, which is why this is a domain
specialisation.  It runs the saturating and floating descriptors, so the same
interleaving is checked on descriptors the plain integers cannot reach.
"""

from __future__ import annotations

from mmul_gen.machine import EXTRA_PERMUTE
from mmul_gen.templates.matrix_ops_zip_dual import ZipDualSource


class ZipExtraSource(ZipDualSource):
    """Merge or split two ramps of a full-width non-integer descriptor."""

    name = "zip_extra_dtype_ramp"
    dtypes = EXTRA_PERMUTE
    extra = True


__all__ = ["ZipExtraSource"]
