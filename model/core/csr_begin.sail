// =======================================================================================
// This Sail RISC-V architecture model, comprising all files and
// directories except where otherwise noted is subject the BSD
// two-clause license in the LICENSE file.
//
// SPDX-License-Identifier: BSD-2-Clause
// =======================================================================================

// Mapping of csr addresses to their names.

val csr_name_map : csreg <-> string

scattered mapping csr_name_map

function csr_name(csr : csreg) -> string = csr_name_map(csr)
overload to_str = {csr_name}

// returns whether a CSR exists
val is_CSR_accessible : (csreg, Privilege, CSRAccessType) -> bool
scattered function is_CSR_accessible

// Some extensions allocate writable CSRs in an address range whose encoding
// normally denotes read-only state.  Those extensions declare the exception
// here; the generic CSR access check remains address-agnostic.
val is_CSR_writable : csreg -> bool
scattered function is_CSR_writable

// Extension state can constrain otherwise valid writes to mstatus/sstatus.
// The core applies this after status-field legalisation, keeping extension
// ownership rules out of the base status-register implementation.
val is_mstatus_write_legal : bits(64) -> bool
scattered function is_mstatus_write_legal

// returns the value of the CSR if it is defined
val read_CSR : csreg -> xlenbits
scattered function read_CSR

// returns new value (after legalisation) if the CSR is defined,
// otherwise a unit value indicating an illegal instruction.
val write_CSR : (csreg, xlenbits) -> result(xlenbits, unit)
scattered function write_CSR

// returns whether a virtual instruction exception has occurred
val is_CSR_exception_virtual : (csreg, Privilege, CSRAccessType) -> bool
scattered function is_CSR_exception_virtual
