#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

GEN_ROOT = Path(__file__).resolve().parents[1]
if str(GEN_ROOT) not in sys.path:
    sys.path.insert(0, str(GEN_ROOT))

from check_manual_sync import read_sail_execute_names  # noqa: E402


class SailExecuteDiscoveryTests(unittest.TestCase):
    def test_discovers_grouped_family_cases_and_fixed_clauses(self) -> None:
        sail = """
mapping ame_int_op : ame_int_op <-> bits(3) = {
  AME_INT_ADD <-> 0b000
}
function clause execute ARITH_R2_MD_MS_TYPE(op, rd, rs1) = {
  match op {
    AME_MABS_EW => {
      internal_error(__FILE__, __LINE__, "Ztt execute implementation missing: mabs.ew")
    },
  }
}
function clause execute AME_AME_RELEASE() = {
  RETIRE_SUCCESS
}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ztt_arithmetic_insts.sail"
            path.write_text(sail)
            execute, stubs = read_sail_execute_names(path)

        self.assertEqual(execute, {"AME_MABS_EW", "AME_AME_RELEASE"})
        self.assertEqual(stubs, {"mabs.ew"})

    def test_floating_point_families_have_a_dedicated_sail_file(self) -> None:
        model_root = GEN_ROOT.parents[2] / "model/extensions/Ztt"
        float_text = (model_root / "ztt_float_insts.sail").read_text()
        self.assertIn("union clause instruction = FP_FR2_MD_MS_TYPE", float_text)
        self.assertIn("union clause instruction = FP_FR3_MD_MS_MS_TYPE", float_text)
        self.assertIn("AME_MCOS_EW", float_text)
        self.assertIn("AME_MLOG2SUB_EW_X", float_text)

        arithmetic_text = (model_root / "ztt_arithmetic_insts.sail").read_text()
        math_text = (model_root / "ztt_math_insts.sail").read_text()
        for source in (arithmetic_text, math_text):
            self.assertNotIn("FP_FR2_MD_MS_TYPE", source)
            self.assertNotIn("FP_FR3_MD_MS_MS_TYPE", source)


if __name__ == "__main__":
    unittest.main()
