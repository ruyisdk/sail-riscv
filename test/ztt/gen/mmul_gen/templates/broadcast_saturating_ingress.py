#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Saturating integer descriptors broadcast through the scalar ingress.

Spec:    instructions.adoc:1373-1375 (§6.29)
Quote:   The source and destination datatype encodings must be supported, and the
         source-to-destination conversion must be supported.
Checks:  Broadcasts 42 into every element of each saturating whole-register
         integer descriptor and compares the first and last stored element of
         the destination square.

The body is inherited from the shared scalar-ingress template; only the
datatype domain and the case numbering restart per group.
"""

from __future__ import annotations

from mmul_gen.machine import SATURATING_INTEGER
from mmul_gen.templates.broadcast_common import ScalarIngressTemplate


class SaturatingIngressBroadcast(ScalarIngressTemplate):
    """Saturating integer descriptors broadcast through the scalar ingress."""

    name = "saturating_ingress"
    dtypes = SATURATING_INTEGER


__all__ = ["SaturatingIngressBroadcast"]


SATURATING_INGRESS = SaturatingIngressBroadcast()
