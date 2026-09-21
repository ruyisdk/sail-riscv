#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The template inventory: one class per template, reused by every instruction.

The inventory has two tiers.  A template with no per-instruction inputs is one
shared instance in ``ALL_TEMPLATES``; a template that carries its own inputs --
the elementwise templates, the descriptor roundtrips, the integer shifts, the mmul
products, the float-math operations, the log/exp stimulus -- is a class in
``TEMPLATE_CLASSES`` that each instruction constructs with its own arguments, so
the object is per instruction and it is the *class* that is shared.
"""

from __future__ import annotations

import unittest

from mmul_gen.catalog import ALL_INSTRUCTIONS, MATRIX_MULTIPLY_INSTRUCTIONS
from mmul_gen.templates import (
    ALL_TEMPLATES,
    ELEMENTWISE_TEMPLATE_CLASSES,
    TEMPLATE_CLASSES,
    MatrixSmall,
    Template,
)
from mmul_gen.templates.ones_uniform import OnesUniform, OnesUniform128, OnesUniformPayload
from mmul_gen.tests.helpers import machine


EXPECTED_TEMPLATE_NAMES = (
    "zero_acc",
    "zero_m",
    "acc_to_m",
    "m_to_acc",
    "row_column_roundtrip_with_edge_checks",
    "row_column_roundtrip_with_edge_checks",
    "position_roundtrip_and_memory_image",
    "position_roundtrip_and_memory_image",
    "position_roundtrip_and_memory_image",
    "position_roundtrip_and_memory_image",
    "physical_image_and_register_edge",
    # Backend ownership/ordering: fixed scenarios, no datatype dimension.
    "acquire_release_state",
    "busy_state",
    "acquire_release_state",
    "busy_state",
    "ones_uniform",
    "ones_uniform_128",
    "multi_acc_independent",
    # The two directions of the indexed packed-slot conversion.
    "packed_slot_write",
    "packed_slot_read",
    # The non-indexed storage/compute conversion round trip.
    "roundtrip_with_boundary_values",
    # The descriptor roundtrips are constructed per instruction (see
    # ``EXPECTED_TEMPLATE_CLASS_NAMES``); their probes are shared instances.
    "unsupported_dtype",
    "unsupported_dtype",
    "scalar_ingress",
    "integer128_ingress",
    "saturating_ingress",
    "saturating_integer128_ingress",
    "packed_storage_ingress",
    "floating_ingress",
    "unsupported_dtype_probe",
    "column_broadcast",
    "row_broadcast",
    "column_index",
    "row_index",
    "column_shift",
    "row_shift",
    "reduce_saturating_boundary",
    "gather_extra_dtype_index",
    "scatter_saturating_boundary",
)

#: The templates that carry per-instruction inputs, in registry order: the
#: elementwise templates, then the two descriptor roundtrips.  These are classes
#: rather than instances, because each instruction constructs the ones it runs.
EXPECTED_TEMPLATE_CLASS_NAMES = (
    "elementwise_integer_value_rules",
    "elementwise_integer_value_rules_128",
    "elementwise_saturating_boundary",
    "elementwise_saturating_boundary_128",
    "elementwise_float_nominal",
    "elementwise_float_special_values",
    "elementwise_float_semantics_sweep",
    "supported_dtype_roundtrip",
    "acc_span_exceptions",
    "acc_span_routing",
    "exp2_saturating_128",
    "exp2_saturating_boundary",
    "float_math_cases",
    "float_pair_sweep",
    "gather_indexed_elements",
    "ldexpacc_saturating_boundary",
    "nominal",
    "supported_dtype_roundtrip",
    "matrix_small",
    "mixed_signedness_multiple_square",
    "packed_small",
    "reduce_row_ramp",
    "saturating_boundary",
    "shift_register_source",
    "shift_scalar_source",
    "strided_conversion_pairs",
    "strided_normal_square",
    "strided_packed_storage",
    "zip_dual_source_ramp",
    "zip_extra_dtype_ramp",
)


class TemplateContractTests(unittest.TestCase):
    def test_the_inventory_lists_every_template_in_declaration_order(self) -> None:
        self.assertEqual(
            tuple(template.name for template in ALL_TEMPLATES),
            EXPECTED_TEMPLATE_NAMES,
        )

    def test_the_elementwise_templates_are_declared_in_canonical_order(self) -> None:
        self.assertEqual(
            tuple(cls.name for cls in ELEMENTWISE_TEMPLATE_CLASSES),
            EXPECTED_TEMPLATE_CLASS_NAMES[:7],
        )

    def test_a_constructed_template_is_never_also_a_shared_instance(self) -> None:
        """The registry and the shared-instance list are two tiers, not one."""

        self.assertEqual(
            tuple(cls.name for cls in TEMPLATE_CLASSES),
            EXPECTED_TEMPLATE_CLASS_NAMES,
        )
        self.assertEqual(
            set(TEMPLATE_CLASSES) & {type(template) for template in ALL_TEMPLATES},
            set(),
        )

    def test_every_template_is_a_documented_template_subclass(self) -> None:
        for template in ALL_TEMPLATES:
            with self.subTest(template=template.name):
                self.assertIsInstance(template, Template)
                self.assertTrue(type(template).__doc__)
                self.assertTrue(template.summary)
                self.assertNotIn("\n", template.summary)
                self.assertEqual(type(template).name, template.name)

    def test_summary_is_read_from_the_docstring_rather_than_restated(self) -> None:
        for template in ALL_TEMPLATES:
            with self.subTest(template=template.name):
                self.assertEqual(template.summary, type(template).__doc__.strip())
                self.assertNotIn("summary", vars(type(template)))

    def test_a_declared_datatype_domain_is_never_empty(self) -> None:
        for template in ALL_TEMPLATES:
            with self.subTest(template=template.name):
                if template.dtypes is None:
                    # A dtype-free template still runs, once, with no dtype.
                    self.assertEqual(template.iter_dtypes(machine()), (None,))
                    continue
                self.assertTrue(template.dtypes(machine()))

    def test_a_subclass_without_a_docstring_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "must document"):

            class Undocumented(Template):
                name = "undocumented"
                dtypes = MatrixSmall.dtypes

                def build(self, machine, instruction, dtype):
                    return ()

                def render(self, machine, instruction, case, out):
                    return None


class TemplateReuseTests(unittest.TestCase):
    def test_the_plain_product_templates_are_run_by_every_instruction(self) -> None:
        """The class is shared; the object is the instruction's own."""
        holders: dict[str, set[str]] = {}
        for instruction in MATRIX_MULTIPLY_INSTRUCTIONS:
            for template in instruction.templates:
                holders.setdefault(template.name, set()).add(instruction.name)
        for name in (
            "float_pair_sweep",
            "packed_small",
            "saturating_boundary",
            "mixed_signedness_multiple_square",
        ):
            with self.subTest(template=name):
                self.assertEqual(len(holders[name]), 6)
        self.assertEqual(len(holders["matrix_small"]), 5)

    def test_every_template_an_instruction_uses_comes_from_the_registry(self) -> None:
        """A template class is declared once, whatever binds its inputs.

        The other families hold the same *object* everywhere; the elementwise
        templates are constructed per instruction, so what must hold there is that
        the class is one the family declares -- a template written inside an
        instruction would be invisible to the inventory and to the tests that
        read it.
        """

        declared = {type(template) for template in ALL_TEMPLATES} | set(
            TEMPLATE_CLASSES
        )
        for instruction in ALL_INSTRUCTIONS:
            for template in instruction.templates:
                with self.subTest(mnemonic=instruction.name, template=template.name):
                    self.assertIn(type(template), declared)

    def test_the_other_families_share_their_template_objects(self) -> None:
        constructed = set(TEMPLATE_CLASSES)
        holders: dict[int, set[str]] = {}
        for instruction in ALL_INSTRUCTIONS:
            for template in instruction.templates:
                if type(template) in constructed:
                    continue
                holders.setdefault(id(template), set()).add(instruction.name)

        by_id = {id(template): template for template in ALL_TEMPLATES}
        self.assertEqual(set(holders), set(by_id), "an instruction used an undeclared template")

        pairs = sum(len(names) for names in holders.values())
        self.assertGreater(pairs, len(ALL_TEMPLATES), "no template is shared between instructions")

    def test_a_template_specialises_by_subclassing_only_what_changes(self) -> None:
        # ones_uniform_128 is ones_uniform with a different renderer, domain,
        # and resource predicate; the case builder is inherited unchanged.
        self.assertTrue(issubclass(OnesUniform128, OnesUniform))
        self.assertIs(OnesUniform128.build, OnesUniform.build)
        self.assertIsNot(OnesUniform128.render, OnesUniform.render)
        self.assertIsNot(OnesUniform128.dtypes, OnesUniform.dtypes)
        self.assertIsNot(OnesUniform128.fits, OnesUniform.fits)

    def test_the_inherited_builder_hands_the_renderer_the_base_payload(self) -> None:
        instruction = MATRIX_MULTIPLY_INSTRUCTIONS[0]
        config = machine()
        dtype = min(OnesUniform128().dtypes(config), key=lambda d: d.bits)
        cases = OnesUniform128().build(config, instruction, dtype)
        self.assertTrue(cases)
        for case in cases:
            self.assertIsInstance(case.payload, OnesUniformPayload)


if __name__ == "__main__":
    unittest.main()
