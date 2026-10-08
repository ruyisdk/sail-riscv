#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Datatype domains and geometry track the N/UDS configuration."""

from __future__ import annotations

import unittest

from mmul_gen.machine import (
    ALL_DOMAINS,
    INTEGER,
    INTEGER128,
    PACKED_INTEGER,
    SATURATING_INTEGER,
    SIGNED_PACKED_SOURCE,
    SOFTFLOAT,
    MachineConfig,
)
from mmul_gen.tests.helpers import dtypes


def names(selection) -> set[str]:
    return {dtype.name for dtype in selection}


class MachineConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dtypes = dtypes()

    def machine(self, uds: int, **kwargs) -> MachineConfig:
        return MachineConfig(dtypes=self.dtypes, uds=uds, **kwargs)

    def test_every_domain_is_named_and_described(self) -> None:
        self.assertEqual(len({domain.name for domain in ALL_DOMAINS}), len(ALL_DOMAINS))
        for domain in ALL_DOMAINS:
            with self.subTest(domain=domain.name):
                self.assertTrue(domain.name)
                self.assertTrue(domain.description)
                self.assertTrue(domain(self.machine(8)))

    def test_semantic_and_formed_domains_track_uds(self) -> None:
        for uds in (8, 16, 32):
            with self.subTest(uds=uds):
                config = self.machine(uds)
                self.assertTrue(
                    all(dtype.bits >= uds and dtype.bits % uds == 0 for dtype in config.semantic_dtypes)
                )
                storage_bits = uds // 2
                packed = names(PACKED_INTEGER(config))
                self.assertIn(f"AME_UINT{storage_bits}_DTYPE", packed)
                self.assertIn(f"AME_INT{storage_bits}_DTYPE", packed)
                self.assertTrue(all(dtype.bits < uds for dtype in PACKED_INTEGER(config)))

    def test_semantic_integer_domains_exclude_float_and_saturating_descriptors(self) -> None:
        config = self.machine(8)
        self.assertEqual(
            names(INTEGER(config)),
            {
                "AME_UINT8_DTYPE",
                "AME_INT8_DTYPE",
                "AME_UINT16_DTYPE",
                "AME_INT16_DTYPE",
                "AME_UINT32_DTYPE",
                "AME_INT32_DTYPE",
                "AME_UINT64_DTYPE",
                "AME_INT64_DTYPE",
            },
        )
        self.assertEqual(
            names(INTEGER128(config)), {"AME_UINT128_DTYPE", "AME_INT128_DTYPE"}
        )
        self.assertTrue(
            all("_SAT_" in dtype.name for dtype in SATURATING_INTEGER(config))
        )
        self.assertEqual(
            names(SOFTFLOAT(config)),
            {
                "AME_OCP_E4M3_DTYPE",
                "AME_OCP_E5M2_DTYPE",
                "AME_FP16_DTYPE",
                "AME_BF16_DTYPE",
                "AME_FP32_DTYPE",
                "AME_FP64_DTYPE",
            },
        )

    def test_formed_domains_narrow_with_uds(self) -> None:
        self.assertEqual(
            names(PACKED_INTEGER(self.machine(16))),
            {
                "AME_UINT4_DTYPE",
                "AME_INT4_DTYPE",
                "AME_UINT8_DTYPE",
                "AME_INT8_DTYPE",
            },
        )
        self.assertEqual(
            names(SIGNED_PACKED_SOURCE(self.machine(32))), {"AME_INT16_DTYPE"}
        )

    def test_geometry_is_element_width_relative_to_uds(self) -> None:
        config = self.machine(16, n=8)
        self.assertEqual(config.nelem, 64)
        self.assertEqual(config.nregs(16), 1)
        self.assertEqual(config.nregs(32), 2)
        self.assertEqual(config.square_bytes(16), 128)
        self.assertEqual(config.square_bytes(4), 128)
        self.assertEqual(config.storage_elements(4), 256)
        self.assertEqual(config.storage_elements(32), 64)

    def test_invalid_configurations_fail_loudly(self) -> None:
        for override in (
            {"n": 0},
            {"uds": 0},
            {"num_m_regs": 0},
            {"num_acc_regs": 0},
        ):
            arguments = {"uds": 8} | override
            with self.subTest(**override), self.assertRaises(ValueError):
                MachineConfig(dtypes=self.dtypes, **arguments)


if __name__ == "__main__":
    unittest.main()
