// =======================================================================================
// This Sail RISC-V architecture model, comprising all files and
// directories except where otherwise noted is subject the BSD
// two-clause license in the LICENSE file.
//
// SPDX-License-Identifier: BSD-2-Clause
// =======================================================================================
type ame_nlen_pow : Int = config extensions.Ztt.ame_nlen_pow
constraint 2 <= ame_nlen_pow <= 16
let ame_nlen_pow = sizeof(ame_nlen_pow)
type ame_nlen : Int = 2 ^ ame_nlen_pow
type ame_nelem : Int = 2 ^ (ame_nlen_pow * 2)
let ame_nlen = sizeof(ame_nlen)
let ame_nelem = sizeof(ame_nelem)

type ame_unit_dtype_size_pow : Int = config extensions.Ztt.ame_unit_dtype_size_pow
constraint 3 <= ame_unit_dtype_size_pow <= 63
let ame_unit_dtype_size_pow = sizeof(ame_unit_dtype_size_pow)
type ame_unit_dtype_size : Int = 2 ^ ame_unit_dtype_size_pow
let ame_unit_dtype_size = sizeof(ame_unit_dtype_size)

type ame_max_dtype_size_pow : Int = config extensions.Ztt.ame_max_dtype_size_pow
constraint 7 <= ame_max_dtype_size_pow <= 63 & ame_unit_dtype_size_pow <= ame_max_dtype_size_pow
let ame_max_dtype_size_pow = sizeof(ame_max_dtype_size_pow)
type ame_max_dtype_size : Int = 2 ^ ame_max_dtype_size_pow
let ame_max_dtype_size = sizeof(ame_max_dtype_size)

type mlen : Int = 2 ^ (ame_unit_dtype_size_pow + 2 * ame_nlen_pow)
let mlen = sizeof(mlen)

type acclen = 2 ^ (ame_max_dtype_size_pow + 2 * ame_nlen_pow)
let acclen = sizeof(acclen)
