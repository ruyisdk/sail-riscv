# Ztt test generator (`mmul_gen`)

The Ztt test generator: **one file per instruction, one file per template**, grouped by instruction
family. It is the only test generator in the repository, and `test/ztt/run_ztt_tests.py` calls it
directly.

Coverage: **141 sources** (`accumulator` 4 + `acc_span` 3 + `axis_permute` 6 + `backend` 2 + `broadcast` 1 +
`debug_move` 8 + `elementwise` 46 + `float_math` 10 + `integer_shift` 6 +
`load_store` 2 + `logexp` 12 + `matrix_ops` 20 + `mconv` 1 + `memory_order` 4 +
`mmul` 6 + `pack` 2 + `strided_memory` 4 + `type_register` 4).

```sh
cd sail-ame/test/ztt/gen
python3 -m mmul_gen --list                    # the catalog of all families
python3 -m mmul_gen --family type_register --list
```

```sh
cd sail-ame/test/ztt/gen
python3 -m mmul_gen --list
python3 -m mmul_gen --n 8 --uds 8 --m 32 --acc 4 \
    --out-dir <out-dir>
python3 -m mmul_gen.tests
```

## Directory structure

| Path                                  | Responsibility                                                                                                                                                                    |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `instructions/<family>/<mnemonic>.py` | one file per instruction, one package per family; the class inherits the family's base class                                                                                      |
| `catalog.py`                          | **Entry point.** The ordered instruction tuple and the generation loop                                                                                                            |
| `instruction.py`                      | the instruction base class: `gen()`, operands, the title, and the contract that "a class only declares identity and formula"                                                      |
| `templates/`                          | one module per template: a `Template` subclass with a docstring, owning its own datatype domain, case builders and renderer. See [`templates/README.md`](templates/README.md)     |
| `templates/base.py`                   | the `Template` contract, the case model, and the machinery more than one template needs                                                                                           |
| `templates/__init__.py`               | the two-layer template registry: `ALL_TEMPLATES` are parameterless shared singletons, `TEMPLATE_CLASSES` are the parameterized classes constructed by the instructions themselves |
| `tests/test_architecture.py`          | structural guard: instruction classes only declare identity and formula, and templates do not read back family data                                                               |
| `machine.py`                          | `MachineConfig` (N/UDS/M/ACC) and the named datatype domains                                                                                                                      |
| `registers.py`                        | M/ACC layout declarations and their strict parsing                                                                                                                                |
| `inputs.py`                           | stimulus recipes (integer ramps, packed square matrices, floating-point boundaries)                                                                                               |
| `reference.py`                        | exact expected values, cross-checked against `numeric_reference`                                                                                                                  |
| `float_formats.py`                    | power-of-two expected values for floating-point formats                                                                                                                           |
| `asm.py`                              | instruction-independent GAS emission primitives                                                                                                                                   |
| `macros.py`                           | parses datatypes from `src/ame_macros.inc`                                                                                                                                        |
| `__main__.py`                         | CLI: writes out the generated sources atomically and cleans up stale files it produced itself                                                                                     |

## How instructions declare themselves

Everything about what an instruction "is" lives in one file, as class attributes. There is no
dispatch table, no decorators and no import side effects:

```python
class MmulBtAcc2d(MatrixMultiplyInstruction):
    name = "mmulbtacc.2d"
    summary = "C = C + sum(A x transpose(B))"
    operands = PRODUCT_OPERANDS
    templates = (
        MATRIX_SMALL,
        FLOAT_PAIR_SWEEP,
        PACKED_SMALL,
        SATURATING_BOUNDARY,
        MIXED_SIGNEDNESS_MULTIPLE_SQUARE,
    )
    transposes_rhs = True
```

`name`, `summary` and `operands` say what it "is"; `templates` says how it is checked. Datatype
coverage is **not** declared a second time: every template owns the machine-dependent datatype
domain it iterates over (`INTEGER`, `INTEGER128`, `SATURATING_INTEGER`, `PACKED_INTEGER`,
`SOFTFLOAT`, `SIGNED_PACKED_SOURCE`), and the instruction exposes two derived views:

- `datatype_domains` — the domains its templates cover, in declaration order;
- `supported_dtypes(machine)` — the result of expanding those domains under a concrete N/UDS
  configuration and applying the resource predicates.

`--list` prints both, so coverage can be inspected without a second source of truth that might
drift. It also prints `input_cases`: all the input cases (by name) that each instruction runs, read
from the `templates` it constructs — templates that declare a list (such as
`GatherScatterIndexed`) report their own labels, while elementwise reports the list it hands to the
integer scenarios; both have exactly one declaration site: the input case list is written once, in
the template that declares it, and each case's own comment is written once too.

