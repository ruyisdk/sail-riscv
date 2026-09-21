# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
# Common test infrastructure for Ztt bare-metal tests.
# Include with: .include "test.inc"

# ── Entry point ──────────────────────────────────────────────────────────────
.text
.globl _start
_start:
    # AME context state resets to Off.  Tests enable the architectural
    # Initial state before issuing ame.acquire or any other AME instruction.
    li      t0, 0x02000000
    csrs    mstatus, t0

# ── tohost/fromhost memory region ────────────────────────────────────────────
.pushsection .tohost,"aw",@progbits
.align 8; .global tohost; tohost: .dword 0
.align 8; .global fromhost; fromhost: .dword 0
.popsection

# ── Signal pass and spin ──────────────────────────────────────────────────────
.macro RVMODEL_HALT_PASS
    li    x1, 1
    la    t0, tohost
.Lpass_\@:
    sw    x1, 0(t0)
    sw    x0, 4(t0)
    j     .Lpass_\@
.endm

# ── Signal fail and spin ──────────────────────────────────────────────────────
.macro RVMODEL_HALT_FAIL
    li    x1, 3
    la    t0, tohost
.Lfail_\@:
    sw    x1, 0(t0)
    sw    x0, 4(t0)
    j     .Lfail_\@
.endm

# ── Equality assertion ────────────────────────────────────────────────────────
# EXPECT reg, const  — if reg != const, halt with fail.
# Clobbers: t6
.macro EXPECT reg, expected
    li    t6, \expected
    beq   \reg, t6, .Lexpect_ok_\@
    RVMODEL_HALT_FAIL
.Lexpect_ok_\@:
.endm

# ── Illegal-instruction trap guard ────────────────────────────────────────────
# TRAP_GUARD_ARM installs the guard handler and zeroes the s11 trap counter.
# Each guarded instruction must be followed by EXPECT_TRAP n, where n counts
# the traps expected since arming.  The handler fails on any cause other than
# illegal instruction, steps over the 4-byte trapping instruction, and bumps
# s11.  Clobbers: t5, t6, s11.
.macro TRAP_GUARD_ARM
    la    t0, .Ltrap_guard_handler
    csrw  mtvec, t0
    li    s11, 0
.endm

.macro EXPECT_TRAP count
    EXPECT s11, \count
.endm

    j     .Ltrap_guard_done
.balign 4
.Ltrap_guard_handler:
    csrr  t5, mcause
    li    t6, 2
    bne   t5, t6, .Ltrap_guard_unexpected
    csrr  t5, mepc
    addi  t5, t5, 4
    csrw  mepc, t5
    addi  s11, s11, 1
    mret
.Ltrap_guard_unexpected:
    RVMODEL_HALT_FAIL
.Ltrap_guard_done:
