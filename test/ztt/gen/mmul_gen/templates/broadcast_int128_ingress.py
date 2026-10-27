#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""128-bit integers broadcast through the scalar ingress.

Spec:    instructions.adoc:1365-1367 (§6.29)
Quote:   If sizeof(src_dtype) is less than XLEN, only the low sizeof(src_dtype)
         bits are used and higher X-register bits are ignored; if it is greater
         than XLEN, X[rs1] is zero-extended to that width.
Checks:  Broadcasts 42 into every element of each 128-bit integer descriptor and
         compares the first and last stored element of the destination square.

The body is inherited from the shared scalar-ingress template; only the
datatype domain and the case numbering restart per group.
"""

from __future__ import annotations

from mmul_gen.machine import INTEGER128
from mmul_gen.templates.broadcast_common import ScalarIngressTemplate


class Integer128IngressBroadcast(ScalarIngressTemplate):
    """128-bit integers broadcast through the scalar ingress."""

    name = "integer128_ingress"
    dtypes = INTEGER128


__all__ = ["Integer128IngressBroadcast"]


INTEGER128_INGRESS = Integer128IngressBroadcast()
