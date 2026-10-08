#!/usr/bin/env ruby
# frozen_string_literal: true

# Generate Sail encdec clauses and execute implementations for Ztt from the
# current prose specification instruction snapshot.
#
# Usage:
#   ruby generators/gen_ztt_sail.rb
#   ruby generators/gen_ztt_sail.rb --output-dir path/to/generated
#   ruby generators/gen_ztt_sail.rb --output path/to/ztt_combined.sail
#   ruby generators/gen_ztt_sail.rb --stdout
#   ruby generators/gen_ztt_sail.rb --no-execute

require "fileutils"
require "json"
require "optparse"
require "pathname"
require "set"
require "tempfile"
require_relative "manual_instruction_data"

MACHINE_READABLE_ROOT = Pathname.new(__FILE__).dirname.parent.expand_path
DEFAULT_OUT_DIR = MACHINE_READABLE_ROOT.parent.parent / "model/extensions/Ztt"
SEMANTIC_SOURCE_DIR = MACHINE_READABLE_ROOT / "generators/sail_semantics"
IMPLEMENTED_INSTRUCTIONS_FILE = MACHINE_READABLE_ROOT / "manual-main/implemented-instructions.json"
IMPLEMENTED_INSTRUCTIONS = JSON.parse(IMPLEMENTED_INSTRUCTIONS_FILE.read)
  .fetch("instructions")
  .to_set
  .freeze

