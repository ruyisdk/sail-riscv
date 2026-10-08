#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The store-atomicity recipe's configuration and its registration on every store.

The generated sources are frozen by the golden test; these are the properties a
reader of the recipe should be able to check without hashing assembly: every
store instruction runs it once, at UDS 8 its whole-square length is the same for
the raw, row/column-major, and strided forms, and only a form whose store extent
actually reaches the trigger gets the fault case.
"""

from __future__ import annotations

import unittest

from mmul_gen.catalog import ALL_INSTRUCTIONS
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.store_fault_atomicity import (
    DENIED_REGION_OFFSET,
    ELEMENT_DTYPE,
    NON_RAM_HOLE,
    STORE_ACCESS_FAULT_CAUSE,
    StoreCase,
    StoreFaultAtomicity,
    StoreForm,
    store_bytes,
)
from mmul_gen.tests.helpers import dtypes, machine, required_template

#: The store form each instruction must bind, keyed by mnemonic.
STORE_FORMS = {
    "mss.1r": StoreForm("raw", strided=False),
    "mss.cm": StoreForm("cm", strided=False),
    "mss.rm": StoreForm("rm", strided=False),
    "mss.st": StoreForm("st", strided=True),
    "mss.tst": StoreForm("tst", strided=True),
}


def instruction(name: str):
    for candidate in ALL_INSTRUCTIONS:
        if candidate.name == name:
            return candidate
    raise AssertionError(f"no instruction named {name}")


def element_dtype(config: MachineConfig):
    return next(dtype for dtype in dtypes() if dtype.name == ELEMENT_DTYPE)


class StoreFormTest(unittest.TestCase):
    def test_every_store_instruction_binds_its_own_recipe(self) -> None:
        for name, form in STORE_FORMS.items():
            with self.subTest(mnemonic=name):
                template = required_template(instruction(name), StoreFaultAtomicity)
                self.assertEqual(template.form, form)

    def test_the_recipe_covers_one_whole_square_at_uds_eight(self) -> None:
        config = machine()
        self.assertEqual(store_bytes(config), config.nelem)
        self.assertEqual(store_bytes(config), config.square_bytes(8))

    def test_no_other_uds_is_covered(self) -> None:
        template = required_template(instruction("mss.st"), StoreFaultAtomicity)
        for uds in (16, 32):
            with self.subTest(uds=uds):
                config = machine(uds=uds)
                self.assertFalse(
                    template.fits(config, instruction("mss.st"), element_dtype(config))
                )

    def test_only_the_uint8_descriptor_is_covered(self) -> None:
        template = required_template(instruction("mss.st"), StoreFaultAtomicity)
        config = machine()
        for dtype in dtypes():
            if dtype.name == ELEMENT_DTYPE:
                continue
            with self.subTest(dtype=dtype.name):
                self.assertFalse(template.fits(config, instruction("mss.st"), dtype))


class StoreCaseTest(unittest.TestCase):
    def cases(self, name: str, config: MachineConfig):
        template = required_template(instruction(name), StoreFaultAtomicity)
        dtype = element_dtype(config)
        return [
            case.payload
            for case in template.build(config, instruction(name), dtype)
        ]

    def test_the_overlap_case_is_always_built(self) -> None:
        for name in STORE_FORMS:
            with self.subTest(mnemonic=name):
                first = self.cases(name, machine())[0]
                self.assertIsInstance(first, StoreCase)
                self.assertTrue(first.overlap)

    def test_a_strided_store_always_reaches_the_fault(self) -> None:
        for name in ("mss.st", "mss.tst"):
            with self.subTest(mnemonic=name):
                self.assertEqual(len(self.cases(name, machine())), 2)

    def test_a_short_contiguous_store_has_no_fault_case(self) -> None:
        # At N=4 a contiguous store moves exactly the denied region's own
        # length, so the second window never lies inside the store.
        config = machine(n=4, num_m_regs=16, num_acc_regs=1)
        self.assertEqual(store_bytes(config), DENIED_REGION_OFFSET)
        for name in ("mss.1r", "mss.cm", "mss.rm"):
            with self.subTest(mnemonic=name):
                self.assertEqual(len(self.cases(name, config)), 1)

    def test_a_long_contiguous_store_reaches_the_fault(self) -> None:
        for name in ("mss.1r", "mss.cm", "mss.rm"):
            with self.subTest(mnemonic=name):
                self.assertEqual(len(self.cases(name, machine())), 2)


class StoreEmissionTest(unittest.TestCase):
    def text(self, name: str, config: MachineConfig) -> str:
        return instruction(name).gen(config).text

    def test_a_strided_fault_stores_into_the_non_ram_hole(self) -> None:
        text = self.text("mss.st", machine())
        self.assertIn(f"li      t2, {NON_RAM_HOLE}", text)
        self.assertIn("sub     t2, t2, t1", text)
        self.assertIn(f"EXPECT_TRAP_CAUSE 1, {STORE_ACCESS_FAULT_CAUSE}", text)

    def test_a_contiguous_fault_is_denied_by_a_locked_pmp_entry(self) -> None:
        text = self.text("mss.rm", machine())
        self.assertIn("csrw    pmpaddr0, t0", text)
        self.assertIn("csrw    pmpcfg0, t0", text)
        self.assertIn(f"EXPECT_TRAP_CAUSE 1, {STORE_ACCESS_FAULT_CAUSE}", text)

    def test_the_fault_case_follows_the_overlap_case(self) -> None:
        for name in STORE_FORMS:
            with self.subTest(mnemonic=name):
                text = self.text(name, machine())
                self.assertLess(
                    text.index("overlapping stores"),
                    text.index("a store that faults"),
                )


if __name__ == "__main__":
    unittest.main()
