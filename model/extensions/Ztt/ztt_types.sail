// =======================================================================================
// This Sail RISC-V architecture model, comprising all files and
// directories except where otherwise noted is subject the BSD
// two-clause license in the LICENSE file.
//
// SPDX-License-Identifier: BSD-2-Clause
// =======================================================================================
let ame_num_m_regs : {16, 32} = config extensions.Ztt.ame_num_m_regs

let ame_num_acc_regs : {1, 2, 4, 8, 16} = config extensions.Ztt.ame_num_acc_regs

// Backend ownership mode.  Keep this as a string configuration value, like
// other reserved-behavior settings; validation is handled by validate_config.
let ame_backend : string = config extensions.Ztt.ame_backend

// Which NaN mantissa encodings of E5M2 are signaling is implementation-defined:
// OCP OFP8 Rev 1.0 §5.1 gives the three encodings (01, 10, 11) but states that
// "Interpretation of the three mantissa values for NaNs is not defined."
//   false (default) -- QEMU-aligned: no E5M2 NaN is signaling, so no NV is
//                      raised; the delivered result is still the canonical
//                      quiet NaN.  This is the default because the two
//                      implementations we compare against must agree out of the
//                      box, and QEMU is the reference for that comparison.
//   true            -- IEEE 754 quiet-bit convention: frac[1] clear (0x7D,
//                      0xFD) is a signaling NaN and raises NV.
// Only E5M2 is affected; E4M3 has no signaling NaN encoding and the IEEE
// formats pin their quiet bit in IEEE 754 itself.
let ame_e5m2_nan_ieee : bool = config extensions.Ztt.ztt_e5m2_nan_ieee

type amereglen = bits(mlen)

type ameaccreglen = bits(acclen)

newtype ameregidx = Ameregidx : bits(5)

newtype ameregno = Ameregno : range(0, 31)

newtype mdregidx = Mdregidx : bits(5)

newtype mdregno = Mdregno : range(0, 31)

newtype ameaccregidx = Ameaccregidx : bits(5)

newtype ameaccregno = Ameaccregno : range(0, 31)

newtype ameadregidx = Ameadregidx : bits(5)

newtype ameadregno = Ameadregno : range(0, 31)