Inputs are also fully written out in the instruction class: the four generic integer cases are
`BASE_INTEGER_INPUT_CASES` (written once in the family base class), and instructions with an
overflow case compose it in with `BASE_INTEGER_INPUT_CASES + (overflow(...),)`, so opening any
instruction file shows the complete list of inputs it runs (see
[`instructions/README.md`](instructions/README.md)).

The elementwise family writes its templates out directly: each of the 46 instructions lists its
`templates`, and every template **carries its values at construction time** (integer list,
saturation recipe, softfloat nominal answer, ...), and the order of the list is the order of the
scenario sections in the source. There is no filtering step — what is written into the list is what
runs, and what is not written does not exist — so opening an instruction file shows which checks it
takes part in and what each check receives, while `--list` reports the number of scenarios each
instruction actually renders (between 2 and 7, not the same number for every instruction).

Semantic differences (`transposes_lhs`, `transposes_rhs`, `negates_product`) are flags rather than
mnemonic strings, so no template ever inspects a mnemonic prefix.

**What it computes** is also written in the instruction. Integer elementwise instructions declare
one method:

```python
    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B`` when ``A >= 0``, else ``D`` keeps its value; the M form
        shares ``D`` and ``A``."""

        return elements.rhs if elements.lhs >= 0 else elements.dest
```

It returns the **exact result**, which `integer_expected` re-encodes to the element width;
`elements` has already translated the operand form into `lhs`/`rhs`/`dest` (including the `_raw` bit
reads and `mask`), so the M form and the scalar form write the formula the same way. This formula is
**handed to both integer templates as an argument**
(`ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate)`); the templates hold it and
`integer_expected` calls it, so forgetting to pass it raises a `TypeError` at class-definition time;
`mmul_gen/tests/test_elementwise_declared_evaluation.py` then aligns it point by point,
exhaustively, with the shared oracle `numeric_reference`. For the full vocabulary see
[`instructions/README.md`](instructions/README.md).

Floating point follows the same idea, only the body of the function differs: the class declares an
additional `evaluate_float(dtype_name, element_bits)`, handed to `ElementwiseFloatNominal`; the body
is usually a one-line table lookup (`FLOAT_OPERATION_VALUES`; comparison classes return all ones or
0). So "`evaluate` must be computed" does not hold — **what the template holds is "how to obtain the
expected value": arithmetic for integers, a table lookup for floating point**. The other two
floating-point cells (special values, rounding) have no "single answer" — each is dozens or
hundreds of cases — and what the instruction declares there is a role, not `evaluate_float`.

`gen(machine)` is the only method the generator calls; `evaluate` is the formula declared by integer
instructions and held by the integer templates; the other families do not have it.
`gen` walks the declared templates and hands each rendered case to `_TestProgram`, which handles the
accumulation of `.text`/`.data` and the file skeleton.

## How templates declare themselves

`Template` is the generator's main class type. A template is a loop: the datatype domain it
iterates, the cases it builds for each datatype, and how it renders those cases. Every template
lives in its own module, as a subclass:

```python
class PackedSmall(Template):
    """Sub-UDS packed integer source widened into a whole-register product."""

    name = "packed_small"
    dtypes = PACKED_INTEGER

    def build(self, machine, instruction, dtype) -> list[Case]: ...
    def render(self, machine, instruction, case, out) -> None: ...
```

- The class docstring **is** the template's summary; `--list` reads it from there, so there is no
  second `summary` field that could drift.
- `build` computes operand values, expected values and register layout, and produces no assembly.
- `render` emits assembly from the typed case payload, never recomputes expected values and never
  re-reads the datatype table.
- `fits(machine, dtype)` is the resource predicate, defaulting to "always fits"; override it only
  when the template needs more than one M register span.
- Every case payload is a frozen dataclass (`PackedPayload`, `SaturatingPayload`,
  `FloatOverflowPayload`, ...) rather than a string-keyed dictionary; renderers assert the payload
  type they receive.

`Case` carries the parsed `RegisterLayout`, so the generated `M layout` / `ACC layout` comments are
emitted uniformly by the program builder instead of being written by every template. A layout that
does not fit the current register file is **skipped**, never silently re-laid out.

### Reusing templates through inheritance

Inheritance applies to templates that are "almost another template", not to instructions.
`ones_uniform_128` is `ones_uniform` acting on a wider domain, so it inherits the case builder and
overrides only what genuinely differs:

```python
class OnesUniform128(OnesUniform):
    """All-ones 128-bit integer product spanning several M registers."""

    name = "ones_uniform_128"
    dtypes = INTEGER128

    def fits(self, machine, dtype) -> bool:
        return two_register_groups_fit(machine, dtype)

    def render(self, machine, instruction, case, out) -> None: ...
```

