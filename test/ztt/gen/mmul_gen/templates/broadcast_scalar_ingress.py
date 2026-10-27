#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Whole-register integer descriptors broadcast through the scalar ingress.

Spec:    instructions.adoc:1363-1365 (§6.29)
Quote:   Interprets the low 32 bits of X[rs2] as an AME datatype encoding and the
         X-register bit pattern as one scalar of that datatype, where
         src_dtype = X[rs2][31:0].
Checks:  Broadcasts 42 into every element of each plain whole-register integer
         descriptor and compares the first and last stored element of the
         destination square.

The body is inherited from the shared scalar-ingress template; only the
datatype domain and the case numbering restart per group.
"""

from __future__ import annotations

from mmul_gen.machine import INTEGER
from mmul_gen.templates.broadcast_common import ScalarIngressTemplate


class ScalarIngressBroadcast(ScalarIngressTemplate):
    """Whole-register integer descriptors broadcast through the scalar ingress."""

    name = "scalar_ingress"
    dtypes = INTEGER


__all__ = ["ScalarIngressBroadcast"]


SCALAR_INGRESS = ScalarIngressBroadcast()
