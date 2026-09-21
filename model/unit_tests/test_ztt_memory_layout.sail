// Memory-layout helpers are pure, so these tests exercise packed and wide
// transfer ordering without depending on a host memory-map configuration.
$[test]
function test_ztt_typed_memory_layouts() -> unit = {
  let uint4 : bits(32) = 0x00000004;
  let int4 : bits(32) = 0x40000004;
  let uint128 : bits(32) = 0x00000080;
  let int128 : bits(32) = 0x40000080;

  // Packed 4-bit row-major transfers preserve all packed sub-squares.
  var packed_rm : bits(acclen) = zeros();
  foreach (index from 0 to (ame_total_elements(uint4) - 1)) {
    packed_rm = insert_elem_rm(packed_rm, 4, index,
      zero_extend(ame_max_dtype_size, to_bits(4, index % 16)))
  };
  assert(ame_square_memory_to_rm(uint4,
    ame_square_rm_to_memory(uint4, packed_rm, false), false) == packed_rm);

  // Column-major order is a permutation only within each packed sub-square.
  assert(ame_square_memory_to_rm(int4,
    ame_square_rm_to_memory(int4, packed_rm, true), true) == packed_rm);

  // 128-bit values are represented byte-wise in the staged memory image and
  // retain their complete 128-bit payload in both layouts.
  var wide_rm : bits(acclen) = zeros();
  foreach (index from 0 to (ame_total_elements(uint128) - 1)) {
    let lo : bits(64) = to_bits_unsafe(64, index : int);
    let hi : bits(64) = ~(lo);
    let value : bits(128) = hi @ lo;
    wide_rm = insert_elem_rm(wide_rm, 128, index,
      zero_extend(ame_max_dtype_size, value))
  };
  assert(ame_square_memory_to_rm(uint128,
    ame_square_rm_to_memory(uint128, wide_rm, false), false) == wide_rm);
  assert(ame_square_memory_to_rm(int128,
    ame_square_rm_to_memory(int128, wide_rm, true), true) == wide_rm);
}

$[test]
function test_ztt_store_fault_reporting() -> unit = {
  let uint8 : bits(32) = 0x00000008;
  let address_bits : bits(5) = 0b00001;
  let address_reg = Regidx(trunc(address_bits));
  let store_fault = E_SAMO_Access_Fault();

  ame_test_enable_context();
  X(address_reg) = to_bits_unsafe(xlen, 4096 : int);

  // Late vmem_write failures are returned immediately and normalized to the
  // instruction base address, even though transactional rollback is deferred.
  assert(ame_memory_exception_at_base(address_reg, Store(Data),
    memory_exception(store_fault, bits_of(Virtaddr(to_bits_unsafe(xlen, 4224 : int))), Store(Data))) ==
    memory_exception(store_fault, bits_of(Virtaddr(X(address_reg))), Store(Data)));

  // Instruction-level validation likewise reports a store exception instead
  // of retiring when the complete square transfer is misaligned.
  MD(Mdregidx(0b00000)) = uint8;
  X(address_reg) = to_bits_unsafe(xlen, 1);
  assert(execute(TEST_AME_MSS_RM(0b00000, address_bits)) ==
    memory_exception(E_SAMO_Addr_Align(), bits_of(Virtaddr(X(address_reg))), Store(Data)));
}