By contrast, instructions **compose** templates rather than inheriting them: the 6 matrix multiply
instructions share `float_pair_sweep`, `packed_small`, `saturating_boundary` and
`mixed_signedness_multiple_square`, 5 share `matrix_small`, and only `mmulacc.2d` additionally uses
`ones_uniform`, `ones_uniform_128` and `multi_acc_independent`. Shared instances are never copied —
that is exactly why `packed_small` is written once yet appears in 6 generated sources, instead of
being written again in each of 6 instruction files.

## Adding an instruction

1. Add `instructions/<family>/<mnemonic>.py` with the subclass and the templates it covers (reuse
   existing template lists by reference, do not copy them).
2. Register the class in `instructions/__init__.py`.
3. Add the instance to `MATRIX_MULTIPLY_INSTRUCTIONS` in `catalog.py`.

No existing instruction file needs any change.

## Coverage

For every instruction, `--list` prints the exact datatypes, operands and templates. These templates
cover all the configurations the generated suite needs:

| Template                            | Covers                                                                                   |
| ----------------------------------- | ---------------------------------------------------------------------------------------- |
| `ones_uniform` / `ones_uniform_128` | whole-register and cross-register all-ones products (the latter inherits the former)     |
| `matrix_small`                      | position-dependent small matrix products, including transpose and negation variants      |
| `float_pair_sweep`                  | exactly representable products, plus an overflow sweep over signs × the 6 rounding modes |
| `packed_small`                      | sources narrower than the UDS, widened on write-back, for 4/8/16-bit storage             |
| `saturating_boundary`               | the `1 x max` that must raise `amexsat` and saturate                                     |
| `multi_acc_independent`             | seed, accumulate and read back each legal accumulator independently                      |
| `mixed_signedness_multiple_square`  | two packed square matrices differing in both sign and value                              |

The generator runs over all 120 configurations of `N ∈ {4,8,16,32}` × `UDS ∈ {8,16,32}` ×
`M ∈ {16,32}` × `ACC ∈ {1,2,4,8,16}`, one static N form per instruction per configuration. All 141
instructions generate source files across these 120 configurations and are verified byte for byte
(the difference comes from `debug_move`, `matrix_ops`, `acc_span` and `elementwise`, where in narrow
configurations the whole source is not generated).

What needs to be distinguished is this: the 120 is the **configuration space over which the
generator is exercised**, not "every template runs in every configuration". Whether a given template
takes part in a given configuration is decided by its `fits` predicate, so the participating range
differs between templates: `ones_uniform_128` needs two M register spans and
`multi_acc_independent` needs at least two accumulators. Cases that do not fit are skipped, never
silently re-laid out.

Datatype coverage per template, UDS 8/16/32:

- integer: all non-saturating `AME_{UINT,INT}{4,8,16,32,64,128}` descriptors that make up a full
  M register (128-bit covered only by `mmulacc.2d`);
- saturating: all `AME_*_SAT` integer descriptors;
- floating point: `E4M3`, `E5M2`, `FP16`, `BF16`, `FP32`, `FP64`;
- packed: all integer descriptors whose storage width is narrower than the current UDS;
- mixed sign: signed descriptors half the width of the current UDS.

## Verification

```sh
# Unit tests: directory catalog, datatype domains, register layout, end-to-end rendering,
# local label uniqueness, and that the hashes of the emitted assembly under 5 configurations
# match the frozen catalog.
python3 -m mmul_gen.tests
```

`tests/golden_sources.json` freezes the SHA-256 of the emitted assembly for 5 configurations (701
sources), normalizing the `Auto-generated by ...` attribution comment before comparison. A template
change that affects the emitted result fails here, and the byte-level constraint does not depend on
a second copy of the generator existing in the tree.

Matching hashes only prove that "the emitted result did not change", not that "it runs". These
source files compile and pass:

```sh
python3 test/ztt/run_ztt_tests.py --sim build/c_emulator/sail_riscv_sim
```

### One binary per N

The generator generates source files for the selected N, and `run_ztt_tests.py` builds and runs the
binary for that same N, so expected values are computed by the Python reference implementation and
emitted directly into the source file, and are not recomputed inside the test. To cover multiple N
values, generate one source file per N.

## Reused repository modules

`mmul_gen` reuses the repository's single sources of truth for ISA reference data:

- `fp_semantics` — IEEE/OCP boundary encodings, rounding modes, exception flags;
- `numeric_reference` — cross-checked exact integer matrix products;
- `generator_types` — `DType` descriptors.
