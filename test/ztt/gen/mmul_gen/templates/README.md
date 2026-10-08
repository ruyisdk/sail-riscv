# Templates

One module per template, plus `base.py` (the contract) and `__init__.py` (the instantiated
catalog); `ones_uniform.py` is the only module holding a shared `build` for a pair of templates. A
template is the smallest unit of coverage: it owns one datatype domain, builds cases for every
datatype in that domain, and renders those cases.

Templates are grouped by **instruction family**, and the catalog below is split into sections
accordingly. The same template can be reused by instructions from different families (for example
`matrix_small` serves 5 of the 6 matrix multiply instructions).

Instructions contain no assembly. An instruction only lists the templates it covers, so the same
template object serves all instructions — `matrix_small` is written once, here, yet appears in 5
generated sources.

```sh
# A live view of everything on this page (varies with the configuration).
cd sail-ame/test/ztt/gen
python3 -m mmul_gen --list --uds 8
```

## The shape of a template file

Every module has the same shape, in the same order:

```python
"""One-line summary."""

@dataclass(frozen=True)
class SomePayload:          # what `build` decided that `render` needs
    ...

def _some_trick(...): ...   # optional: an emit fragment only this template uses

class SomeTemplate(Template):
    """Summary; also what `--list` prints (read from here, not restated)."""

    name = "some_template"
    dtypes = SOME_DOMAIN

    def fits(self, machine, instruction, dtype) -> bool:   # only when it can decline
        ...

    def build(self, machine, instruction, dtype) -> list[Case]: ...
    def render(self, machine, instruction, case, out) -> None: ...
```

The payload is usually a frozen dataclass declared in this module, but not always:
`mixed_signedness_multiple_square` directly reuses the `MixedSignednessProduct` record already
returned by `reference.mixed_signedness_product`, instead of declaring the same fields again.

`build` decides values and layout and produces no assembly; `render` renders assembly and expected
data from the payload, and never recomputes expected values. `Template.__init_subclass__` rejects
subclasses missing a docstring, `name` or `dtypes`, so an undocumented template cannot exist in the
catalog.

`case_payload(PayloadType, case)` is the type check at the `build`/`render` boundary: if a case's
payload comes from another template, it raises a `TypeError` immediately and reports both type names
at once, instead of ending later in an `AttributeError`.

## Catalog

Case counts are taken from `--n 8 --uds 8 --m 32 --acc 4`, the configuration in which every template
survives. `dtypes` is the number of descriptors the domain selects under that configuration.

| Template                           | Datatype domain        | Instructions using it   | Cases/datatype | dtypes |
| ---------------------------------- | ---------------------- | ----------------------- | -------------- | ------ |
| `ones_uniform`                     | `integer`              | only `mmulacc.2d`       | 4              | 8      |
| `ones_uniform_128`                 | `integer128`           | only `mmulacc.2d`       | 4              | 2      |
| `matrix_small`                     | `integer`              | all except `mmulacc.2d` | 4              | 8      |
| `float_pair_sweep`                 | `softfloat`            | all 6                   | 8              | 6      |
| `packed_small`                     | `packed_integer`       | all 6                   | 4              | 2      |
| `saturating_boundary`              | `saturating_integer`   | all 6                   | 4              | 8      |
| `mixed_signedness_multiple_square` | `signed_packed_source` | all 6                   | 4              | 1      |
| `multi_acc_independent`            | `integer`              | only `mmulacc.2d`       | 3              | 8      |

The four templates of the `type_register` family (each case selects only one register file, so it
emits only one layout comment):

| Template                  | Datatype domain | Instructions using it | Cases/datatype | dtypes |
| ------------------------- | --------------- | --------------------- | -------------- | ------ |
| `MTypeRoundtrip`          | `every_dtype`   | `msettyp`, `mgettyp`  | 2              | 30     |
| `AccTypeRoundtrip`        | `every_dtype`   | `asettyp`, `agettyp`  | 4              | 30     |
| `MTypeUnsupportedProbe`   | `probe_dtype`   | only `msettyp`        | 2              | 1      |
| `AccTypeUnsupportedProbe` | `probe_dtype`   | only `asettyp`        | 4              | 1      |

The round-trip templates cover every register placement for each descriptor (low/high on the M side,
every accumulator on the ACC side); the probe templates run only on the two physical boundaries of
the M register file, and only for one descriptor.

The `load_store` family has only one template, shared by two instructions:

| Template      | Datatype domain | Instructions using it | Cases/datatype | dtypes |
| ------------- | --------------- | --------------------- | -------------- | ------ |
| `RawTransfer` | `every_dtype`   | `mls.1r`, `mss.1r`    | 1              | 30     |

The assembly of `mls.1r` and `mss.1r` is identical (one case first seeds with a load and then reads
back with a store); the only difference is the mnemonic on the `# case N:` line, so they are two
users of the same template object — exactly the example of "instructions compose templates" rather
than "instructions own templates". A raw transfer moves a whole physical register
(`n² · uds / 8` bytes) regardless of the descriptor, so every descriptor produces the same block, and
the case does not describe the register layout either.

The four templates of the `backend` family have no datatype dimension (`dtypes = None`) and build
exactly one case per configuration:

| Template              | Instructions using it | Scenario                                                                         |
| --------------------- | --------------------- | -------------------------------------------------------------------------------- |
| `AcquireReleaseState` | `ame.acquire`         | acquire ownership without contention, the status bit is observable, then release |
| `AcquireBusyState`    | `ame.acquire`         | the request is rejected under contention and does not change the state           |
| `ReleaseState`        | `ame.release`         | after release the status bit returns to idle                                     |
| `ReleaseIdleState`    | `ame.release`         | releasing while not holding is a no-op                                           |

The four scenarios share the architectural constants in `backend_state.py` (the status CSR and the
request mask). Acquiring ownership is what these cases **are meant to test**, so the instruction
family declares `acquires_backend = False`, and no standard prologue is inserted into the header.

The `accumulator` family has four templates, one per operation, each serving only one instruction:

| Template             | Template name (=`# input:` label) | Datatype domain | Instructions using it | Cases/datatype | dtypes |
| -------------------- | --------------------------------- | --------------- | --------------------- | -------------- | ------ |
| `AccumulatorZeroAcc` | `zero_acc`                        | `integer`       | `mzero.2d.acc`        | 4              | 8      |
| `AccumulatorZeroM`   | `zero_m`                          | `integer`       | `mzero.2d.m`          | 2              | 8      |
| `AccumulatorAccToM`  | `acc_to_m`                        | `integer`       | `mmov.m.a`            | 4              | 8      |
| `AccumulatorMToAcc`  | `m_to_acc`                        | `integer`       | `mmov.a.m`            | 4              | 8      |

Every case is "zero one register file, copy it into another, then check that the destination square
matrix is all zeros", so a single all-zero mirror check proves at once that the zeroing wrote
everything, the copy moved everything, and nothing was clobbered out of bounds. The four templates
share the base class and three emission helpers in `accumulator_common.py`; `AccumulatorAccToM` and
`AccumulatorZeroAcc` have identical assembly (they likewise lay the groundwork with `mzero.2d.acc`
before moving), differing only in the `# input:` label line, so they reuse the same helper instead
of duplicating code.

Two details appear only in this family: `AccumulatorZeroM` is the only template that does not
involve an accumulator (its case has only an M layout); and the destination M register of
`AccumulatorMToAcc` **reuses** the source register (`MRegisterRole(..., reuse_of="ms")`), because
the source has already been consumed by the accumulator when the result is read back. In addition,
the `accumulator` case enumeration covers **all** accumulators rather than a representative
low/high/boundary subset — each of its cases touches only one accumulator, so skipping one in the
middle would mean not testing it.

The `acc_span` family is the model for "**two case numberings in the same source**": a packed
(storage-only) datatype lets one M register hold `pack_factor = UDS / element_bits` square matrices,
so one accumulator operand represents a **contiguous span**. Its three declarations use only two
templates, and there is no family base class:

| Template                    | Template name         | Datatype domain  | Instructions using it   | Cases/instruction (n8/uds8/m32/a4)             |
| --------------------------- | --------------------- | ---------------- | ----------------------- | ---------------------------------------------- |
| `AccumulatorSpanRouting`    | `acc_span_routing`    | `packed_integer` | `mmov.m.a` / `mmov.a.m` | 12 (2 legal spans × 3 M layouts × 2 datatypes) |
| `AccumulatorSpanExceptions` | `acc_span_exceptions` | `packed_integer` | `mmov`                  | 1 per datatype                                 |

Two designs unique to this family:

- **The expected value is a consequence of the base address, not a hand-written list**: the routing
  template first writes the first image, then writes a second, overlapping image into an adjacent
  span, and then keeps in `build` the physical mapping of "which accumulator now holds which square
  matrix"; the expected values of the two read-backs are therefore derived directly from the
  selected span base addresses — including where the two spans overlap. A hard-coded expectation
  table could not explain the overlap.
- **There are two kinds of case numbering**: the routing label numbers (`span6_int4_*`) and
  `# case 6` are **file-global** indices (the driver's `case.number`), while the exceptions ones
  (`exc0_uint4_*`) are indices **within a datatype**. The two differ throughout the same source, and
  a wrong entry shifts a whole section at the first datatype boundary.

The exception recipe makes the "step outside the accumulator file" path as strong as the positive
tests: first fill every padding base address with a poison image, then clear the out-of-bounds base
address to zero, then `EXPECT_TRAP` twice, and finally read back **all** padding base addresses one
by one — the one deliberately zeroed reads 0 and the rest still read the poison value. It needs a
file-level `TRAP_GUARD_ARM` outside `Case.layout`, and the driver emits layouts in the order
"`# input:` → layout comment → case body", so the guard is written as a **leading pseudo-case** of
the first datatype, rather than by changing the driver or bypassing the layout declaration. The
out-of-bounds accumulator name is the **subject** of this family, and the guard in `test_generation`
is strengthened accordingly to "an out-of-bounds name must fall inside the `expected illegal` span
range declared by that case".

This family adds no new datatype domain: the domain is `packed_integer` (integer and narrower than
the UDS). The source names of the two routing instructions carry a family suffix
(`mmov_m_a_acc_span.S` / `mmov_a_m_acc_span.S`), which just needs overriding `file_name` with an
ordinary class attribute; the shared exception recipe uses `mmov` as its stem and
`acc_span_exceptions.S` as its file name.

The `strided_memory` family is the model for "**three recipes in one source**": 4 instructions
(load/store × normal/transposed) each get one source, and each source emits three recipes in a fixed
order; the three recipes have different datatype domains, so they correspond to exactly three
templates:

| Template                 | Template name              | Datatype domain      | Recipe                                                                                                                         |
| ------------------------ | -------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `StridedNormalSquare`    | `strided_normal_square`    | `semantic`           | move a whole square matrix segment by segment, one element per segment; with stride=0 all segments overlap at the same address |
| `StridedPackedStorage`   | `strided_packed_storage`   | `strided_storage`    | bit-preservingly move a packed image (`UDS / element width` logical square matrices per M register)                            |
| `StridedConversionPairs` | `strided_conversion_pairs` | `strided_conversion` | half-UDS storage descriptors widened/narrowed to their full-UDS twins via mconv, then moved                                    |

The three recipes are verified byte for byte by `tests/test_strided_recipe_parity.py`.

Two details unique to this family: **the conversion pair numbering** puts unsigned first and signed
second, so the `strided_conversion` domain selects descriptors in that order rather than reusing the
`pack` family's `packed_conversion`; and **the family base class lives in the instruction package**
(`instructions/strided_memory/base.py`) rather than in the template module — otherwise
`templates/__init__` → template module → `mmul_gen.instruction` → `templates.base` would form a
cycle, which is why the template module obtains `transfer` through a `TYPE_CHECKING` + duck-typing
narrowing.

The `logexp` family is the model for "12 instructions sharing a few templates": all the differences
are written as **declarations on the instruction**, and the templates only read declarations.

| Template                     | Template name                  | Datatype domain         | Used by        |
| ---------------------------- | ------------------------------ | ----------------------- | -------------- |
| `LogExpNominal`              | `nominal`                      | `integer`               | all 12         |
| `Exp2SaturatingBoundary`     | `exp2_saturating_boundary`     | `saturating_integer`    | `mexp2.ew`     |
| `Exp2Saturating128`          | `exp2_saturating_128`          | `saturating_integer128` | `mexp2.ew`     |
| `LdexpaccSaturatingBoundary` | `ldexpacc_saturating_boundary` | `saturating_integer`    | `mldexpacc.ew` |

Fields declared by the instructions: `src1_label`/`src2_label` (which data square matrix to read),
`expected` (the expected value per element), `form` (`unary`/`binary_m`/`ternary_m`/`binary_x`),
`scalar`, `initialize_destination`, `scalar_dtype_csr`. `mexp2.ew` therefore differs from the other
instructions in only two ways: it declares two more templates and two more input cases. Datatypes
skipped for lack of registers **still take a number**: the number is the datatype's position in its
own template domain, so skipped datatypes leave holes in the numbering.

The two assertions of the saturating group are independent: the result must clamp to the maximum,
**and** `amexsat` must be set — passing only one of them is not a pass.

In the `axis_permute` family one template serves one instruction, and **the input cases are a case
dimension rather than a template dimension**: the template's `build` returns `len(input_cases)` cases
per datatype, `Case.description` is the `# input: <label>` line, and the case order naturally matches
the numbering in the file.

| Template          | Template name      | Input cases                      | Datatypes (UDS=8) | Cases/instruction |
| ----------------- | ------------------ | -------------------------------- | ----------------- | ----------------- |
| `ColumnBroadcast` | `column_broadcast` | `first_column`, `last_column`    | 8                 | 16                |
| `RowBroadcast`    | `row_broadcast`    | `first_row`, `last_row`          | 8                 | 16                |
| `ColumnIndex`     | `column_index`     | `coordinate_ramp`                | 8                 | 8                 |
| `RowIndex`        | `row_index`        | `coordinate_ramp`                | 8                 | 8                 |
| `ColumnShift`     | `column_shift`     | `forward_shift`, `reverse_shift` | 8                 | 16                |
| `RowShift`        | `row_shift`        | `forward_shift`, `reverse_shift` | 8                 | 16                |

Every case loads a `1..nelem` ramp source into `m0`, performs the row/column operation, stores back
into the destination square matrix, and samples the five positions `(0, 1, n-1, n, nelem-1)` —
**this tuple is kept as is and not deduplicated**: when `n = 2` the 2nd and 3rd entries coincide and
that element is checked twice. Broadcast takes the first/last row (column) cases in order to pin
down both "read by row" and "the row stride equals the active length"; shift takes both a positive
and a negative direction in order to pin down that the out-of-bounds side must read as 0.

`column_index`/`row_index` likewise load the ramp source (even though they do not read it), and
their expected values are the coordinates themselves.

The `broadcast` family writes the **seven groups** of `mbcast.m.x` datatypes into a single source
file, so it is "one instruction, eight templates" (including one dtype-free template that declares
the input list):

| Template                               | Template name                   | Datatype domain         | Cases/datatype (UDS=8 / UDS=32) |
| -------------------------------------- | ------------------------------- | ----------------------- | ------------------------------- |
| `ScalarIngressBroadcast`               | `scalar_ingress`                | `integer`               | 8 / 4                           |
| `Integer128IngressBroadcast`           | `integer128_ingress`            | `integer128`            | 2 / 2                           |
| `SaturatingIngressBroadcast`           | `saturating_ingress`            | `saturating_integer`    | 8 / 4                           |
| `SaturatingInteger128IngressBroadcast` | `saturating_integer128_ingress` | `saturating_integer128` | 2 / 2                           |
| `PackedStorageBroadcast`               | `packed_storage_ingress`        | `packed_storage`        | 4 / 6                           |
| `FloatingBroadcast`                    | `floating_ingress`              | `softfloat`             | 6 / 2                           |
| `UnsupportedDtypeProbe`                | `unsupported_dtype_probe`       | none (dtype-free)       | 1 / 1                           |

The first four templates (integer/128-bit/saturating/saturating 128-bit) differ only in their
datatype domain and emit exactly the same body, so they share one base class; the last three each
emit different content and each get their own file. Three idioms that appear only in `broadcast`:

- **Case numbering restarts per group**: the N in `# case N` is "the datatype's position in its own
  template domain", not a file-wide count.
- **The input list is an independent case**: the file lists all 7 `# input:` lines at once before
  the first case, and independently of the configuration; making it a dtype-free template declared
  first keeps it unconditional while placing it in the only position the format allows.
- **Floating point uses raw bit patterns**: broadcast scalars are written as bit-pattern literals
  (e.g. `0x3c00`) and do not go through the host floating-point library.

The two domains cover storage and 128-bit saturating: `packed_storage` (**all** descriptors with
`bits*2 == uds`, including saturating and floating-point ones — bit-preserving operations do not
require pairing) and `saturating_integer128`. At UDS=32 they move FP16/BF16 from the floating-point
group into the storage group, so a list hard-coded for one group would be wrong.

The `matrix_ops` family is the most thorough instance of "**declarations instead of dispatch**": its
20 instructions are split into three groups by operation shape, each group uses a single template,
and **nowhere** inside a template is there dispatch on a mnemonic. All the differences are written
as three enum declarations on the instruction.

| Template                 | Template name                 | Datatype domain      | Instructions using it             | Cases/instruction (n8/uds8/m32/a4) |
| ------------------------ | ----------------------------- | -------------------- | --------------------------------- | ---------------------------------- |
| `ReducePrefixRamp`       | `reduce_row_ramp`             | `integer`            | 10 reduce/prefix                  | 9 (17 for the two `add.row`)       |
| `ReducePrefixSaturating` | `reduce_saturating_boundary`  | `saturating_integer` | `mreduceadd.row`/`mprefixadd.row` | 8                                  |
| `ZipDualSource`          | `zip_dual_source_ramp`        | `integer`            | 4 zip/unzip                       | 8                                  |
| `ZipExtraSource`         | `zip_extra_dtype_ramp`        | `extra_permute`      | 4 zip/unzip                       | 14                                 |
| `GatherScatterIndexed`   | `gather_indexed_elements`     | `integer`            | 6 gather/scatter                  | 8 (16 for `mrowscatadd`)           |
| `GatherExtraIndex`       | `gather_extra_dtype_index`    | `extra_permute`      | only `mcolgather.ew`              | 14                                 |
| `ScatterSaturating`      | `scatter_saturating_boundary` | `saturating_integer` | only `mrowscatadd.ew`             | 8                                  |

The three enums **carry their own algorithms**, and what a template receives is not an instruction
member but a constructor argument (written as `ReducePrefixRamp(MatrixAxis.ROW, Reduction.SUM)` and
the like), while the enum values themselves are still declared by
`mmul_gen/instructions/matrix_ops/base.py`:

| Declaration                                 | Enum                           | Values               | How the template uses it                                                                                             |
| ------------------------------------------- | ------------------------------ | -------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `ReducePrefixInstruction.axis`              | `MatrixAxis`                   | `row`/`column`       | `line_indices` (whole row/column) + `prefix_indices` + `reduce_check_indices`/`prefix_check_indices` (sample points) |
| `ReducePrefixInstruction.reduction`         | `Reduction`                    | `sum`/`max`/`min`    | `aggregate(values)`                                                                                                  |
| `ReducePrefixInstruction.prefix`            | `bool`                         | —                    | whether to take the prefix or the whole row                                                                          |
| `ZipInstruction.axis` / `.unzip`            | `MatrixAxis` / `bool`          | —                    | `varying` (which coordinate is being interleaved) + `result_index` (where the result lands)                          |
| `GatherScatterInstruction.axis` / `.access` | `MatrixAxis` / `ScatterAccess` | `gather`/`add`/`max` | `source_index` (where to read) + `result_index` (where to write) + `combine`/`accumulates`/`by_max`                  |

The 10 reduce/prefix instructions are in fact the 10 configurations of `axis × reduction × prefix`
(`row×sum×reduce` = `mreduceadd.row`, `column×sum×prefix` = `mprefixadd.col` ...), so "one
expected-value table per instruction" is replaced by one general formula. The `extra_permute` domain
(`bits >= uds` and not an ordinary integer) is exactly what this family needs: zip and gather need
three non-overlapping register groups, so they run saturating and floating-point descriptors.

Three idioms that appear only in `matrix_ops`:

- **Emit `.data` even with zero cases**: the whole family still produces a `.data` section (empty)
  in a configuration where no type fits, so all three family base classes declare
  `always_emits_data = True`.
- **Sample points are a function of the shape, not of the mnemonic**: reduce samples
  `(0, n-1, nelem-1)` and prefix samples along the axis `(0, 3, n+2)` or `(0, n, 2n+3)`, written as
  methods of `MatrixAxis`.
- **The register-group count checks are asymmetric**: zip's ordinary branch does not check
  `2*nregs <= num_m_regs`, while the extra branch skips types that do not fit.

The `float_math` family is the model for "**one template holding the whole family**": its 10
instructions each declare one `MathOperation` enum member, and the whole family has only **one**
emission template — because the generated file is **interleaved by datatype**: for each datatype it
first emits its nominal cases, then its own boundary scenarios, and only then moves on to the next
datatype. The framework pipeline is "template → datatype", so two templates would turn the order
into "all nominal, then all boundary", which is a different file. So the nominal / boundary /
transcendental emitters are three private methods of the same template, distinguished by
`Case.payload`.

| Template         | Template name      | Datatype domain    | Instructions using it | Cases/instruction (n8/uds8/m32/a4)                      |
| ---------------- | ------------------ | ------------------ | --------------------- | ------------------------------------------------------- |
| `FloatMathCases` | `float_math_cases` | `formed_softfloat` | all 10                | see the table below (1 catalog case + several per type) |

Case counts by operation category (including that 1 catalog case):

| Category               | Instructions       | Per datatype                                                               | Cases |
| ---------------------- | ------------------ | -------------------------------------------------------------------------- | ----- |
| rounding               | `mfrintm/n/p/z.ew` | 1 nominal + 6 rounding modes                                               | 43    |
| reciprocal             | `mrec.ew`          | 1 + 24 (12 poles at ±0 + 12 overflows at ±smallest subnormal)              | 151   |
| reciprocal square root | `mrsqrt.ew`        | 1 + 18 (12 poles + 6 negative invalid)                                     | 115   |
| square root            | `msqrt.ew`         | 1 + 12 (6 negative invalid + 6 inexact √2)                                 | 79    |
| transcendental         | `mcos/sin/tanh.ew` | 6 (±0, qNaN, ±inf, 1.0 numeric cases; E4M3 has no inf encoding, so only 4) | 35    |

| Declaration | Values                          | Description                                                                                                            |
| ----------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `operation` | 10 members, one per instruction | the enum member carries its own nominal stimulus, boundary scenarios, and the host libm entry name for transcendentals |

Three idioms that appear only in `float_math`:

- **The domain must be the formed version**: `formed_softfloat`. `softfloat` goes through
  `semantic_dtypes` (which is what `mmul` uses), while this family goes through `formed_dtypes` —
  at UDS=16 the 8-bit OCP formats are packed storage and must still be covered, so using the wrong
  domain would drop two datatypes entirely.
- **Expected values come from the host libm, not from a table**: the narrow-format cases of the
  transcendental functions replicate the simulator's path (widen to f32 → call the **host**
  `cosf`/`sinf`/`tanhf` → narrow back with RNE), and cross-check against a 30-bit mpmath reference
  at generation time with a 2 ulp budget — host libm drift blows up at generation time instead of
  becoming a flaky failure in the test.
- **The reference tables are reused module-wide**: the bit-pattern tables come from
  `mmul_gen/fp_semantics.py`, and `tests/test_fp_semantics_parity.py` guards every table and every
  rule for equality.

The `integer_shift` family has two templates, split by "where the shift amount comes from" rather
than by instruction: the three shift instructions (`msll`/`msrl`/`msra`) each choose one of them, so
one template serves three instructions.

| Template              | Template name           | Datatype domain  | Instructions using it               | Cases/datatype | dtypes            |
| --------------------- | ----------------------- | ---------------- | ----------------------------------- | -------------- | ----------------- |
| `ShiftRegisterSource` | `shift_register_source` | `formed_integer` | `msll.ew`/`msrl.ew`/`msra.ew`       | 1              | 10 (5 for `msra`) |
| `ShiftScalarSource`   | `shift_scalar_source`   | `formed_integer` | `msll.ew.x`/`msrl.ew.x`/`msra.ew.x` | 1              | 10 (5 for `msra`) |

The two differ only in "where the shift amount comes from": the register form reads a per-element
amount from a second M operand, and the scalar form reuses a single integer register. The shift
amount sweeps the boundaries `0, 1, bits-1, bits, bits+1, 2*bits-1` — only amounts **equal to or
exceeding the element width** can exercise the hardware's modulo reduction of the shift amount,
which a "constant shift" test can never reach. The source pattern makes every element's sign bit
constantly 1.

This family is the first to use three new framework capabilities:

- the `formed_integer` domain (`machine.formed_dtypes`) has **sub-UDS** 4/8-bit descriptors in
  addition to the `integer` domain, so narrow types such as `AME_UINT4_DTYPE` enter the cases too;
  four-bit elements pack two nibbles onto the same `.byte` line (not split across lines, otherwise
  the bytes would no longer match).
- `choose_m_group_base(num_m_regs, bits, uds, preferred=16)` keeps the preferred `m16` base address
  and falls back to the last aligned group when the register file is too small.
- `fits(machine, instruction, dtype)` can now see the instruction: `msra` has one more restriction
  than the other two — only signed descriptors have arithmetic right-shift semantics, and since the
  three instructions share the same template, the restriction belongs to the **operation** and not
  to the template.

The `memory_order` family has two templates, one per direction, and each direction is shared by its
load and store instructions:

| Template              | Datatype domain | Instructions using it | Cases/datatype | dtypes |
| --------------------- | --------------- | --------------------- | -------------- | ------ |
| `MemoryOrderRowToCol` | `integer`       | `mls.rm`, `mss.cm`    | 1              | 8      |
| `MemoryOrderColToRow` | `integer`       | `mls.cm`, `mss.rm`    | 1              | 8      |

A single case executes the whole round trip of "load in one memory order, then store back in the
other", so the assembly of `mls.rm` and `mss.cm` is identical, differing only in the header and the
`# case` line — another example of one template serving two instructions. The two directions are
inverse transforms, so the expected values are exactly swapped (whether the second element and the
first element of the next storage row are `N+1`/`2` or `2`/`N+1`). The `# input:` label appears only
once, before the whole dtype loop, expressed by "the case of the first dtype carries a
`description` and the rest are `None`" (the same pattern as `raw_transfer`).

The `debug_move` family has four templates, one per width, and each width is shared by two
instructions:

| Template      | Datatype domain | Instructions using it        | Cases/datatype | dtypes |
| ------------- | --------------- | ---------------------------- | -------------- | ------ |
| `DebugMove8`  | none (`None`)   | `mmove8.m.x`, `mmove8.x.m`   | 1              | —      |
| `DebugMove16` | none (`None`)   | `mmove16.m.x`, `mmove16.x.m` | 1              | —      |
| `DebugMove32` | none (`None`)   | `mmove32.m.x`, `mmove32.x.m` | 1              | —      |
| `DebugMove64` | none (`None`)   | `mmove64.m.x`, `mmove64.x.m` | 1              | —      |

The cases of all four instructions go in both directions (write into the M register, then read it
back), so the assembly of `.m.x` and `.x.m` is **completely identical**, differing only in the header
line — which is why there is "one template serving two instructions" rather than two nearly
identical templates. The four templates share the family base class in `debug_move_common.py`, and
subclasses declare only three constants (`element_bits`, `position`, `value`).

This family is also the only one whose **source set varies with the configuration**: an instruction
whose width exceeds one row (`n * uds` bits) does not generate a source at all in that configuration,
because the model reports an Illegal Instruction for it and there is nothing to test. So at
`n=4, uds=8` there are only 6 sources, and 8 sources only from `n=8, uds=8` onwards.

The `pack` family has two templates, sharing the shape and the three input patterns of
`pack_common.py`:

| Template      | Datatype domain     | Instructions using it | Cases/datatype | dtypes |
| ------------- | ------------------- | --------------------- | -------------- | ------ |
| `PackSlots`   | `packed_conversion` | only `mpack.ew.x`     | 3              | 2      |
| `UnpackSlots` | `packed_conversion` | only `munpack.ew.x`   | 3              | 2      |

Both templates inherit the dtype-free family base class `PackedSlotConversion` in `pack_common.py`,
with the input patterns fixed to the three `selected_slot` / `preserved_slot` /
`signed_boundary_values`, and the selected slot is always 3. "The selected slot is written
correctly, not one byte of the unselected slots is touched, and the signed boundary values are
correct" must be tested separately, so there are three cases rather than three sections of one case
— any single failure can be located immediately to one class of error.

The `mconv` family has only one template, and it is also the only template used by conversions in
both directions at once:

| Template         | Datatype domain     | Instructions using it | Cases/datatype | dtypes |
| ---------------- | ------------------- | --------------------- | -------------- | ------ |
| `MconvRoundtrip` | `packed_conversion` | `mconv.ew`            | 1              | 2      |

`mconv.ew` performs conversions in both directions at once (widening the packed storage square
matrix, then narrowing the two compute square matrices back), so only one template can be used. Its
datatype domain selects **two** descriptors under this configuration (one unsigned and one signed),
each descriptor produces **one** case, and the expected value rotates through seven boundary values.
Its header also has a line `UDS=<uds>: storage=<uds/2>, compute=<uds>`, appended by the instruction
file overriding `banner(machine)`.

The number of cases per datatype is exactly the number of legal M/ACC layout pairs that
`paired_cases` finds for that datatype, so it varies with the configuration and drops as registers
get scarcer. Under `--m 16 --acc 1`: `ones_uniform`, `matrix_small` and `saturating_boundary` become
1 or 3, `float_pair_sweep` becomes 2 or 6, `packed_small` and `mixed_signedness_multiple_square`
become 3, while `ones_uniform_128` and `multi_acc_independent` do not run at all — their `fits`
predicates reject that configuration outright instead of re-laying out the operands.

`elementwise` is the only family where the **scenarios are written in the instruction**: there are 7
scenario classes, and which ones an instruction runs is decided by its own `templates` list — the
list is the catalog of what runs, and behavior not written into it does not exist on that
instruction. So `--list` reports each instruction's own scenario count: `mand.ew` reports 2 and
`madd.ew` reports 7, rather than everyone reporting 7. The 7 templates are listed in the order their
cases appear in the source:

| Template                              | Datatype domain             | Instructions that actually emit cases | Total cases (`--m 32`) | dtypes | How the entry is constructed                                                   |
| ------------------------------------- | --------------------------- | ------------------------------------- | ---------------------- | ------ | ------------------------------------------------------------------------------ |
| `elementwise_integer_value_rules`     | `formed_integer`            | 46/46                                 | 2040                   | 10     | 46/46 (integer list + that instruction's `evaluate`)                           |
| `elementwise_integer_value_rules_128` | `integer128`                | 46/46                                 | 268                    | 2      | 46/46 (same, with `wide=True`)                                                 |
| `elementwise_saturating_boundary`     | `formed_saturating_integer` | 7/46                                  | 65                     | 10     | `SaturatingExpectation` + `CasePlan`                                           |
| `elementwise_saturating_boundary_128` | `saturating_integer128`     | 6/46                                  | 11                     | 2      | same as above                                                                  |
| `elementwise_float_nominal`           | `formed_softfloat`          | 27/46                                 | 162                    | 6      | that instruction's `evaluate_float` (`comparison=True` for comparison classes) |
| `elementwise_float_special_values`    | `formed_softfloat`          | 27/46                                 | 541                    | 6      | `FloatArithmeticRole` or `FloatSpecialRole`                                    |
| `elementwise_float_semantics_sweep`   | `formed_softfloat`          | 18/46                                 | 108                    | 6      | `FloatArithmeticRole`                                                          |

The "instructions that actually emit cases" column is not hand-written but **counted from the
`templates` of the 46 classes**: 7 = the number of `SATURATING_EXPECTED_KIND` entries, 6 =
`SATURATING_128_INSTRUCTIONS`, 27 = `FLOAT_EXPECTED_KEYS` (23 nominal + 4 comparison), 27 = 9
special-case + 18 arithmetic special-case, 18 = `ELEMENTWISE_FP_ROUNDING_INSTRUCTIONS`. If the list
changes, these four numbers change immediately.

"Which scenario runs" is decided by the instruction, and in exactly one place: the instruction
**constructs each template it wants to run** into `templates`, passing the values into the
constructor on the spot — **there is no other gate**, and a template not written into the list does
not run, so the instruction file is its complete check list. The two 128-bit ones follow their
respective roots and receive the same values. The order of the scenario classes is given by
`ELEMENTWISE_TEMPLATE_CLASSES`, and the test verifies each instruction's list.
Together the two are compared point by point by `test_elementwise_template_table_parity.py` (46
instructions × 7 scenarios × 120 configurations), so a wrong order, a wrong argument or a missing
scenario immediately becomes a comparison failure. The scenarios themselves only answer "does this
configuration have room for my cases", and do not guess whether the instruction has this behavior.

The two integer templates take "list + formula", and the floating-point nominal one takes "formula +
a `comparison` flag" — both paths are functions written in the class, differing only in the body:
arithmetic for integers, a `FLOAT_OPERATION_VALUES` lookup for floating-point nominal (comparison
classes give all ones/0 and rely on that flag to seed the destination and to walk the three M
register groups). The other two cells take a role, because their expected value is a set of cases
rather than a single number.
The first four templates separate "integer/saturating" from "128-bit" because 128-bit datatypes have
completely different case construction and expected-value computation (spanning multiple M
registers); the three floating-point templates share the `formed_softfloat` domain but each filters
different instructions: nominal, special values (NaN/infinity/signed zero and invalid operations),
and the rounding sweep. Of the 6 dtypes in `float_special_values`, one emits only 1 case and the
rest emit 3 each, the difference coming from `NO_INFINITY_DTYPES` — `AME_OCP_E4M3_DTYPE` has no
infinity encoding, so it has no infinity case.

The **case count of the floating-point scenarios varies with the configuration**:
`float_semantics_sweep` only emits cases for instructions that declare `float_arithmetic` and are
not in scalar form (the scalar form has a different rounding path, covered by two other blocks); the
ternary form of `float_special_values` uses the destination's NaN rather than the addend's NaN; these
differences are all dispatched inside the template by `form`, and do not require a copy in each
instruction file.

## Template by template

### `ones_uniform` — whole-register smoke test

- **Coverage** all non-saturating integers that can make up a full M register.
- **Stimulus** both source square matrices are all ones, and the accumulator is zeroed with
  `mzero.2d.acc`, so the destination value is the sum of N 1×1 products.
- **Expected value** `uniform_ones_product` = N; −N when the instruction negates the product.
- **Self-check** load the starting bytes of the first, second and last elements byte by byte, and
  compare each against the expected byte (`check_dst_lines`).
- **Why it is needed** it is the cheapest test that can fail. No value depends on position, sign,
  packing or saturation, so if it fails here the problem must be in the formation, the datatype or
  the accumulate/subtract semantics, not in the numbers themselves.
- **Who uses it** only `mmulacc.2d`: it is the only instruction that reads the accumulator back with
  just `mmov.m.a` after obtaining a new product, which is exactly the precondition that makes the
  "accumulator already zeroed, image uniform" case meaningful.

### `ones_uniform_128` — a destination spanning multiple registers

- **Coverage** `AME_{UINT,INT}128`, i.e. descriptors spanning multiple M registers.
- **Stimulus and expected value** inherited verbatim from `ones_uniform`; only the renderer, the
  datatype domain and the predicate differ.
- **Self-check** compare the first and last 128-bit elements. The value of a 128-bit element is N in
  the **first byte** of each 16-byte slot (the remaining bytes are two's-complement filled when
  negated), so the endpoint comparison verifies the address and layout of the cross-register image.
- **Why it is needed** 128-bit destinations are where cross-register formation of M registers and
  `movv.m.a` multi-register write-back go wrong.
- **Who uses it** only `mmulacc.2d`, and only when both M register spans fit.

### `matrix_small` — a position-dependent product

- **Coverage** all non-saturating integers that make up a full M register.
- **Stimulus** `small_matrix_inputs` builds `a[i][j] = (i + 2j + 1) mod 3` and
  `b[i][j] = (2i + j + 2) mod 3` in row-major order. The values are always less than 3, so the exact
  product is representable under every datatype here.
- **Expected value** `small_matrix_product` replays the dot product exactly and applies the
  instruction's `product_flags` (transpose left, transpose right, negate).
- **Self-check** it checks 5 element positions — first element, second element, first element of the
  second row, some position in the middle of the square matrix, last element
  (`check_dst_element_lines`) — which is exactly what makes "position dependence" genuinely
  observable.
- **Why it is needed** it is the only integer template whose expected value depends on row and
  column, so it can catch strides, indexing and row/column mix-ups that a uniform square matrix
  cannot see. Transpose variants are distinguished here too: `reference.py` replays the dot product
  according to the instruction's `product_flags`, so a transpose shows up only in the emitted
  expected value, with the stimulus and the code byte-for-byte identical.
- **Who uses it** the 5 ordinary product instructions; `mmulacc.2d` uses `ones_uniform` instead.

### `float_pair_sweep` — one template, two payloads

- **Coverage** `E4M3`, `E5M2`, `FP16`, `BF16`, `FP32`, `FP64`.
- **Stimulus and expected value** two payloads, dispatched in `render`:
  - `FloatNominalPayload` — all-ones product, exactly representable, with expected value
    `softfloat_product_expected`, i.e. N as a power of two (narrow formats are limited by their
    mantissa width).
  - `FloatOverflowPayload` — largest finite value times 2, walking all rounding modes and signs,
    with the expected value taken from `float_overflow_boundaries` per mode.
- **Self-check** nominal compares the expected square matrix; overflow additionally asserts the
  exception flags (`EXPECT` on `fflags` is inexact) and checks together with the infinity image.
- **Why it is needed** it is the only template that checks **flags** and not just data, and the only
  one covering rounding modes. The overflow sweep is what exposes regressions in rounding-mode or
  flag propagation.
- **Who uses it** all 6 instructions.

### `packed_small` — sources whose storage width is narrower than the UDS

- **Coverage** every integer descriptor whose storage width is narrower than the current UDS.
- **Stimulus** left-hand 1, right-hand 2, accumulate. Packed instructions fold each storage slot in
  a row into the destination element, so the expected value is `2 * pack * N`, where
  `pack = uds / element_bits`.
- **Expected value** `packed_product`, with the destination datatype selected by
  `packed_compute_dtype` — a whole-register type, not a storage type.
- **Self-check** compare the first and last elements of the whole-register destination image
  (`check_dst_lines`).
- **Why it is needed** the source storage width differs from the destination formation width, so
  this is where widening or write-back errors are caught. Selecting the wrong destination datatype
  changes the storage image, and no same-width template would notice.
- **Who uses it** all 6 instructions.

### `saturating_boundary` — data plus the exception flag

- **Coverage** `AME_*_SAT` integer descriptors.
- **Stimulus** a single accumulation: all ones multiplied by the maximum representable value. If the
  reference product does **not** actually saturate, `saturating_edge_product` raises outright, so
  when the stimulus no longer touches the boundary it is a generation-time failure rather than a
  quiet degradation into an ordinary boundary test.
- **Expected value** the saturated result, plus `amexsat` reading 1, asserted with `EXPECT`.
- **Self-check** check the first and last elements (`check_dst_element_lines`), and separately assert
  `amexsat`.
- **Why it is needed** it is the only integer template that asserts that saturation is **reported**,
  not merely clamped. Wrap-around regressions and missing flags are two different classes of defect,
  and this is the only place that pins both down at once.
- **Who uses it** all 6 instructions, and only when both M register spans fit.

### `multi_acc_independent` — one accumulator does not stand in for another

- **Coverage** non-saturating whole-register integers.
- **Stimulus** seed each legal accumulator with `mmov.a.m` using `0x11 * (index + 1)`, then
  accumulate the same all-ones product into all accumulators, and finally read each back into its own
  destination square matrix.
- **Expected value** `seeded_ones_product` = seed + N, per accumulator.
- **Self-check** each accumulator's destination square matrix is compared independently
  (`check_dst_lines`), and each has its own data label (`..._acc0_dst`, `..._acc1_dst`, ...), so a
  mismatch points to which accumulator it is.
- **Why it is needed** the seeds are distinct and spaced apart, so "one accumulator bleeding into
  another" or "one operand aliasing two accumulators to the same register" changes the stored result
  immediately. Uniform seeds would hide all of this.
- **Who uses it** only `mmulacc.2d`, and only when at least two accumulators exist.

### `mixed_signedness_multiple_square` — one operand holding two square matrices

- **Coverage** signed integer descriptors half the width of the current UDS.
- **Stimulus** `_packed_square_data_lines` packs two **logical** square matrices (differing in both
  sign and value) into the same physically formed operand, so a single `mls.rm` load obtains both at
  once.
- **Expected value** `mixed_signedness_product` returns a `MixedSignednessProduct` describing the
  two halves; the check proceeds by geometric width rather than element width.
- **Self-check** compare the storage square matrix against the expected image byte by byte
  (`check_dst_lines`), by geometric width rather than element width.
- **Why it is needed** it is the only template that puts "two differently signed square matrices in
  one operand"; sign extension of the packed source and "whether the product read both halves" are
  decided here.
- **Who uses it** all 6 instructions.

### `MTypeRoundtrip` / `AccTypeRoundtrip` — descriptor round-trips

For **every** descriptor declared in the macro file (`every_dtype`, with no UDS filtering: a
round-trip does not form an operand, so there is no storage ratio to speak of), write the type code
into the register and read it back, then compare against the type-code macro. The M side covers
every legal placement (landing on low and on high when spanning 1/2/4/8/16 registers) and the ACC
side covers every accumulator. The description text on the `# case N:` line comes from the
instruction's `case_action`, because that sentence names both the writer and the reader.

### `MTypeUnsupportedProbe` / `AccTypeUnsupportedProbe` — illegal type codes

First seed the register with `AME_INT8_DTYPE`, then feed in the out-of-encoding `0x80000008`: the
status bit must report rejection, and the descriptor must still read back the seeded value. This is
**error-path** coverage, a different matter from the round-trip templates, so it is a separate
template rather than a branch inside the round-trip template.

## Checking machinery

The generator emits only the **static N** form: N is known at generation time, so expected values
can be computed exactly and emitted as immediates, and the check only has to compare a few fixed
positions. All renderers share two primitives:

| Primitive                 | Purpose                                                                                   |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| `check_dst_lines`         | uniform expected square matrix: compare the first and last elements                       |
| `check_dst_element_lines` | position-dependent expected square matrix: compare exactly the element at one given index |

Both carry the element index, so the assertion itself states which position it checks; the
comparison is done through the `EXPECT` macro, and on failure `RVMODEL_HALT_FAIL` writes the uniform
code 3 to `tohost` — that is, the static form only tells you **that this source failed**, and
locating the failure means reading the assembly. This is coarser than the runtime encoding mentioned
below, but it is how these 720 generated sources have actually been used all along.

### Why there is no `--generic-n`

An earlier version also supported a `--generic-n` mode: tables were generated for the maximum N, the
check loops were bounded by the `amenlen` read at runtime, and so one binary could run with the same
set of different N configurations ≤ 32. It has been removed.

The reason is that it **conflicts with the goals** of static N: the expected value changes when N
changes, while the immediates in the binary are fixed at generation time. So `--generic-n` could
only switch to recomputing expected values in assembly inside the test, giving up the strong
guarantee that "expected values come from the Python reference implementation" in exchange for "one
binary across N". And that "across N" capability has no consumer in this project:
`run_ztt_tests.py` renders one model configuration per configuration and always builds the binary
for one N and runs it for that same N. More importantly, the set of N values one binary could cover
would not grow — N is a power of two in the model, and the powers below 32 are exactly 4/8/16/32,
the same as the static matrix.

If "one binary covering multiple N configurations" is genuinely needed in the future, the right
approach is to bake the expected values for every supported N into the binary and select at runtime
based on `amenlen`, rather than recomputing the formula inside the test; but that is only worth
introducing given a real requirement.

## Inheritance and reuse

Only one template inherits from another: `OnesUniform128` inherits `OnesUniform`, overrides
`render`, `dtypes` and `fits`, and inherits `build` verbatim. This is the only place in the whole
generator where a template body is genuinely shared through inheritance, and it is the pattern to
follow: use a subclass only when the case construction is completely identical and only the
rendering or the applicable domain differs.

`FloatPairSweep` shows another seam — `render` dispatches to `self._render_nominal` /
`self._render_overflow`, so "one template with two payload shapes" can keep one public entry point
and two private implementations.

Instructions reuse templates by **composition**, not inheritance: they hold the same instances. 6
instructions share `float_pair_sweep`, `packed_small`, `saturating_boundary` and
`mixed_signedness_multiple_square`; 5 share `matrix_small`; only `mmulacc.2d` additionally adds
`ones_uniform`, `ones_uniform_128` and `multi_acc_independent`.
`mmul_gen.tests.test_templates` pins down both "the same object is shared" and the inheritance
relationship above.

## Adding a template

1. Add `<name>.py` with the payload, the class and the docstring.
2. Instantiate it in `__init__.py` and add it to `ALL_TEMPLATES`.
3. Add the instance to the `templates` tuple of every instruction that should cover it.
4. Add a row to the coverage table in the README one level up.

`build` and `render` are the only required members; `fits` is only needed when the template requires
more than one M register span. Apart from the new module and the two declarations above, nothing
needs changing.