ZTT_PRELUDE = <<~'SAIL'
  function clause currentlyEnabled(Ext_Ztt) = hartSupports(Ext_Ztt)

  function ame_retire_if(success : bool) -> ExecutionResult =
    if success then RETIRE_SUCCESS else Illegal_Instruction()

  function ame_check_mreg_operand(reg : bits(5)) -> bool =
    ame_check_mreg_group(Ameregidx(reg), 1)

  function ame_check_mreg_group_operand(reg : bits(5), nregs : nat) -> bool =
    ame_check_mreg_group(Ameregidx(reg), nregs)

  // AME load/store helpers.  Opaque transfers operate on exactly one physical
  // M register; typed transfers use their datatype only to arrange a portable
  // row- or column-major memory image.

  function ame_memory_exception_at_base(rs1 : regidx, access : MemoryAccessType(mem_payload),
                                        result : ExecutionResult)
    -> ExecutionResult = {
    match result {
      Trap(_, exc, _) => memory_exception(exc.trap, bits_of(Virtaddr(X(rs1))), access),
      _ => result,
    }
  }

  // Check every byte before a multi-byte AME store begins.  The normal RAM
  // backend then cannot fail after this validation.  If an actual vmem_write
  // nevertheless fails, every store helper immediately reports that error at
  // the instruction base address.
  // TODO: replace the byte-wise commit with a transactional memory API that
  // can roll back earlier writes after a late device/PMA/backend failure.
  function ame_check_store_byte(rs1 : regidx, byte_offset : nat)
    -> result(unit, ExecutionResult) = {
    let access = Store(Data);
    let vaddr : virtaddr = match get_transformed_data_addr(
      rs1, to_bits_unsafe(xlen, byte_offset), access, 1
    ) {
      Ext_DataAddr_Error(e) => return Err(Ext_DataAddr_Check_Failure(e)),
      Ext_DataAddr_OK(vaddr) => vaddr,
    };
    let eff_priv = effectivePrivilege(access, mstatus, cur_privilege);
    match translateAddr(vaddr, access, eff_priv) {
      Err(e, _) => Err(memory_exception(e.trap, bits_of(Virtaddr(X(rs1))), access)),
      Ok(paddr, pbmt, _) => {
        match phys_access_check(access, pbmt, eff_priv, paddr, 1, false) {
          Err(e) => Err(memory_exception(e, bits_of(Virtaddr(X(rs1))), access)),
          Ok(_) => Ok(()),
        }
      }
    }
  }

  // The model's M-register representation is mlen bits, so an opaque transfer
  // is mlen / 8 bytes and never reads Md.  The generic vmem API cannot prove
  // every legal parameterization fits one access, so stage the fixed-size image
  // byte-wise and commit the physical register only after all reads succeed.
  function ame_load_mreg_raw(md : ameregidx, rs1 : regidx) -> ExecutionResult = {
    var reg_data : amereglen = zeros();
    foreach (byte from 0 to (mlen / 8 - 1)) {
      match vmem_read(rs1, to_bits_unsafe(xlen, byte), 1, Load(Data), false, false, false) {
        Ok(value) => reg_data = [reg_data with (byte * 8 + 7) .. (byte * 8) = value],
        Err(e) => return ame_memory_exception_at_base(rs1, Load(Data), e),
      }
    };
    M(md) = reg_data;
    RETIRE_SUCCESS
  }

  function ame_store_mreg_raw(ms1 : ameregidx, rs1 : regidx) -> ExecutionResult = {
    let reg_data = M(ms1);
    foreach (byte from 0 to (mlen / 8 - 1)) {
      match ame_check_store_byte(rs1, byte) {
        Ok(()) => (),
        Err(e) => return e,
      }
    };
    foreach (byte from 0 to (mlen / 8 - 1)) {
      match vmem_write(rs1, to_bits_unsafe(xlen, byte), 1,
                       reg_data[(byte * 8 + 7) .. (byte * 8)], Store(Data), false, false, false) {
        Ok(_) => (),
        Err(e) => return ame_memory_exception_at_base(rs1, Store(Data), e),
      }
    };
    RETIRE_SUCCESS
  }

  function ame_square_memory_bytes(dtype : bits(32)) -> nat =
    (ame_total_elements(dtype) * ame_dtype_size(dtype) + 7) / 8

  // Staging every byte before decoding means a fault cannot leave a partially
  // updated M register group.  It also gives packed elements their specified
  // contiguous bit layout and avoids a special memory access width for 128-bit
  // elements.
  function ame_read_square_memory_bytes(rs1 : regidx, byte_count : nat)
    -> result(bits(acclen), ExecutionResult) = {
    var data : bits(acclen) = zeros();
    foreach (byte from 0 to (acclen / 8 - 1)) {
      if byte < byte_count then {
        match vmem_read(rs1, to_bits_unsafe(xlen, byte), 1, Load(Data), false, false, false) {
          Ok(value) => data = [data with (byte * 8 + 7) .. (byte * 8) = value],
          Err(e) => return Err(ame_memory_exception_at_base(rs1, Load(Data), e)),
        }
      }
    };
    Ok(data)
  }

  function ame_write_square_memory_bytes(rs1 : regidx, data : bits(acclen),
                                         byte_count : nat)
    -> ExecutionResult = {
    foreach (byte from 0 to (acclen / 8 - 1)) {
      if byte < byte_count then {
        match ame_check_store_byte(rs1, byte) {
          Ok(()) => (),
          Err(e) => return e,
        }
      }
    };
    foreach (byte from 0 to (acclen / 8 - 1)) {
      if byte < byte_count then {
        match vmem_write(rs1, to_bits_unsafe(xlen, byte), 1,
                         data[(byte * 8 + 7) .. (byte * 8)], Store(Data), false, false, false) {
          Ok(_) => (),
          Err(e) => return ame_memory_exception_at_base(rs1, Store(Data), e),
        }
      }
    };
    RETIRE_SUCCESS
  }

  function ame_square_memory_to_rm(dtype : bits(32), memory_data : bits(acclen),
                                   column_major : bool) -> bits(acclen) = {
    let size = ame_dtype_size(dtype);
    var result : bits(acclen) = zeros();
    foreach (memory_index from 0 to (ame_total_elements(dtype) - 1)) {
      let square = memory_index / ame_nelem;
      let within_square = memory_index % ame_nelem;
      let element_index = if column_major then
        square * ame_nelem + (within_square % ame_nlen) * ame_nlen + (within_square / ame_nlen)
      else memory_index;
      result = insert_elem_rm(result, size, element_index,
        extract_elem_rm(memory_data, size, memory_index))
    };
    result
  }

  function ame_square_rm_to_memory(dtype : bits(32), rm_data : bits(acclen),
                                   column_major : bool) -> bits(acclen) = {
    let size = ame_dtype_size(dtype);
    var result : bits(acclen) = zeros();
    foreach (memory_index from 0 to (ame_total_elements(dtype) - 1)) {
      let square = memory_index / ame_nelem;
      let within_square = memory_index % ame_nelem;
      let element_index = if column_major then
        square * ame_nelem + (within_square % ame_nlen) * ame_nlen + (within_square / ame_nlen)
      else memory_index;
      result = insert_elem_rm(result, size, memory_index,
        extract_elem_rm(rm_data, size, element_index))
    };
    result
  }

  function ame_load_mreg_square_memory(md : ameregidx, rs1 : regidx,
                                       column_major : bool) -> ExecutionResult = {
    let dtype : bits(32) = MD(Mdregidx(ameregidx_bits(md)));
    if not(ame_datatype_supported(dtype)) then {
      ame_set_unsupported();
      return RETIRE_SUCCESS;
    };
    let size = ame_dtype_size(dtype);
    let nregs = ame_nregs(size);
    if not(ame_check_mreg_group(md, nregs)) then return Illegal_Instruction();
    let total_bytes = ame_square_memory_bytes(dtype);
    let alignment = min(total_bytes, 4096);
    if unsigned(X(rs1)) % max(1, alignment) != 0 then
      return memory_exception(E_Load_Addr_Align(), bits_of(Virtaddr(X(rs1))), Load(Data));

    match ame_read_square_memory_bytes(rs1, total_bytes) {
      Ok(memory_data) => { write_m_square_rm(dtype, md,
                            ame_square_memory_to_rm(dtype, memory_data, column_major));
                           RETIRE_SUCCESS },
      Err(e) => e,
    }
  }

  function ame_store_mreg_square_memory(ms1 : ameregidx, rs1 : regidx,
                                        column_major : bool) -> ExecutionResult = {
    let dtype : bits(32) = MD(Mdregidx(ameregidx_bits(ms1)));
    if not(ame_datatype_supported(dtype)) then {
      ame_set_unsupported();
      return RETIRE_SUCCESS;
    };
    let size = ame_dtype_size(dtype);
    let nregs = ame_nregs(size);
    if not(ame_check_mreg_group(ms1, nregs)) then return Illegal_Instruction();
    let total_bytes = ame_square_memory_bytes(dtype);
    let alignment = min(total_bytes, 4096);
    if unsigned(X(rs1)) % max(1, alignment) != 0 then
      return memory_exception(E_SAMO_Addr_Align(), bits_of(Virtaddr(X(rs1))), Store(Data));

    ame_write_square_memory_bytes(rs1,
      ame_square_rm_to_memory(dtype, read_m_square_rm(dtype, ms1), column_major),
      total_bytes)
  }

  // Strided square transfers stage independently byte-rounded segments before
  // committing their destination.  The largest legal segment is a row of
  // 128-bit elements.  A transposed transfer has one segment per column of
  // every packed square; the smallest architectural element is 4 bits, so
  // UDS/4 is the configured upper bound on that packing factor.
  type ame_strided_segment = bits(ame_nlen * ame_max_dtype_size)
  type ame_max_strided_segments : Int = 2 ^ (ame_unit_dtype_size_pow - 2) * ame_nlen
  let ame_max_strided_segments = sizeof(ame_max_strided_segments)
  type ame_strided_segments = vector(ame_max_strided_segments, dec, ame_strided_segment)

  function ame_read_strided_segment(rs1 : regidx, byte_offset : nat,
                                    byte_count : nat)
    -> result(ame_strided_segment, ExecutionResult) = {
    var segment : ame_strided_segment = zeros();
    foreach (byte from 0 to (ame_nlen * ame_max_dtype_size / 8 - 1)) {
      if byte < byte_count then {
        match vmem_read(rs1, to_bits_unsafe(xlen, byte_offset + byte), 1,
                        Load(Data), false, false, false) {
          Ok(data) => segment = [segment with (byte * 8 + 7) .. (byte * 8) = data],
          Err(e) => return Err(ame_memory_exception_at_base(rs1, Load(Data), e)),
        }
      }
    };
    Ok(segment)
  }

  function ame_extract_strided_elem(segment : ame_strided_segment, element_size : nat,
                                    bit_offset : nat) -> bits(ame_max_dtype_size) = {
    assert(bit_offset + element_size <= ame_nlen * ame_max_dtype_size,
      "strided element extends beyond segment bounds");
    match element_size {
       4  => { let value : bits( 4) = segment[(bit_offset +  3) .. bit_offset]; zero_extend(ame_max_dtype_size, value) },
       8  => { let value : bits( 8) = segment[(bit_offset +  7) .. bit_offset]; zero_extend(ame_max_dtype_size, value) },
      16  => { let value : bits(16) = segment[(bit_offset + 15) .. bit_offset]; zero_extend(ame_max_dtype_size, value) },
      32  => { let value : bits(32) = segment[(bit_offset + 31) .. bit_offset]; zero_extend(ame_max_dtype_size, value) },
      64  => { let value : bits(64) = segment[(bit_offset + 63) .. bit_offset]; zero_extend(ame_max_dtype_size, value) },
      128 => { let value : bits(128) = segment[(bit_offset + 127) .. bit_offset]; zero_extend(ame_max_dtype_size, value) },
      _   => internal_error(__FILE__, __LINE__, "unsupported strided element size")
    }
  }

  function ame_insert_strided_elem(segment : ame_strided_segment, element_size : nat,
                                   bit_offset : nat,
                                   ms1_val : bits(ame_max_dtype_size)) -> ame_strided_segment = {
    assert(bit_offset + element_size <= ame_nlen * ame_max_dtype_size,
      "strided element extends beyond segment bounds");
    match element_size {
       4  => [segment with (bit_offset +  3) .. bit_offset = ms1_val[ 3 .. 0]],
       8  => [segment with (bit_offset +  7) .. bit_offset = ms1_val[ 7 .. 0]],
      16  => [segment with (bit_offset + 15) .. bit_offset = ms1_val[15 .. 0]],
      32  => [segment with (bit_offset + 31) .. bit_offset = ms1_val[31 .. 0]],
      64  => [segment with (bit_offset + 63) .. bit_offset = ms1_val[63 .. 0]],
      128 => [segment with (bit_offset + 127) .. bit_offset = ms1_val[127 .. 0]],
      _   => internal_error(__FILE__, __LINE__, "unsupported strided element size")
    }
  }

  function ame_store_strided_segment(rs1 : regidx, byte_offset : nat,
                                     segment : ame_strided_segment,
                                     byte_count : nat) -> result(unit, ExecutionResult) = {
    foreach (byte from 0 to (ame_nlen * ame_max_dtype_size / 8 - 1)) {
      if byte < byte_count then {
        match vmem_write(rs1, to_bits_unsafe(xlen, byte_offset + byte), 1,
                         segment[(byte * 8 + 7) .. (byte * 8)], Store(Data), false, false, false) {
          Ok(_) => (),
          Err(e) => return Err(ame_memory_exception_at_base(rs1, Store(Data), e)),
        }
      }
    };
    Ok(())
  }

  function ame_load_mreg_square_strided_memory(md : ameregidx, rs1 : regidx,
                                                rs2 : regidx, transposed : bool)
    -> ExecutionResult = {
    let dtype : bits(32) = MD(Mdregidx(ameregidx_bits(md)));
    if not(ame_datatype_supported(dtype)) then {
      ame_set_unsupported();
      return RETIRE_SUCCESS;
    };
    let size = ame_dtype_size(dtype);
    let nregs = ame_nregs(size);
    if not(ame_check_mreg_group(md, nregs)) then return Illegal_Instruction();

    let pack_factor = if ame_is_storage_only(dtype) then ame_pack_factor(size) else 1;
    let element_bytes = (size + 7) / 8;
    let alignment = min(element_bytes, 4096);
    if unsigned(X(rs1)) % max(1, alignment) != 0 then
      return memory_exception(E_Load_Addr_Align(), bits_of(Virtaddr(X(rs1))), Load(Data));

    let segment_count = if transposed then pack_factor * ame_nlen else ame_nlen;
    let segment_bits = if transposed then ame_nlen * size else pack_factor * ame_nlen * size;
    let segment_bytes = (segment_bits + 7) / 8;
    let stride = unsigned(X(rs2));
    var segments : ame_strided_segments = vector_init(zeros());

    foreach (seg from 0 to (ame_max_strided_segments - 1)) {
      if seg < segment_count then {
        match ame_read_strided_segment(rs1, seg * stride, segment_bytes) {
          Ok(segment) => segments[seg] = segment,
          Err(e) => return e,
        }
      }
    };

    var result : bits(acclen) = zeros();
    foreach (sq from 0 to (pack_factor - 1)) {
      foreach (row from 0 to (ame_nlen - 1)) {
        foreach (col from 0 to (ame_nlen - 1)) {
          let segment = if transposed then sq * ame_nlen + col else row;
          let bit_offset = if transposed then row * size else (sq * ame_nlen + col) * size;
          // Supported dtypes make this modulo an identity; it supplies the
          // static vector-bound proof that Sail cannot derive from dtype bits.
          let segment_index = segment % ame_max_strided_segments;
          let value = ame_extract_strided_elem(segments[segment_index], size, bit_offset);
          result = insert_elem_rm(result, size, sq * ame_nelem + row * ame_nlen + col, value)
        }
      }
    };
    write_m_square_rm(dtype, md, result);
    RETIRE_SUCCESS
  }

  function ame_store_mreg_square_strided_memory(ms1 : ameregidx, rs1 : regidx,
                                                 rs2 : regidx, transposed : bool)
    -> ExecutionResult = {
    let dtype : bits(32) = MD(Mdregidx(ameregidx_bits(ms1)));
    if not(ame_datatype_supported(dtype)) then {
      ame_set_unsupported();
      return RETIRE_SUCCESS;
    };
    let size = ame_dtype_size(dtype);
    let nregs = ame_nregs(size);
    if not(ame_check_mreg_group(ms1, nregs)) then return Illegal_Instruction();

    let pack_factor = if ame_is_storage_only(dtype) then ame_pack_factor(size) else 1;
    let element_bytes = (size + 7) / 8;
    let alignment = min(element_bytes, 4096);
    if unsigned(X(rs1)) % max(1, alignment) != 0 then
      return memory_exception(E_SAMO_Addr_Align(), bits_of(Virtaddr(X(rs1))), Store(Data));

    let segment_count = if transposed then pack_factor * ame_nlen else ame_nlen;
    let segment_bits = if transposed then ame_nlen * size else pack_factor * ame_nlen * size;
    let segment_bytes = (segment_bits + 7) / 8;
    let stride = unsigned(X(rs2));
    let square = read_m_square_rm(dtype, ms1);
    var segments : ame_strided_segments = vector_init(zeros());

    foreach (sq from 0 to (pack_factor - 1)) {
      foreach (row from 0 to (ame_nlen - 1)) {
        foreach (col from 0 to (ame_nlen - 1)) {
          let segment = if transposed then sq * ame_nlen + col else row;
          let bit_offset = if transposed then row * size else (sq * ame_nlen + col) * size;
          // See the corresponding load-side vector-bound proof above.
          let segment_index = segment % ame_max_strided_segments;
          let value = extract_elem_rm(square, size, sq * ame_nelem + row * ame_nlen + col);
          segments[segment_index] = ame_insert_strided_elem(
            segments[segment_index], size, bit_offset, value)
        }
      }
    };

    foreach (seg from 0 to (ame_max_strided_segments - 1)) {
      if seg < segment_count then {
        foreach (byte from 0 to (ame_nlen * ame_max_dtype_size / 8 - 1)) {
          if byte < segment_bytes then {
            match ame_check_store_byte(rs1, seg * stride + byte) {
              Ok(()) => (),
              Err(e) => return e,
            }
          }
        }
      }
    };

    foreach (seg from 0 to (ame_max_strided_segments - 1)) {
      if seg < segment_count then {
        match ame_store_strided_segment(rs1, seg * stride, segments[seg], segment_bytes) {
          Ok(()) => (),
          Err(e) => return e,
        }
      }
    };
    RETIRE_SUCCESS
  }
SAIL

ZTT_ENCDEC_PRELUDE = <<~'SAIL'
  function clause currentlyEnabled(Ext_Ztt) = hartSupports(Ext_Ztt)
SAIL

COMMON_FILE = "ztt_insts_common.sail"
TYPE_FILE = "ztt_instruction_types.sail"
CATEGORY_FILES = {
  "Resource Management" => "ztt_resource_insts.sail",
  "Datatype Management" => "ztt_datatype_insts.sail",
  "Floating Point" => "ztt_float_insts.sail",
  "Elementwise Arithmetic" => "ztt_arithmetic_insts.sail",
  "Bitwise" => "ztt_bitwise_insts.sail",
  "Compare and Predication" => "ztt_compare_insts.sail",
  "Permutation" => "ztt_permutation_insts.sail",
  "State Management" => "ztt_state_insts.sail",
  "Elementwise Math Functions" => "ztt_math_insts.sail",
  "Memory" => "ztt_memory_insts.sail",
  "Matrix Multiply" => "ztt_mmul_insts.sail",
  "Reduction" => "ztt_reduction_insts.sail"
}.freeze

# Keep generated selector names close to the V-extension convention.  The
# operand-role suffix remains part of a family name because it describes the
# Sail argument types and the assembly interface.
CATEGORY_CODES = {
  "Resource Management" => "res",
  "Datatype Management" => "dtype",
  "Floating Point" => "fp",
  "Elementwise Arithmetic" => "arith",
  "Bitwise" => "bit",
  "Compare and Predication" => "cmp",
  "Permutation" => "perm",
  "State Management" => "state",
  "Elementwise Math Functions" => "math",
  "Memory" => "mem",
  "Matrix Multiply" => "mmul",
  "Reduction" => "red"
}.freeze

# The manual's "Register move / data conversion" category stays folded into the
# Permutation Sail file: its instructions already form separate
# operand-signature families (mconv, mmove*, mpack/munpack, mbcast) there and
# their semantics live in sail_semantics/ztt_conversion.sail.  Keep the fold
# explicit so the importer can record manual category names verbatim.
CATEGORY_ALIASES = {
  "Register move / data conversion" => "Permutation"
}.freeze

# These instructions require floating-point source and destination datatypes
# in the v0.6 manual.  Keep them in separate FP families so their generated
# selectors and execute clauses are as easy to audit as V's FVV/VV families.
# Instructions that accept both integer and floating-point tuples remain in
# the ordinary family: their opcode has only one architectural decode.
FLOAT_ONLY_INSTRUCTIONS = %w[
  mcos.ew
  mexp2.ew
  mfrintm.ew
  mfrintn.ew
  mfrintp.ew
  mfrintz.ew
  mlog2.ew
  mlog2sub.ew
  mlog2sub.ew.x
  mrec.ew
  mrsqrt.ew
  msin.ew
  msqrt.ew
  msublog2.ew
  msublog2.ew.x
  mtanh.ew
].to_set.freeze

# Sail follows the V-extension convention of keeping instruction encodings and
# their execution semantics in the same category file.  These source
# fragments are inserted before the generated encoding clauses.  They remain
# separate generator inputs so regeneration cannot overwrite reviewed semantic
# code while the model still presents one file per instruction category.
SEMANTIC_SOURCES = {
  "Floating Point" => %w[ztt_float.sail],
  "Elementwise Arithmetic" => %w[ztt_arithmetic.sail],
  "Bitwise" => %w[ztt_bitwise.sail],
  "Compare and Predication" => %w[ztt_compare.sail],
  "Permutation" => %w[ztt_conversion.sail ztt_permutation.sail],
  "Matrix Multiply" => %w[ztt_matrix.sail],
  "Reduction" => %w[ztt_reduction.sail]
}.freeze

# The AME encoding uses a small number of fixed layouts.  Keep one union
# constructor per semantic category, layout, and operand-role signature, like
# the V extension's VVTYPE/NVTYPE families, and carry the instruction-specific
# funct field as an enum.
FAMILY_LAYOUTS = {
  r1: {
    constructor: "R1",
    type: "r1funct17",
    width: 17,
    arguments: %w[rd]
  },
  r2: {
    constructor: "R2",
    type: "r2funct12",
    width: 12,
    arguments: %w[rd rs1]
  },
  fp_r2: {
    constructor: "FR2",
    type: "fpr2funct12",
    width: 12,
    arguments: %w[rd rs1]
  },
  r3_pair: {
    constructor: "R3PAIR",
    type: "r3pairfunct7",
    width: 7,
    arguments: %w[ms1 ms2]
  },
  r3: {
    constructor: "R3",
    type: "r3funct7",
    width: 7,
    arguments: %w[rd rs1 rs2]
  },
  fp_r3: {
    constructor: "FR3",
    type: "fpr3funct7",
    width: 7,
    arguments: %w[rd rs1 rs2]
  }
}.freeze

# Family grouping is deliberately based on operand roles, not only on the
# instruction's bit layout.  This mirrors V's VVTYPE/VXTYPE split: instructions
# may share a constructor only when their assembly operand interface matches.
OPERAND_ROLE_CODES = {
  "md" => "md",
  "ms" => "ms",
  "ms1" => "ms",
  "ms2" => "ms",
  "rd" => "xd",
  "rs1" => "xs",
  "rs2" => "xs",
  "acc" => "ad",
  "ad" => "ad"
}.freeze

def assembly_operand_tokens(inst)
  inst.fetch(:assembly).to_s.split(",").map(&:strip).reject(&:empty?)
end

def operand_role_code(inst, token)
  operand = token.delete("()")
  code = OPERAND_ROLE_CODES.fetch(operand) do
    raise "#{inst.fetch(:name)}: unsupported operand role #{operand}"
  end

  # Accumulator direction is encoded by the instruction interface rather than
  # by the `acc`/`ad` spelling alone.
  code = "as" if operand == "acc" && inst.fetch(:name) == "mmov.m.a"
  code = "as" if operand == "ad" && inst.fetch(:name) == "agettyp"
  code = "xa" if token.start_with?("(")
  code
end

def operand_signature(inst)
  assembly_operand_tokens(inst).map { |token| operand_role_code(inst, token) }
end

def category_code(category)
  CATEGORY_CODES.fetch(category) do
    raise "missing short code for Ztt instruction category: #{category}"
  end
end

# Floating-point-only instructions are kept in a dedicated category file,
# even when the prose manual places them beside integer arithmetic or math
# operations.  Instructions whose operation is polymorphic remain in their
# original category and ordinary family so one architectural opcode has one
# decode path.
def instruction_category(inst)
  return "Floating Point" if FLOAT_ONLY_INSTRUCTIONS.include?(inst.fetch(:name))

  category = inst.fetch(:category)
  CATEGORY_ALIASES.fetch(category, category)
end

def family_key(inst, format, signature)
  "#{category_code(instruction_category(inst))}:#{format}:#{signature.join("_")}".to_sym
end

def family_parts(family)
  category, format, signature = family.to_s.split(":", 3)
  [category.to_sym, format.to_sym, signature ? signature.split("_") : []]
end

def family_comment(family)
  category, layout, signature = family_parts(family)
  category_name = category == :fp ? "Floating Point" : category.to_s.tr("_", " ").split.map(&:capitalize).join(" ")
  "#{category_name}: #{layout.to_s.upcase}(#{signature.join(', ')}) instruction family"
end

def semantic_source_text(category)
  SEMANTIC_SOURCES.fetch(category, []).map do |filename|
    path = SEMANTIC_SOURCE_DIR / filename
    raise "missing Ztt semantic source: #{path}" unless path.file?

    path.read.rstrip
  end.join("\n\n")
end

def retire_if_true(call)
  ["  ame_retire_if(#{call})"]
end

def retire_mmul_accum_2d(subtract_product:, transpose_a:, transpose_b:)
  [
    "  let md_dtype : bits(32) = AD(Ameadregidx(acc));",
    "  let ms1_dtype : bits(32) = MD(Mdregidx(ms1));",
    "  let ms2_dtype : bits(32) = MD(Mdregidx(ms2));",
    "  ame_retire_if(ame_mmul_2d(md_dtype, ms1_dtype, ms2_dtype, Ameaccregidx(acc), Ameregidx(ms1), Ameregidx(ms2), true, #{subtract_product}, #{transpose_a}, #{transpose_b}))"
  ]
end

BASE_EXECUTE_BODIES = {
  "ame.acquire" => [
    "  X(Regidx(trunc(xd))) = ame_acquire_backend(X(Regidx(trunc(xs))));",
    "  RETIRE_SUCCESS"
  ],
  "ame.release" => [
    "  ame_release_backend();",
    "  RETIRE_SUCCESS"
  ],
  "agettyp" => [
    "  X(Regidx(trunc(xd))) = zero_extend(AD(Ameadregidx(ad)));",
    "  RETIRE_SUCCESS"
  ],
  "asettyp" => [
    "  let dtype : bits(32) = X(Regidx(trunc(xs1)))[31..0];",
    "  if not(ame_datatype_supported(dtype)) then {",
    "    ame_set_unsupported();",
    "    RETIRE_SUCCESS",
    "  } else {",
    "    AD(Ameadregidx(ad)) = dtype;",
    "    ACC(Ameaccregidx(ad)) = zeros();",
    "    RETIRE_SUCCESS",
    "  }"
  ],
  "mgettyp" => [
    "  X(Regidx(trunc(xd))) = zero_extend(MD(Mdregidx(ms1)));",
    "  RETIRE_SUCCESS"
  ],
  "mls.1r" => [
    "  let byte_count = mlen / 8;",
    "  if unsigned(X(Regidx(trunc(xs1)))) % max(1, min(byte_count, 4096)) != 0 then",
    "    return memory_exception(E_Load_Addr_Align(), bits_of(Virtaddr(X(Regidx(trunc(xs1))))), Load(Data));",
    "  ame_load_mreg_raw(Ameregidx(md), Regidx(trunc(xs1)))"
  ],
  "mls.cm" => [
    "  ame_load_mreg_square_memory(Ameregidx(md), Regidx(trunc(xs1)), true)"
  ],
  "mls.rm" => [
    "  ame_load_mreg_square_memory(Ameregidx(md), Regidx(trunc(xs1)), false)"
  ],
  "mls.st" => [
    "  ame_load_mreg_square_strided_memory(Ameregidx(md), Regidx(trunc(xs1)), Regidx(trunc(xs2)), false)"
  ],
  "mls.tst" => [
    "  ame_load_mreg_square_strided_memory(Ameregidx(md), Regidx(trunc(xs1)), Regidx(trunc(xs2)), true)"
  ],
  "mabs.ew" => retire_if_true(
    "ame_ew_unary_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_ABS)"
  ),
  "mbcast.m.x" => [
    "  let md_dtype : bits(32) = MD(Mdregidx(md));",
    "  let ms1_dtype : bits(32) = X(Regidx(trunc(xtyp)))[31..0];",
    "  if not(ame_datatype_supported(md_dtype) & ame_datatype_supported(ms1_dtype)) | md_dtype != ms1_dtype then {",
    "    ame_set_unsupported();",
    "    RETIRE_SUCCESS",
    "  } else ame_retire_if(ame_broadcast_typed_x(md_dtype, ms1_dtype, Ameregidx(md), X(Regidx(trunc(xs1)))))"
  ],
  "mcolunzip.ew" => retire_if_true(
    "ame_pair_permute_ew(MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(ms1), Ameregidx(ms2), AME_PAIR_COL_UNZIP)"
  ),
  "mcolzip.ew" => retire_if_true(
    "ame_pair_permute_ew(MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(ms1), Ameregidx(ms2), AME_PAIR_COL_ZIP)"
  ),
  "mcolgather.ew" => retire_if_true(
    "ame_gather_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), false)"
  ),
  "mcolbcast.ew.x" => retire_if_true(
    "ame_broadcast_axis_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), X(Regidx(trunc(xs1))), false)"
  ),
  "mcolid.ew" => retire_if_true(
    "ame_coordinate_id_ew(MD(Mdregidx(md)), Ameregidx(md), false)"
  ),
  "mcolshift.ew.x" => retire_if_true(
    "ame_shift_axis_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), signed(X(Regidx(trunc(xs1)))[31..0]), false)"
  ),
  "mconv.ew" => retire_if_true(
    "ame_mconv_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1))"
  ),
  "mmove8.m.x" => retire_if_true(
    "ame_debug_mmove_write(Ameregidx(md), X(Regidx(trunc(xs1))), to_bits_unsafe(64, unsigned(X(Regidx(trunc(xs2))))), 8)"
  ),
  "mmove16.m.x" => retire_if_true(
    "ame_debug_mmove_write(Ameregidx(md), X(Regidx(trunc(xs1))), to_bits_unsafe(64, unsigned(X(Regidx(trunc(xs2))))), 16)"
  ),
  "mmove32.m.x" => retire_if_true(
    "ame_debug_mmove_write(Ameregidx(md), X(Regidx(trunc(xs1))), to_bits_unsafe(64, unsigned(X(Regidx(trunc(xs2))))), 32)"
  ),
  "mmove64.m.x" => [
    "  if xlen < 64 then return Illegal_Instruction();",
    *retire_if_true("ame_debug_mmove_write(Ameregidx(md), X(Regidx(trunc(xs1))), to_bits_unsafe(64, unsigned(X(Regidx(trunc(xs2))))), 64)")
  ],
  "mmove8.x.m" => [
    "  match ame_debug_mmove_read(Ameregidx(ms2), X(Regidx(trunc(xs1))), 8) {",
    "    Some(value) => { X(Regidx(trunc(xd))) = zero_extend(value[7..0]); RETIRE_SUCCESS },",
    "    None() => Illegal_Instruction(),",
    "  }"
  ],
  "mmove16.x.m" => [
    "  match ame_debug_mmove_read(Ameregidx(ms2), X(Regidx(trunc(xs1))), 16) {",
    "    Some(value) => { X(Regidx(trunc(xd))) = zero_extend(value[15..0]); RETIRE_SUCCESS },",
    "    None() => Illegal_Instruction(),",
    "  }"
  ],
  "mmove32.x.m" => [
    "  match ame_debug_mmove_read(Ameregidx(ms2), X(Regidx(trunc(xs1))), 32) {",
    "    Some(value) => { X(Regidx(trunc(xd))) = zero_extend(value[31..0]); RETIRE_SUCCESS },",
    "    None() => Illegal_Instruction(),",
    "  }"
  ],
  "mmove64.x.m" => [
    "  if xlen < 64 then return Illegal_Instruction();",
    "  match ame_debug_mmove_read(Ameregidx(ms2), X(Regidx(trunc(xs1))), 64) {",
    "    Some(value) => { X(Regidx(trunc(xd))) = to_bits_unsafe(xlen, unsigned(value)); RETIRE_SUCCESS },",
    "    None() => Illegal_Instruction(),",
    "  }"
  ],
  "mmov.m.a" => [
    "  let md_dtype : bits(32) = MD(Mdregidx(md));",
    "  let ms1_dtype : bits(32) = AD(Ameadregidx(acc));",
    "  let dest_size = ame_dtype_size(md_dtype);",
    "  let src_size = ame_dtype_size(ms1_dtype);",
    "  if not(ame_datatype_supported(md_dtype)) | not(ame_datatype_supported(ms1_dtype)) | md_dtype != ms1_dtype then {",
    "    ame_set_unsupported();",
    "    return RETIRE_SUCCESS",
    "  };",
    "  let dest_nregs = ame_nregs(dest_size);",
    "  let pack_factor = if ame_is_storage_only(md_dtype) then ame_pack_factor(dest_size) else 1;",
    "  if pack_factor > ame_num_acc_regs then {",
    "    ame_set_unsupported();",
    "    return RETIRE_SUCCESS",
    "  };",
    "  if unsigned(acc) + pack_factor > ame_num_acc_regs then return Illegal_Instruction();",
    "  if not(ame_check_mreg_group_operand(md, dest_nregs)) then return Illegal_Instruction();",
    "  var dest_data : bits(acclen) = zeros();",
    "  foreach (sq from 0 to (pack_factor - 1)) {",
    "    let src_data = ACC(ameaccregidx_add(Ameaccregidx(acc), sq));",
    "    foreach (e from 0 to (ame_nelem - 1)) {",
    "      let value = extract_elem_rm(src_data, src_size, e);",
    "      dest_data = insert_elem_rm(dest_data, dest_size, sq * ame_nelem + e, value);",
    "    };",
    "  };",
    "  write_m_square_rm(md_dtype, Ameregidx(md), dest_data);",
    "  RETIRE_SUCCESS"
  ],
  "mmov.a.m" => [
    "  let md_dtype : bits(32) = AD(Ameadregidx(acc));",
    "  let ms1_dtype : bits(32) = MD(Mdregidx(ms));",
    "  let dest_size = ame_dtype_size(md_dtype);",
    "  let src_size = ame_dtype_size(ms1_dtype);",
    "  if not(ame_datatype_supported(md_dtype)) | not(ame_datatype_supported(ms1_dtype)) | md_dtype != ms1_dtype then {",
    "    ame_set_unsupported();",
    "    return RETIRE_SUCCESS",
    "  };",
    "  let src_nregs = ame_nregs(src_size);",
    "  let pack_factor = if ame_is_storage_only(ms1_dtype) then ame_pack_factor(src_size) else 1;",
    "  if pack_factor > ame_num_acc_regs then {",
    "    ame_set_unsupported();",
    "    return RETIRE_SUCCESS",
    "  };",
    "  if unsigned(acc) + pack_factor > ame_num_acc_regs then return Illegal_Instruction();",
    "  if not(ame_check_mreg_group_operand(ms, src_nregs)) then return Illegal_Instruction();",
    "  let src_data = read_m_square_rm(ms1_dtype, Ameregidx(ms));",
    "  foreach (sq from 0 to (pack_factor - 1)) {",
    "    var dest_data : bits(acclen) = zeros();",
    "    foreach (e from 0 to (ame_nelem - 1)) {",
    "      let value = extract_elem_rm(src_data, src_size, sq * ame_nelem + e);",
    "      dest_data = insert_elem_rm(dest_data, dest_size, e, value);",
    "    };",
    "    ACC(ameaccregidx_add(Ameaccregidx(acc), sq)) = dest_data",
    "  };",
    "  RETIRE_SUCCESS"
  ],
  "mmov.m.m" => [
    "  let md_dtype : bits(32) = MD(Mdregidx(md));",
    "  let ms1_dtype : bits(32) = MD(Mdregidx(ms));",
    "  let dest_size = ame_dtype_size(md_dtype);",
    "  let src_size = ame_dtype_size(ms1_dtype);",
    "  if not(ame_datatype_supported(md_dtype)) | not(ame_datatype_supported(ms1_dtype)) | md_dtype != ms1_dtype then {",
    "    ame_set_unsupported();",
    "    return RETIRE_SUCCESS",
    "  };",
    "  let nregs = ame_nregs(dest_size);",
    "  if not(ame_check_mreg_group_operand(md, nregs)) | not(ame_check_mreg_group_operand(ms, nregs)) then",
    "    return Illegal_Instruction();",
    "  let src_data = read_m_square_rm(ms1_dtype, Ameregidx(ms));",
    "  write_m_square_rm(md_dtype, Ameregidx(md), src_data);",
    "  RETIRE_SUCCESS"
  ],
  "mmulacc.2d" => [
    "  let md_dtype : bits(32) = AD(Ameadregidx(acc));",
    "  let ms1_dtype : bits(32) = MD(Mdregidx(ms1));",
    "  let ms2_dtype : bits(32) = MD(Mdregidx(ms2));",
    "  ame_retire_if(ame_mmulacc_2d(md_dtype, ms1_dtype, ms2_dtype, Ameaccregidx(acc), Ameregidx(ms1), Ameregidx(ms2)))"
  ],
  "mmulaccneg.2d" => retire_mmul_accum_2d(
    subtract_product: true,
    transpose_a: false,
    transpose_b: false
  ),
  "mmulatacc.2d" => retire_mmul_accum_2d(
    subtract_product: false,
    transpose_a: true,
    transpose_b: false
  ),
  "mmulataccneg.2d" => retire_mmul_accum_2d(
    subtract_product: true,
    transpose_a: true,
    transpose_b: false
  ),
  "mmulbtacc.2d" => retire_mmul_accum_2d(
    subtract_product: false,
    transpose_a: false,
    transpose_b: true
  ),
  "mmulbtaccneg.2d" => retire_mmul_accum_2d(
    subtract_product: true,
    transpose_a: false,
    transpose_b: true
  ),
  "mpack.ew.x" => [
    "  let md_dtype : bits(32) = MD(Mdregidx(md));",
    "  let ms1_dtype : bits(32) = MD(Mdregidx(ms1));",
    "  let dest_size = ame_dtype_size(md_dtype);",
    "  let src_size = ame_dtype_size(ms1_dtype);",
    "  if not(ame_datatype_supported(md_dtype) & ame_datatype_supported(ms1_dtype)) then {",
    "    ame_set_unsupported();",
    "    RETIRE_SUCCESS",
    "  } else if not(ame_is_integer(md_dtype) & ame_is_integer(ms1_dtype)) | not(ame_is_storage_only(md_dtype)) | ame_is_storage_only(ms1_dtype) | src_size != ame_unit_dtype_size | dest_size * 2 != ame_unit_dtype_size | ame_pack_factor(dest_size) != 2 then {",
    "    ame_set_unsupported();",
    "    RETIRE_SUCCESS",
    "  } else ame_retire_if(ame_pack_square_ew(md_dtype, ms1_dtype, Ameregidx(md), Ameregidx(ms1), X(Regidx(trunc(xs1)))))"
  ],
  "mprefixadd.col" => retire_if_true(
    "ame_prefix_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_ADD, false)"
  ),
  "mprefixadd.row" => retire_if_true(
    "ame_prefix_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_ADD, true)"
  ),
  "mprefixmax.col" => retire_if_true(
    "ame_prefix_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_MAX, false)"
  ),
  "mprefixmax.row" => retire_if_true(
    "ame_prefix_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_MAX, true)"
  ),
  "mreduceadd.col" => retire_if_true(
    "ame_reduce_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_ADD, false)"
  ),
  "mreduceadd.row" => retire_if_true(
    "ame_reduce_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_ADD, true)"
  ),
  "mreducemax.col" => retire_if_true(
    "ame_reduce_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_MAX, false)"
  ),
  "mreducemax.row" => retire_if_true(
    "ame_reduce_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_MAX, true)"
  ),
  "mreducemin.col" => retire_if_true(
    "ame_reduce_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_MIN, false)"
  ),
  "mreducemin.row" => retire_if_true(
    "ame_reduce_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), AME_INT_REDUCE_MIN, true)"
  ),
  "mrowunzip.ew" => retire_if_true(
    "ame_pair_permute_ew(MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(ms1), Ameregidx(ms2), AME_PAIR_ROW_UNZIP)"
  ),
  "mrowzip.ew" => retire_if_true(
    "ame_pair_permute_ew(MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(ms1), Ameregidx(ms2), AME_PAIR_ROW_ZIP)"
  ),
  "mrowbcast.ew.x" => retire_if_true(
    "ame_broadcast_axis_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), X(Regidx(trunc(xs1))), true)"
  ),
  "mrowgather.ew" => retire_if_true(
    "ame_gather_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), true)"
  ),
  "mrowid.ew" => retire_if_true(
    "ame_coordinate_id_ew(MD(Mdregidx(md)), Ameregidx(md), true)"
  ),
  "mrowshift.ew.x" => retire_if_true(
    "ame_shift_axis_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), signed(X(Regidx(trunc(xs1)))[31..0]), true)"
  ),
  "msll.ew" => retire_if_true(
    "ame_ew_shift_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), AME_INT_SHIFT_LEFT)"
  ),
  "msll.ew.x" => retire_if_true(
    "ame_ew_shift_x(MD(Mdregidx(md)), MD(Mdregidx(ms2)), Ameregidx(md), X(Regidx(trunc(xs1))), Ameregidx(ms2), AME_INT_SHIFT_LEFT)"
  ),
  "msra.ew" => retire_if_true(
    "ame_ew_shift_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), AME_INT_SHIFT_RIGHT_ARITH)"
  ),
  "msra.ew.x" => retire_if_true(
    "ame_ew_shift_x(MD(Mdregidx(md)), MD(Mdregidx(ms2)), Ameregidx(md), X(Regidx(trunc(xs1))), Ameregidx(ms2), AME_INT_SHIFT_RIGHT_ARITH)"
  ),
  "msrl.ew" => retire_if_true(
    "ame_ew_shift_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), AME_INT_SHIFT_RIGHT_LOGICAL)"
  ),
  "msrl.ew.x" => retire_if_true(
    "ame_ew_shift_x(MD(Mdregidx(md)), MD(Mdregidx(ms2)), Ameregidx(md), X(Regidx(trunc(xs1))), Ameregidx(ms2), AME_INT_SHIFT_RIGHT_LOGICAL)"
  ),
  "munpack.ew.x" => [
    "  let md_dtype : bits(32) = MD(Mdregidx(md));",
    "  let ms1_dtype : bits(32) = MD(Mdregidx(ms1));",
    "  let dest_size = ame_dtype_size(md_dtype);",
    "  let src_size = ame_dtype_size(ms1_dtype);",
    "  if not(ame_datatype_supported(md_dtype) & ame_datatype_supported(ms1_dtype)) then {",
    "    ame_set_unsupported();",
    "    RETIRE_SUCCESS",
    "  } else if not(ame_is_integer(md_dtype) & ame_is_integer(ms1_dtype)) | ame_is_storage_only(md_dtype) | not(ame_is_storage_only(ms1_dtype)) | dest_size != ame_unit_dtype_size | src_size * 2 != ame_unit_dtype_size | ame_pack_factor(src_size) != 2 then {",
    "    ame_set_unsupported();",
    "    RETIRE_SUCCESS",
    "  } else ame_retire_if(ame_unpack_square_ew(md_dtype, ms1_dtype, Ameregidx(md), Ameregidx(ms1), X(Regidx(trunc(xs1)))))"
  ],
  "mrowscatadd.ew" => retire_if_true(
    "ame_scatter_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), AME_INT_SCATTER_ADD, true)"
  ),
  "mcolscatadd.ew" => retire_if_true(
    "ame_scatter_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), AME_INT_SCATTER_ADD, false)"
  ),
  "mrowscatmax.ew" => retire_if_true(
    "ame_scatter_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), AME_INT_SCATTER_MAX, true)"
  ),
  "mcolscatmax.ew" => retire_if_true(
    "ame_scatter_ew(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), AME_INT_SCATTER_MAX, false)"
  ),
  "msettyp" => [
    "  let dtype : bits(32) = X(Regidx(trunc(xs1)))[31..0];",
    "  if not(ame_datatype_supported(dtype)) then {",
    "    ame_set_unsupported();",
    "    return RETIRE_SUCCESS",
    "  };",
    "  let size = ame_dtype_size(dtype);",
    "  let nregs = ame_nregs(size);",
    "  if not(ame_check_mreg_group_operand(md, nregs)) then return Illegal_Instruction();",
    "  MD(Mdregidx(md)) = dtype;",
    "  let max_regs = acclen / mlen;",
    "  foreach (r from 0 to (max_regs - 1)) {",
    "    if r < nregs then M(ameregidx_add(Ameregidx(md), r)) = zeros()",
    "  };",
    "  RETIRE_SUCCESS"
  ],
  "mss.1r" => [
    "  let byte_count = mlen / 8;",
    "  if unsigned(X(Regidx(trunc(xs1)))) % max(1, min(byte_count, 4096)) != 0 then",
    "    return memory_exception(E_SAMO_Addr_Align(), bits_of(Virtaddr(X(Regidx(trunc(xs1))))), Store(Data));",
    "  ame_store_mreg_raw(Ameregidx(ms1), Regidx(trunc(xs1)))"
  ],
  "mss.cm" => [
    "  ame_store_mreg_square_memory(Ameregidx(ms1), Regidx(trunc(xs1)), true)"
  ],
  "mss.rm" => [
    "  ame_store_mreg_square_memory(Ameregidx(ms1), Regidx(trunc(xs1)), false)"
  ],
  "mss.st" => [
    "  ame_store_mreg_square_strided_memory(Ameregidx(ms1), Regidx(trunc(xs1)), Regidx(trunc(xs2)), false)"
  ],
  "mss.tst" => [
    "  ame_store_mreg_square_strided_memory(Ameregidx(ms1), Regidx(trunc(xs1)), Regidx(trunc(xs2)), true)"
  ],
  "mzero.2d.acc" => [
    "  let dtype : bits(32) = AD(Ameadregidx(acc));",
    "  if not(ame_datatype_supported(dtype)) then {",
    "    ame_set_unsupported();",
    "    RETIRE_SUCCESS",
    "  } else {",
    "    ACC(Ameaccregidx(acc)) = zeros();",
    "    RETIRE_SUCCESS",
    "  }"
  ],
  "mzero.2d.m" => [
    "  let dtype : bits(32) = MD(Mdregidx(md));",
    "  if not(ame_datatype_supported(dtype)) then {",
    "    ame_set_unsupported();",
    "    return RETIRE_SUCCESS",
    "  };",
    "  let nregs = ame_nregs(ame_dtype_size(dtype));",
    "  if not(ame_check_mreg_group_operand(md, nregs)) then return Illegal_Instruction();",
    "  let max_regs = acclen / mlen;",
    "  foreach (r from 0 to (max_regs - 1)) {",
    "    if r < nregs then M(ameregidx_add(Ameregidx(md), r)) = zeros()",
    "  };",
    "  RETIRE_SUCCESS"
  ]
}.freeze

INT_EW_BINARY_M_OPS = {
  "madd.ew" => "AME_INT_ADD",
  "msub.ew" => "AME_INT_SUB_RHS_LHS",
  "mand.ew" => "AME_INT_AND",
  "mandnot.ew" => "AME_INT_ANDNOT",
  "mor.ew" => "AME_INT_OR",
  "mornot.ew" => "AME_INT_ORNOT",
  "mxor.ew" => "AME_INT_XOR",
  "mmax.ew" => "AME_INT_MAX",
  "mmin.ew" => "AME_INT_MIN",
  "mabsdiff.ew" => "AME_INT_ABSDIFF",
  "mhdiff.ew" => "AME_INT_HDIFF_RHS_LHS",
  "mmean.ew" => "AME_INT_MEAN",
  "mmul.ew" => "AME_INT_MUL",
  "mmulneg.ew" => "AME_INT_MULNEG",
  "mcmpge.ew" => "AME_INT_CMPGE",
  "mcmplt.ew" => "AME_INT_CMPLT"
}.freeze

INT_EW_BINARY_X_OPS = {
  "madd.ew.x" => "AME_INT_ADD",
  "msub.ew.x" => "AME_INT_SUB_RHS_LHS",   # manual: D[i] = B[i] - c
  "mand.ew.x" => "AME_INT_AND",
  "mandnot.ew.x" => "AME_INT_ANDNOT",
  "mor.ew.x" => "AME_INT_OR",
  "mornot.ew.x" => "AME_INT_ORNOT",
  "mxor.ew.x" => "AME_INT_XOR",
  "mmax.ew.x" => "AME_INT_MAX",
  "mmin.ew.x" => "AME_INT_MIN",
  "mabsdiff.ew.x" => "AME_INT_ABSDIFF",
  "mhdiff.ew.x" => "AME_INT_HDIFF_RHS_LHS",  # manual: D[i] = (B[i] - c) / 2
  "mmean.ew.x" => "AME_INT_MEAN",
  "mmul.ew.x" => "AME_INT_MUL",
  "mmulneg.ew.x" => "AME_INT_MULNEG",
  "mcmpge.ew.x" => "AME_INT_CMPGE",
  "mcmplt.ew.x" => "AME_INT_CMPLT"
}.freeze

INT_EW_TERNARY_M_OPS = {
  "mmulacc.ew" => "AME_INT_MULACC",
  "mmulaccneg.ew" => "AME_INT_MULNACC",
  "mmuladd.ew" => "AME_INT_MULADD",
  "mmulsub.ew" => "AME_INT_MULSUB"
}.freeze

PREDICATE_BINARY_M_OPS = {
  "mselge.ew" => [false, false],
  "msellt.ew" => [true, false]
}.freeze

PREDICATE_TERNARY_M_OPS = {
  "mcmovge.ew" => [false, true],
  "mcmovlt.ew" => [true, true]
}.freeze

INT_EW_TERNARY_X_OPS = {
  "mmulacc.ew.x" => "AME_INT_MULACC",
  "mmulaccneg.ew.x" => "AME_INT_MULNACC",
  "mmuladd.ew.x" => "AME_INT_MULADD",
  "mmulsub.ew.x" => "AME_INT_MULSUB"
}.freeze

INT_LOGEXP_UNARY_M_OPS = {
  "mexp2.ew" => "AME_INT_EXP2",
  "mlog2.ew" => "AME_INT_LOG2"
}.freeze

INT_LOGEXP_BINARY_M_OPS = {
  "mldexp.ew" => "AME_INT_LDEXP",
  "mldexpacc.ew" => "AME_INT_LDEXPACC",
  "mrdexp.ew" => "AME_INT_RDEXP",
  "mrdexpacc.ew" => "AME_INT_RDEXPACC",
  "mlog2sub.ew" => "AME_INT_LOG2SUB",
  "msublog2.ew" => "AME_INT_SUBLOG2"
}.freeze

INT_LOGEXP_BINARY_X_OPS = {
  "mldexp.ew.x" => "AME_INT_LDEXP",
  "mldexpacc.ew.x" => "AME_INT_LDEXPACC",
  "mlog2sub.ew.x" => "AME_INT_LOG2SUB",
  "msublog2.ew.x" => "AME_INT_SUBLOG2"
}.freeze

FLOAT_MATH_UNARY_M_OPS = {
  "mfrintm.ew" => "AME_FLOAT_ROUND_DOWN",
  "mfrintn.ew" => "AME_FLOAT_ROUND_NEAREST",
  "mfrintp.ew" => "AME_FLOAT_ROUND_UP",
  "mfrintz.ew" => "AME_FLOAT_ROUND_ZERO",
  "mrec.ew" => "AME_FLOAT_RECIPROCAL",
  "mrsqrt.ew" => "AME_FLOAT_RSQRT",
  "msqrt.ew" => "AME_FLOAT_SQRT",
  "mcos.ew" => "AME_FLOAT_COS",
  "msin.ew" => "AME_FLOAT_SIN",
  "mtanh.ew" => "AME_FLOAT_TANH"
}.freeze

BACKEND_MANAGEMENT_INSTRUCTIONS = %w[
  ame.acquire
  ame.release
].freeze

EXECUTE_BODIES = BASE_EXECUTE_BODIES
  .merge(INT_EW_BINARY_M_OPS.transform_values do |op|
    retire_if_true(
      "ame_ew_binary_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), #{op})"
    )
  end)
  .merge(INT_EW_BINARY_X_OPS.transform_values do |op|
    retire_if_true(
      "ame_ew_binary_x(MD(Mdregidx(md)), MD(Mdregidx(ms2)), Ameregidx(md), X(Regidx(trunc(xs1))), Ameregidx(ms2), #{op})"
    )
  end)
  .merge(INT_EW_TERNARY_M_OPS.transform_values do |op|
    retire_if_true(
      "ame_ew_ternary_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), #{op})"
    )
  end)
  .merge(PREDICATE_BINARY_M_OPS.transform_values do |select_when_negative, preserve_dest_when_false|
    retire_if_true(
      "ame_ew_predicate_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), #{select_when_negative}, #{preserve_dest_when_false})"
    )
  end)
  .merge(PREDICATE_TERNARY_M_OPS.transform_values do |select_when_negative, preserve_dest_when_false|
    retire_if_true(
      "ame_ew_predicate_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), #{select_when_negative}, #{preserve_dest_when_false})"
    )
  end)
  .merge(INT_EW_TERNARY_X_OPS.transform_values do |op|
    retire_if_true(
      "ame_ew_ternary_x(MD(Mdregidx(md)), MD(Mdregidx(ms2)), Ameregidx(md), X(Regidx(trunc(xs1))), Ameregidx(ms2), #{op})"
    )
  end)
  .merge(INT_LOGEXP_UNARY_M_OPS.transform_values do |op|
    retire_if_true(
      "ame_logexp_unary_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), #{op})"
    )
  end)
  .merge(INT_LOGEXP_BINARY_M_OPS.transform_values do |op|
    retire_if_true(
      "ame_logexp_binary_m(MD(Mdregidx(md)), MD(Mdregidx(ms1)), MD(Mdregidx(ms2)), Ameregidx(md), Ameregidx(ms1), Ameregidx(ms2), #{op})"
    )
  end)
  .merge(INT_LOGEXP_BINARY_X_OPS.transform_values do |op|
    retire_if_true(
      "ame_logexp_binary_x(MD(Mdregidx(md)), MD(Mdregidx(ms2)), Ameregidx(md), X(Regidx(trunc(xs1))), Ameregidx(ms2), #{op})"
    )
  end)
  .merge(FLOAT_MATH_UNARY_M_OPS.transform_values do |op|
    retire_if_true(
      "ame_ew_float_math(MD(Mdregidx(md)), MD(Mdregidx(ms1)), Ameregidx(md), Ameregidx(ms1), #{op})"
    )
  end)
  .freeze

Variable = ManualInstructionData::Variable

def assembly_operands(assembly)
  assembly.to_s.split(",").map { |operand| operand.strip.delete("()") }.reject(&:empty?)
end

def validate_assembly!(inst)
  operands = assembly_operands(inst[:assembly])
  variable_names = inst[:variables].map(&:name)
  missing = operands - variable_names
  raise "#{inst[:name]}: assembly operands missing from encoding variables: #{missing.join(', ')}" unless missing.empty?

  if operands.empty? && !inst[:variables].empty?
    raise "#{inst[:name]}: instruction has encoding variables but no assembly operands"
  end
end

# The v0.6 prose uses the standard RISC-V rd/rs1/rs2 names.  The hand-written
# helper templates use short role names (xd/xs1/xs2, etc.); these are rewritten
# at generation time so the emitted execute clauses contain only their actual
# constructor parameters.
def semantic_aliases(inst)
  aliases = { "rd" => "xd", "rs1" => "xs1", "rs2" => "xs2" }
  aliases["rs1"] = "xs" if inst[:name] == "ame.acquire"
  if %w[mcolbcast.ew.x mcolshift.ew.x mrowbcast.ew.x mrowshift.ew.x
        mpack.ew.x munpack.ew.x].include?(inst[:name])
    aliases["ms2"] = "ms1"
  end
  aliases["rs2"] = "xtyp" if inst[:name] == "mbcast.m.x"
  aliases
end

def load_instructions
  ManualInstructionData.load
end

def ordered_variables(inst)
  by_name = inst[:variables].to_h { |var| [var.name, var] }
  seen = {}
  ordered = assembly_operands(inst[:assembly]).filter_map do |operand|
    var = by_name[operand]
    seen[operand] = true if var
    var
  end
  ordered + inst[:variables].reject { |var| seen[var.name] }
end

def constructor_name(name)
  "AME_#{name.gsub(/[^0-9A-Za-z]+/, "_").gsub(/\A_+|_+\z/, "").upcase}"
end

def constructor_call(inst)
  args = ordered_variables(inst).map(&:name).join(", ")
  "#{constructor_name(inst[:name])}(#{args})"
end

def encdec_segments(inst)
  variables_by_msb = inst[:variables].to_h { |var| [var.msb, var] }
  segments = []
  bit = 31

  while bit >= 0
    if (var = variables_by_msb[bit])
      segments << "#{var.name} : bits(#{var.width})"
      bit = var.lsb - 1
      next
    end

    bits = +""
    while bit >= 0 && !variables_by_msb.key?(bit)
      char = inst[:match][31 - bit]
      raise "#{inst[:name]}: wildcard bit #{bit} is not covered by variables" if char == "-"

      bits << char
      bit -= 1
    end
    segments << "0b#{bits}"
  end

  segments
end

def assembly_operand_expr(inst, operand)
  var = inst[:variables].find { |candidate| candidate.name == operand }
  raise "#{inst[:name]}: assembly operand #{operand} is not an encoding variable" unless var

  case operand
  when "xd", "xs", "xs1", "xs2", "xtyp", "rd", "rs1", "rs2"
    "reg_name(encdec_reg(#{operand}))"
  when "fs1"
    "freg_name(encdec_freg(#{operand}))"
  when "md", "ms", "ms1", "ms2"
    "amereg_name_raw(#{operand})"
  when "acc", "ad"
    "ameaccreg_name_raw(#{operand})"
  when "sw", "sr", "pw", "pr"
    "hex_bits_signed_#{var.width}(#{operand})"
  else
    raise "#{inst[:name]}: unsupported assembly operand #{operand}"
  end
end

def assembly_rhs(inst)
  operands = assembly_operands(inst[:assembly])
  return %("#{inst[:name]}") if operands.empty?

  operand_text = operands.map { |operand| assembly_operand_expr(inst, operand) }
  %("#{inst[:name]}" ^ spc() ^ #{operand_text.join(" ^ sep() ^ ")})
end

M_REGISTER_OPERANDS = %w[md ms ms1 ms2].freeze
ACC_REGISTER_OPERANDS = %w[acc ad].freeze
CONTEXT_ENABLED_INSTRUCTIONS = %w[ame.acquire ame.release].freeze
DISTINCT_M_REGISTER_PAIRS = {
  "mcolunzip.ew" => %w[ms1 ms2],
  "mcolzip.ew" => %w[ms1 ms2],
  "mrowunzip.ew" => %w[ms1 ms2],
  "mrowzip.ew" => %w[ms1 ms2]
}.freeze

# Architectural operand validation must happen before any descriptor or data
# state is read.  Keep it in the emitter so a regenerated execute file cannot
# accidentally restore the old, helper-dependent validation order.
def first_stage_index_checks(inst)
  names = inst[:variables].map(&:name)
  checks = names.grep(/\A(?:#{M_REGISTER_OPERANDS.join('|')})\z/).map do |name|
    "  if not(ame_check_mreg_operand(#{name})) then return Illegal_Instruction();"
  end
  checks.concat(names.grep(/\A(?:#{ACC_REGISTER_OPERANDS.join('|')})\z/).map do |name|
    "  if not(ame_check_acc_reg_operand(#{name})) then return Illegal_Instruction();"
  end)

  if (pair = DISTINCT_M_REGISTER_PAIRS[inst[:name]])
    checks << "  if #{pair[0]} == #{pair[1]} then return Illegal_Instruction();"
  end
  checks
end

def instruction_family(inst)
  layout = case inst.fetch(:format)
  when "R1"
    :r1
  when "R2"
    FLOAT_ONLY_INSTRUCTIONS.include?(inst.fetch(:name)) ? :fp_r2 : :r2
  when "R3"
    if inst.fetch(:variables).length == 2
      :r3_pair
    elsif FLOAT_ONLY_INSTRUCTIONS.include?(inst.fetch(:name))
      :fp_r3
    else
      :r3
    end
  when "Fixed"
    :fixed
  else
    raise "#{inst.fetch(:name)}: unsupported instruction format #{inst.fetch(:format)}"
  end
  return :fixed if layout == :fixed

  family_key(inst, layout, operand_signature(inst))
end

def family_definition(family)
  category, layout_name, signature = family_parts(family)
  layout = FAMILY_LAYOUTS.fetch(layout_name)
  return layout if layout_name == :fixed

  prefix = category.to_s.upcase
  {
    constructor: "#{prefix}_#{layout.fetch(:constructor)}_#{signature.map(&:upcase).join('_')}_TYPE",
    type: "#{category}_#{layout.fetch(:type)}_#{signature.join('_')}",
    width: layout.fetch(:width),
    arguments: layout.fetch(:arguments)
  }
end

def instruction_enum_name(inst)
  constructor_name(inst.fetch(:name))
end

def family_bindings(inst, family)
  definition = family_definition(family)
  variables = ordered_variables(inst)
  arguments = definition.fetch(:arguments)
  unless variables.length == arguments.length
    raise "#{inst.fetch(:name)}: #{family} expects #{arguments.length} encoding variables, got #{variables.length}"
  end

  variables.zip(arguments).to_h { |variable, argument| [variable.name, argument] }
end

def family_op_bits(inst, family)
  width = family_definition(family).fetch(:width)
  pattern = inst.fetch(:match).slice(0, width)
  raise "#{inst.fetch(:name)}: variable bits in #{family} funct field" if pattern.include?("-")

  format("0b%0#{width}b", pattern.to_i(2))
end

def substitute_variables(text, bindings)
  return text if bindings.empty?

  pattern = bindings.keys.sort_by { |name| -name.length }.map { |name| Regexp.escape(name) }.join("|")
  text.gsub(/\b(?:#{pattern})\b/) { |name| bindings.fetch(name) }
end

def semantic_bindings(inst, family_bindings = {})
  variables = inst.fetch(:variables).map(&:name)
  semantic_aliases(inst).each_with_object(family_bindings.dup) do |(source, target), bindings|
    next unless variables.include?(source)

    bindings[target] = family_bindings.fetch(source, source)
  end
end

def family_assembly_rhs(inst, family, op_expression = "op")
  bindings = family_bindings(inst, family)
  operands = assembly_operands(inst.fetch(:assembly))
  mnemonic = op_expression ?
             "#{family_definition(family).fetch(:type)}_mnemonic(#{op_expression})" :
             %("#{inst.fetch(:name)}")
  return mnemonic if operands.empty?

  operand_text = operands.map do |operand|
    expression = case operand
                 when "xd", "xs", "xs1", "xs2", "xtyp", "rd", "rs1", "rs2"
                   "reg_name(encdec_reg(#{bindings.fetch(operand)}))"
                 when "fs1"
                   "freg_name(encdec_freg(#{bindings.fetch(operand)}))"
                 when "md", "ms", "ms1", "ms2"
                   "amereg_name_raw(#{bindings.fetch(operand)})"
                 when "acc", "ad"
                   "ameaccreg_name_raw(#{bindings.fetch(operand)})"
                 when "sw", "sr", "pw", "pr"
                   width = inst.fetch(:variables).find { |var| var.name == operand }.width
                   "hex_bits_signed_#{width}(#{bindings.fetch(operand)})"
                 else
                   raise "#{inst.fetch(:name)}: unsupported assembly operand #{operand}"
                 end
    expression
  end
  "#{mnemonic} ^ spc() ^ #{operand_text.join(' ^ sep() ^ ')}"
end

def emit_single_instruction(inst, include_execute:)
  family = instruction_family(inst)
  definition = family_definition(family)
  constructor = instruction_enum_name(inst)
  arguments = definition.fetch(:arguments)
  argument_types = arguments.map { "bits(5)" }
  argument_text = arguments.join(", ")
  encoding = family_encdec_rhs(family).sub(
    "encdec_#{definition.fetch(:type)}(op)", family_op_bits(inst, family)
  )
  lines = [
    "// *****************************************************************",
    "// #{inst.fetch(:name)}",
    "union clause instruction = #{constructor} : (#{argument_types.join(', ')})",
    "",
    "mapping clause encdec = #{constructor}(#{argument_text})",
    "  <-> #{encoding}",
    "  when currentlyEnabled(Ext_Ztt)",
    "",
    "mapping clause assembly = #{constructor}(#{argument_text})",
    "  <-> #{family_assembly_rhs(inst, family, nil)}",
    ""
  ]
  return lines unless include_execute

  lines << "function clause execute #{constructor}(#{argument_text}) = {"
  lines.concat(family_common_checks(family, [inst]))
  lines.concat(family_case_body(inst, family))
  lines << "}"
  lines << ""
  lines
end

def family_encdec_rhs(family)
  definition = family_definition(family)
  arguments = definition.fetch(:arguments)
  case family_parts(family).fetch(1)
  when :r1
    "encdec_#{definition.fetch(:type)}(op) @ 0b000 @ #{arguments.fetch(0)} : bits(5) @ 0b0101011"
  when :r2, :fp_r2
    "encdec_#{definition.fetch(:type)}(op) @ #{arguments.fetch(1)} : bits(5) @ 0b000 @ #{arguments.fetch(0)} : bits(5) @ 0b0101011"
  when :r3_pair
    # Pair operations retain the R-type operand order: funct7 | rs2 | rs1 |
    # funct3 | rd | opcode.  Their two AME registers occupy rs2 and rs1.
    "encdec_#{definition.fetch(:type)}(op) @ #{arguments.fetch(1)} : bits(5) @ #{arguments.fetch(0)} : bits(5) @ 0b000 @ 0b00000 @ 0b0101011"
  when :r3, :fp_r3
    # R-type encodings use funct7 | rs2 | rs1 | funct3 | rd | opcode.
    "encdec_#{definition.fetch(:type)}(op) @ #{arguments.fetch(2)} : bits(5) @ #{arguments.fetch(1)} : bits(5) @ 0b000 @ #{arguments.fetch(0)} : bits(5) @ 0b0101011"
  else
    raise "#{family}: no grouped encdec layout"
  end
end

def family_constructor_call(family)
  definition = family_definition(family)
  "#{definition.fetch(:constructor)}(op, #{definition.fetch(:arguments).join(', ')})"
end

def indent_family_lines(lines)
  lines.map { |line| "    #{line}" }
end

def family_case_body(inst, family)
  bindings = family_bindings(inst, family)
  lines = if IMPLEMENTED_INSTRUCTIONS.include?(inst.fetch(:name)) && EXECUTE_BODIES.key?(inst.fetch(:name))
            EXECUTE_BODIES.fetch(inst.fetch(:name))
          else
            ["  internal_error(__FILE__, __LINE__, \"Ztt execute implementation missing: #{inst.fetch(:name)}\")"]
          end
  lines.map { |line| substitute_variables(line, semantic_bindings(inst, bindings)) }
end

def family_common_checks(family, entries)
  category, layout_name, signature = family_parts(family)
  definition = family_definition(family)
  checks = []
  names = entries.map { |inst| inst.fetch(:name) }

  unless names.all? { |name| BACKEND_MANAGEMENT_INSTRUCTIONS.include?(name) }
    checks << "  if not(ame_context_owned()) then return Illegal_Instruction();"
  end
  if names.any? { |name| CONTEXT_ENABLED_INSTRUCTIONS.include?(name) }
    checks << "  if not(ame_context_enabled()) then return Illegal_Instruction();"
  end

  definition.fetch(:arguments).zip(signature).each do |argument, role|
    if role == "md" || role == "ms"
      checks << "  if not(ame_check_mreg_operand(#{argument})) then return Illegal_Instruction();"
    elsif %w[ad as].include?(role)
      checks << "  if not(ame_check_acc_reg_operand(#{argument})) then return Illegal_Instruction();"
    end
  end

  if layout_name == :r3_pair && entries.all? { |inst| DISTINCT_M_REGISTER_PAIRS.key?(inst.fetch(:name)) }
    checks << "  if ms1 == ms2 then return Illegal_Instruction();"
  end
  checks
end

def emit_family(family, entries, include_execute:)
  definition = family_definition(family)
  type = definition.fetch(:type)
  lines = []
  lines << "// *****************************************************************"
  lines << "// #{family_comment(family)}"
  lines << "mapping encdec_#{type} : #{type} <-> bits(#{definition.fetch(:width)}) = {"
  entries.each_with_index do |inst, index|
    comma = index == entries.length - 1 ? "" : ","
    lines << "  #{instruction_enum_name(inst)} <-> #{family_op_bits(inst, family)}#{comma}"
  end
  lines << "}"
  lines << ""
  lines << "mapping #{type}_mnemonic : #{type} <-> string = {"
  entries.each_with_index do |inst, index|
    comma = index == entries.length - 1 ? "" : ","
    lines << "  #{instruction_enum_name(inst)} <-> \"#{inst.fetch(:name)}\"#{comma}"
  end
  lines << "}"
  lines << ""
  arguments = definition.fetch(:arguments).map { |_argument| "bits(5)" }
  lines << "mapping #{type}_assembly : (#{type}, #{arguments.join(', ')}) <-> string = {"
  entries.each do |inst|
    enum_name = instruction_enum_name(inst)
    lines << "  (#{enum_name}, #{definition.fetch(:arguments).join(', ')}) <-> #{family_assembly_rhs(inst, family, enum_name)},"
  end
  lines << "}"
  lines << ""
  payload = [definition.fetch(:type), *definition.fetch(:arguments).map { "bits(5)" }].join(', ')
  lines << "union clause instruction = #{definition.fetch(:constructor)} : (#{payload})"
  lines << ""
  lines << "mapping clause encdec = #{family_constructor_call(family)}"
  lines << "  <-> #{family_encdec_rhs(family)}"
  lines << "  when currentlyEnabled(Ext_Ztt)"
  lines << ""
  lines << "mapping clause assembly = #{family_constructor_call(family)}"
  lines << "  <-> #{type}_assembly(op, #{definition.fetch(:arguments).join(', ')})"
  lines << ""
  return lines unless include_execute

  lines << "function clause execute #{family_constructor_call(family)} = {"
  lines.concat(family_common_checks(family, entries))
  lines << "  match op {"
  entries.each do |inst|
    body = family_case_body(inst, family)
    if body.length == 1
      lines << "    #{instruction_enum_name(inst)} => #{body.first.strip},"
    else
      lines << "    #{instruction_enum_name(inst)} => {"
      lines.concat(indent_family_lines(body))
      lines << "    },"
    end
  end
  lines << "  }"
  lines << "}"
  lines << ""
  lines
end

def emit_fixed_instruction(inst, include_execute:)
  validate_assembly!(inst)
  constructor = constructor_name(inst.fetch(:name))
  payload = inst.fetch(:variables).empty? ? " : unit" : " : (#{ordered_variables(inst).map { |var| "bits(#{var.width})" }.join(', ')})"
  lines = [
    "// *****************************************************************",
    "// #{inst.fetch(:name)}",
    "union clause instruction = #{constructor}#{payload}",
    "",
    "mapping clause encdec = #{constructor_call(inst)}",
    "  <-> #{encdec_segments(inst).join(' @ ')}",
    "  when currentlyEnabled(Ext_Ztt)",
    "",
    "mapping clause assembly = #{constructor_call(inst)}",
    "  <-> #{assembly_rhs(inst)}",
    ""
  ]
  return lines unless include_execute

  lines << "function clause execute #{constructor_call(inst)} = {"
  lines << "  if not(ame_context_enabled()) then return Illegal_Instruction();" if CONTEXT_ENABLED_INSTRUCTIONS.include?(inst.fetch(:name))
  lines.concat(first_stage_index_checks(inst))
  lines.concat(EXECUTE_BODIES.fetch(inst.fetch(:name)).map do |line|
    substitute_variables(line, semantic_bindings(inst))
  end)
  lines << "}"
  lines << ""
  lines
end

stdout = false
include_execute = true
output_file = nil
output_dir = DEFAULT_OUT_DIR
OptionParser.new do |opts|
  opts.banner = "Usage: ruby generators/gen_ztt_sail.rb [--output-dir DIR] [--output FILE] [--stdout] [--no-execute]"
  opts.on("--output FILE", "Write one combined file") do |path|
    output_file = Pathname.new(path).expand_path
  end
  opts.on("--output-dir DIR", "Write the generated Sail files to DIR (default: model/extensions/Ztt)") do |path|
    output_dir = Pathname.new(path).expand_path
  end
  opts.on("--stdout", "Write the combined output to stdout") { stdout = true }
  opts.on("--no-execute", "Omit execute clauses and their implementation helpers") { include_execute = false }
end.parse!

def generated_header(description)
  [
    "// This file is generated by generators/gen_ztt_sail.rb.",
    "// Source: manual-main/instructions.json",
    "// #{description}",
    ""
  ]
end

def render(lines)
  lines.join("\n").rstrip + "\n"
end

# Replace generated artifacts atomically so an interrupted generation cannot
# leave a tracked Sail file truncated or syntactically incomplete.
def write_atomically(path, text)
  path = Pathname.new(path)
  FileUtils.mkdir_p(path.dirname)
  Tempfile.create([".#{path.basename}.", ".tmp"], path.dirname.to_s) do |temporary|
    temporary.write(text)
    temporary.flush
    temporary.fsync
    File.rename(temporary.path, path.to_s)
  end
end

instructions = load_instructions
category_order = instructions.map { |inst| instruction_category(inst) }.uniq
family_entries = instructions.reject { |inst| instruction_family(inst) == :fixed }
  .group_by { |inst| instruction_family(inst) }
family_order = instructions.map { |inst| instruction_family(inst) }
  .select { |family| family != :fixed && family_entries.fetch(family).length > 1 }
  .uniq
common_lines = generated_header(
  include_execute ? "Execute helpers are generated from the manual instruction snapshot." :
                    "Execute clauses are omitted by --no-execute."
)
common_lines.concat((include_execute ? ZTT_PRELUDE : ZTT_ENCDEC_PRELUDE).lines(chomp: true))
common_text = render(common_lines)

type_lines = generated_header("Instruction family selectors generated from the manual instruction snapshot.")
family_order.each do |family|
  entries = family_entries.fetch(family)
  next if entries.empty?

  definition = family_definition(family)
  type_lines << "// #{family_comment(family)} selector"
  type_lines << "enum #{definition.fetch(:type)} = {"
  entries.each_with_index do |inst, index|
    comma = index == entries.length - 1 ? "" : ","
    type_lines << "  #{instruction_enum_name(inst)}#{comma}"
  end
  type_lines << "}"
  type_lines << ""
end
type_text = render(type_lines)

unknown_layouts = family_order.map { |family| family_parts(family).fetch(1) }.uniq - FAMILY_LAYOUTS.keys
raise "unmapped Ztt instruction layouts: #{unknown_layouts.join(', ')}" unless unknown_layouts.empty?

category_texts = category_order.to_h do |category|
  category_instructions = instructions.select { |inst| instruction_category(inst) == category }
  category_lines = generated_header(
    include_execute ? "#{category} instruction families generated from the manual instruction snapshot." :
                      "#{category} encodings generated without execute clauses."
  )
  semantic_text = include_execute ? semantic_source_text(category) : ""
  unless semantic_text.empty?
    category_lines << "// Hand-written execution semantics for this instruction category."
    category_lines << ""
    category_lines.concat(semantic_text.lines(chomp: true))
    category_lines << ""
  end
  family_order.select { |family| family_parts(family).first.to_s == category_code(category) }.each do |family|
    entries = family_entries.fetch(family).select { |inst| instruction_category(inst) == category }
    category_lines.concat(emit_family(family, entries, include_execute: include_execute)) unless entries.empty?
  end
  category_instructions
    .select { |inst| (family = instruction_family(inst)) != :fixed && family_entries.fetch(family).length == 1 }
    .each { |inst| category_lines.concat(emit_single_instruction(inst, include_execute: include_execute)) }
  category_instructions.select { |inst| instruction_family(inst) == :fixed }
                      .each { |inst| category_lines.concat(emit_fixed_instruction(inst, include_execute: include_execute)) }
  [category, render(category_lines)]
end

if stdout
  print type_text
  print common_text
  category_texts.each_value { |text| print text }
elsif output_file
  write_atomically(output_file, common_text + type_text + category_texts.values.join)
else
  write_atomically(output_dir / TYPE_FILE, type_text)
  write_atomically(output_dir / COMMON_FILE, common_text)
  category_texts.each do |category, text|
    write_atomically(output_dir / CATEGORY_FILES.fetch(category), text)
  end
end
