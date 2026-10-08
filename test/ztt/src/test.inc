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

# ── Trap guard ────────────────────────────────────────────────────────────────
# TRAP_GUARD_ARM installs the guard handler and zeroes the s11 trap counter.
# The handler always accepts an illegal-instruction trap, and one extra cause
# configured with TRAP_GUARD_ACCEPT_CAUSE.  s10 holds that cause, or -1 when no
# extra cause is accepted.  Each guarded instruction must be followed by
# EXPECT_TRAP n (any accepted cause) or EXPECT_TRAP_CAUSE n, cause (a specific
# one).  The handler fails on any other cause, steps over the 4-byte trapping
# instruction, and bumps s11.  Clobbers: t5, t6, s10, s11.
.macro TRAP_GUARD_ARM
    la    t0, .Ltrap_guard_handler
    csrw  mtvec, t0
    li    s11, 0
    li    s10, -1
.endm

# TRAP_GUARD_ACCEPT_CAUSE cause  — also accept this mcause as expected.
.macro TRAP_GUARD_ACCEPT_CAUSE cause
    li    s10, \cause
.endm

.macro EXPECT_TRAP count
    EXPECT s11, \count
.endm

# EXPECT_TRAP_CAUSE count, cause  — like EXPECT_TRAP, and mcause must be cause.
.macro EXPECT_TRAP_CAUSE count, cause
    EXPECT s11, \count
    csrr  t5, mcause
    EXPECT t5, \cause
.endm

    j     .Ltrap_guard_done
.balign 4
.Ltrap_guard_handler:
    csrr  t5, mcause
    li    t6, 2
    beq   t5, t6, .Ltrap_guard_step
    beq   t5, s10, .Ltrap_guard_step
    j     .Ltrap_guard_unexpected
.Ltrap_guard_step:
    csrr  t5, mepc
    addi  t5, t5, 4
    csrw  mepc, t5
    addi  s11, s11, 1
    mret
.Ltrap_guard_unexpected:
    RVMODEL_HALT_FAIL
.Ltrap_guard_done:
