#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The fault-atomicity recipe's configuration and its registration on every transfer.

The generated sources are frozen by the golden test; these are the properties a
reader of the recipe should be able to check without hashing assembly: every
load and every store instruction runs it, at UDS 8 its whole-square length is
the same for the raw, row/column-major, and strided forms, only a form whose
transfer extent actually reaches the trigger gets the fault case, and each
direction expects its own mcause.
"""

from __future__ import annotations

import unittest

from mmul_gen.catalog import ALL_INSTRUCTIONS
from mmul_gen.machine import MachineConfig
from mmul_gen.templates.memory_fault_atomicity import (
    DENIED_REGION_OFFSET,
    ELEMENT_DTYPE,
    LOAD_ACCESS_FAULT_CAUSE,
    NON_RAM_HOLE,
    STORE_ACCESS_FAULT_CAUSE,
    MemoryCase,
    MemoryFaultAtomicity,
    MemoryForm,
    transfer_bytes,
)
from mmul_gen.tests.helpers import dtypes, machine, required_template

#: The transfer form each instruction must bind, keyed by mnemonic.
TRANSFER_FORMS = {
    "mss.1r": MemoryForm("raw", strided=False, is_load=False),
    "mss.cm": MemoryForm("cm", strided=False, is_load=False),
    "mss.rm": MemoryForm("rm", strided=False, is_load=False),
    "mss.st": MemoryForm("st", strided=True, is_load=False),
    "mss.tst": MemoryForm("tst", strided=True, is_load=False),
    "mls.1r": MemoryForm("raw", strided=False, is_load=True),
    "mls.cm": MemoryForm("cm", strided=False, is_load=True),
    "mls.rm": MemoryForm("rm", strided=False, is_load=True),
    "mls.st": MemoryForm("st", strided=True, is_load=True),
    "mls.tst": MemoryForm("tst", strided=True, is_load=True),
}


def instruction(name: str):
    for candidate in ALL_INSTRUCTIONS:
        if candidate.name == name:
            return candidate
    raise AssertionError(f"no instruction named {name}")


def element_dtype(config: MachineConfig):
    return next(dtype for dtype in dtypes() if dtype.name == ELEMENT_DTYPE)


class TransferFormTest(unittest.TestCase):
    def test_every_transfer_instruction_binds_its_own_recipe(self) -> None:
        for name, form in TRANSFER_FORMS.items():
            with self.subTest(mnemonic=name):
                template = required_template(instruction(name), MemoryFaultAtomicity)
                self.assertEqual(template.form, form)

    def test_the_recipe_covers_one_whole_square_at_uds_eight(self) -> None:
        config = machine()
        self.assertEqual(transfer_bytes(config), config.nelem)
        self.assertEqual(transfer_bytes(config), config.square_bytes(8))

    def test_no_other_uds_is_covered(self) -> None:
        for name in ("mss.st", "mls.st"):
            template = required_template(instruction(name), MemoryFaultAtomicity)
            for uds in (16, 32):
                with self.subTest(mnemonic=name, uds=uds):
                    config = machine(uds=uds)
                    self.assertFalse(
                        template.fits(
                            config, instruction(name), element_dtype(config)
                        )
                    )

    def test_only_the_uint8_descriptor_is_covered(self) -> None:
        for name in ("mss.st", "mls.st"):
            template = required_template(instruction(name), MemoryFaultAtomicity)
            config = machine()
            for dtype in dtypes():
                if dtype.name == ELEMENT_DTYPE:
                    continue
                with self.subTest(mnemonic=name, dtype=dtype.name):
                    self.assertFalse(
                        template.fits(config, instruction(name), dtype)
                    )


class TransferCaseTest(unittest.TestCase):
    def cases(self, name: str, config: MachineConfig):
        template = required_template(instruction(name), MemoryFaultAtomicity)
        dtype = element_dtype(config)
        return [case.payload for case in template.build(config, instruction(name), dtype)]

    def test_the_overlap_case_is_built_for_stores_only(self) -> None:
        for name in TRANSFER_FORMS:
            with self.subTest(mnemonic=name):
                cases = self.cases(name, machine())
                first = cases[0]
                self.assertIsInstance(first, MemoryCase)
                if TRANSFER_FORMS[name].is_load:
                    self.assertFalse(first.overlap)
                else:
                    self.assertTrue(first.overlap)

    def test_a_load_instruction_runs_only_the_fault_case(self) -> None:
        for name in ("mls.1r", "mls.cm", "mls.rm", "mls.st", "mls.tst"):
            with self.subTest(mnemonic=name):
                self.assertEqual(len(self.cases(name, machine())), 1)

    def test_a_strided_transfer_always_reaches_the_fault(self) -> None:
        expected = {"mss.st": 2, "mss.tst": 2, "mls.st": 1, "mls.tst": 1}
        for name, count in expected.items():
            with self.subTest(mnemonic=name):
                self.assertEqual(len(self.cases(name, machine())), count)

    def test_a_short_contiguous_transfer_has_no_fault_case(self) -> None:
        # At N=4 a contiguous transfer moves exactly the denied region's own
        # length, so the second window never lies inside the transfer.
        config = machine(n=4, num_m_regs=16, num_acc_regs=1)
        self.assertEqual(transfer_bytes(config), DENIED_REGION_OFFSET)
        for name in ("mss.1r", "mss.cm", "mss.rm"):
            with self.subTest(mnemonic=name):
                self.assertEqual(len(self.cases(name, config)), 1)
        # A load has no overlap body, so without a reachable fault the recipe
        # must decline the instruction instead of emitting an empty case.
        for name in ("mls.1r", "mls.cm", "mls.rm"):
            template = required_template(instruction(name), MemoryFaultAtomicity)
            with self.subTest(mnemonic=name):
                self.assertFalse(
                    template.fits(config, instruction(name), element_dtype(config))
                )

    def test_a_long_contiguous_transfer_reaches_the_fault(self) -> None:
        for name in ("mss.1r", "mss.cm", "mss.rm"):
            with self.subTest(mnemonic=name):
                self.assertEqual(len(self.cases(name, machine())), 2)
        for name in ("mls.1r", "mls.cm", "mls.rm"):
            with self.subTest(mnemonic=name):
                self.assertEqual(len(self.cases(name, machine())), 1)


class TransferEmissionTest(unittest.TestCase):
    def text(self, name: str, config: MachineConfig) -> str:
        return instruction(name).gen(config).text

    def test_a_strided_fault_transfers_into_the_non_ram_hole(self) -> None:
        for name in ("mss.st", "mls.st"):
            with self.subTest(mnemonic=name):
                text = self.text(name, machine())
                self.assertIn(f"li      t2, {NON_RAM_HOLE}", text)
                self.assertIn("sub     t2, t2, t1", text)

    def test_a_contiguous_fault_is_denied_by_a_locked_pmp_entry(self) -> None:
        for name in ("mss.rm", "mls.rm"):
            with self.subTest(mnemonic=name):
                text = self.text(name, machine())
                self.assertIn("csrw    pmpaddr0, t0", text)
                self.assertIn("csrw    pmpcfg0, t0", text)

    def test_each_direction_expects_its_own_cause(self) -> None:
        for name in ("mss.1r", "mss.st"):
            with self.subTest(mnemonic=name):
                self.assertIn(
                    f"EXPECT_TRAP_CAUSE 1, {STORE_ACCESS_FAULT_CAUSE}",
                    self.text(name, machine()),
                )
        for name in ("mls.1r", "mls.st"):
            with self.subTest(mnemonic=name):
                self.assertIn(
                    f"EXPECT_TRAP_CAUSE 1, {LOAD_ACCESS_FAULT_CAUSE}",
                    self.text(name, machine()),
                )

    def test_a_load_fault_checks_its_destination_group(self) -> None:
        text = self.text("mls.1r", machine())
        self.assertIn("a load that faults must leave its destination group alone", text)
        # The group is pre-filled, then copied out after the trap so a partial
        # load shows up as a changed byte.
        self.assertIn("mls.1r   m0, t1", text)
        self.assertIn("mss.1r   m0, t2", text)

    def test_the_fault_case_follows_the_overlap_case(self) -> None:
        for name in ("mss.1r", "mss.cm", "mss.rm", "mss.st", "mss.tst"):
            with self.subTest(mnemonic=name):
                text = self.text(name, machine())
                self.assertLess(
                    text.index("overlapping stores"),
                    text.index("a store that faults"),
                )


if __name__ == "__main__":
    unittest.main()
