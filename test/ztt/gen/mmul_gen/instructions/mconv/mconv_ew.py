#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Generator for ``mconv.ew``: convert elements between storage and compute types."""

from __future__ import annotations

from collections.abc import Sequence

from mmul_gen.instruction import (
    DESTINATION_OPERAND,
    FIRST_SOURCE_OPERAND,
    Instruction,
)
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.mconv_domain_pairs import (
    MCONV_DOMAIN_PAIRS,
)
from mmul_gen.templates.mconv_roundtrip import (
    MCONV_ROUNDTRIP,
)


class MconvEw(Instruction):
    """Elementwise conversion between a packed storage and its compute type."""

    name = "mconv.ew"
    summary = "convert a formed square between its packed storage and compute datatypes"
    subject = "storage/compute dtype conversion test cases."
    operands = (DESTINATION_OPERAND, FIRST_SOURCE_OPERAND)
    templates = (MCONV_ROUNDTRIP, MCONV_DOMAIN_PAIRS)
    # The conversion format always carries its data section, even when the
    # active UDS has no conversion pair to put in it.
    always_emits_data = True

    def banner(self, machine: MachineConfig) -> Sequence[str]:
        # This family's banner carries the storage/compute split, which no other
        # family states, so the instruction declares it rather than a base class.
        return [
            self.title,
            f"UDS={machine.uds}: storage={machine.uds // 2}, compute={machine.uds}",
        ]


__all__ = ["MconvEw"]
