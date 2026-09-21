#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""New-architecture Ztt matrix-multiply test generator.

Layout
------
``instructions/<mnemonic>.py``
    One module per instruction.  Each declares a
    :class:`~mmul_gen.instruction.MatrixMultiplyInstruction` subclass whose class
    attributes are its name, summary, operands, and the templates it is
    generated from.  Datatype coverage is derived from those templates rather than declared
    again.  The assembly itself comes from the templates in
    :mod:`mmul_gen.templates`.
``catalog.py``
    The entry point that orders those instruction objects and renders them.
``machine.py`` / ``registers.py``
    The N/UDS/M/ACC configuration, the named datatype domains, and the M/ACC
    register-layout declarations.
``templates/``
    One module per template, each a :class:`~mmul_gen.templates.base.Template`
    subclass with its own docstring, datatype domain, case builder, and
    renderer.  ``templates/__init__.py`` instantiates the inventory.
``reference.py`` / ``inputs.py`` / ``float_formats.py``
    Expected values and stimulus recipes the templates consume.
``asm.py``
    Instruction-agnostic GAS emission primitives.

Running it::

    cd sail-ame/test/ztt/gen
    python3 -m mmul_gen --list
    python3 -m mmul_gen --n 8 --uds 8 --m 32 --acc 4 \\
        --out-dir <out-dir>
    python3 -m mmul_gen.tests

This package reuses the repository's single sources of truth for ISA reference
data -- :mod:`fp_semantics` (IEEE/OCP boundary encodings) and
:mod:`numeric_reference` (the cross-checked exact integer matrix product).
"""

from mmul_gen.catalog import (
    MATRIX_MULTIPLY_INSTRUCTIONS,
    describe_instructions,
    find_instruction,
    generate_all,
)
from mmul_gen.instruction import (
    GeneratedSource,
    Operand,
)
from mmul_gen.instructions.mmul.base import MatrixMultiplyInstruction
from mmul_gen.machine import MachineConfig

__all__ = [
    "MATRIX_MULTIPLY_INSTRUCTIONS",
    "GeneratedSource",
    "MachineConfig",
    "MatrixMultiplyInstruction",
    "Operand",
    "describe_instructions",
    "find_instruction",
    "generate_all",
]
