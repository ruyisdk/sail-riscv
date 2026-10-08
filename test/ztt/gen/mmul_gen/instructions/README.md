# Instruction declarations (`mmul_gen/instructions`)

One instruction = one file. The file name is the mnemonic with the lowercase dots and hyphens
replaced by underscores (`mcmovge.ew` → `mcmovge_ew.py`); the file contains one class, whose name is
the camel-cased mnemonic (`McmovgeEw`).

## Opening an instruction file should show the instruction itself

A pure integer instruction only declares its form, its formula, and the two templates that run the
integer checks:

```python
class McmovgeEw(ElementwiseInstruction):
    """Conditional move when greater-or-equal of two matrix operands into the destination."""

    name = "mcmovge.ew"
    summary = "conditional move when greater-or-equal of two matrix operands into the destination"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.TERNARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = B`` when ``A >= 0``, else ``D`` keeps its value; the M form
        shares ``D`` and ``A``."""

        return elements.rhs if elements.lhs >= 0 else elements.dest

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )
```

An instruction writes out all of its templates, and each template carries the values it checks at
construction time. Both template families take a **function**: the integer templates take the list
and the formula `evaluate`, and the floating-point nominal template takes `evaluate_float`. The
functions are defined before the list because they are this instruction's own methods, and they must
have a name before they can be passed as an argument:

```python
class MaddEw(ElementwiseInstruction):
    """Add of two matrix operands."""

    name = "madd.ew"
    summary = "add of two matrix operands"
    subject = "elementwise test cases."
    operands = ()
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        """``D = A + B`` element by element."""

        return elements.lhs + elements.rhs

    def evaluate_float(self, dtype_name: str, element_bits: int) -> int:
        """The softfloat model's nominal ``add`` operand is this instruction's answer."""

        return FLOAT_OPERATION_VALUES[dtype_name]["add"]

    #: Every template this instruction runs, in the order its cases appear.
    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.ADD, downward=False),
        ), evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES + (
            overflow(IntegerInputKind.ADD, downward=False),
        ), evaluate),
        ElementwiseSaturatingBoundary(
            SaturatingExpectation.MAX,
            CasePlan(vector_operands("max", "one"), ZERO, (ZERO, SOURCE)),
        ),
        ElementwiseSaturatingBoundary128(
            SaturatingExpectation.MAX,
            CasePlan(vector_operands("max", "one"), ZERO, (ZERO, SOURCE)),
        ),
        ElementwiseFloatNominal(evaluate_float),
        ElementwiseFloatSpecialValues(FloatArithmeticRole.ADD),
        ElementwiseFloatSemanticsSweep(FloatArithmeticRole.ADD),
    )
```

## How an instruction hands arguments to templates

Family base classes **reserve no optional slots**: behavior an instruction does not have simply does
not exist. Nor is there a layer where values are declared first and the framework then filters
scenarios out by name — **a template receives its values at construction time**, and the
instruction lists the templates it wants to run one by one in `templates`:

```python
class MandEw(ElementwiseInstruction):        # pure integer instruction, only integer checks
    form = ElementwiseForm.BINARY_M

    def evaluate(self, elements: IntegerElements) -> int:
        return elements.lhs & elements.rhs

    templates = (
        ElementwiseIntegerValueRules(BASE_INTEGER_INPUT_CASES, evaluate),
        ElementwiseIntegerValueRules128(BASE_INTEGER_INPUT_CASES, evaluate),
    )
```

Every template receives "**how to obtain the expected value**", and it is always a function written
in the class: the integer templates take `evaluate`, and the floating-point nominal template takes
`evaluate_float` — whose body is usually a single table lookup (`FLOAT_OPERATION_VALUES`), with
comparison classes returning all ones or 0. The other two cells receive a role rather than a
function: the special-value and rounding cells each hold dozens or hundreds of cases (the same
operand pair across 6 rounding modes, or across special operands such as NaN/±0/infinity), which no
function of the form "return one number for one operation" can hold, so what the instruction
declares there is "**which group of cases to apply**".

The class body reads as "which templates this instruction runs and what each template checks": a
template that is not listed does not exist on it and therefore does not run, so `templates` is its
complete check list. The list is written in the order of the scenario sections in the source; the
two 128-bit templates (the two classes ending in `...128`) follow their respective roots and receive
the same values. A misspelled class name raises a `NameError` on the spot; a wrong value type is
reported by the type checker on the construction line. Wrong ordering, or a missing 128-bit template,
is verified instruction by instruction by `test_elementwise_template_table_parity.py`.

| Declaration                    | Meaning                                                                                                        | Who reads it                                                                             |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `name` / `summary` / `subject` | mnemonic and documentation attributes                                                                          | `catalog`, `--list`                                                                      |
| `form`                         | operand form (`BINARY_M` / `BINARY_X` / `TERNARY_M` / `TERNARY_X` / `MOVE_M` / `UNARY_ABS`)                    | all 7 scenarios (integer operand reads, emitter plan selection, floating-point dispatch) |
| `evaluate`                     | **the exact result this instruction computes on one element**; handed to both integer templates as an argument | the templates hold a copy of it, and `integer_expected` uses it to compute each case     |
| `templates`                    | **the templates this instruction runs, in source order**, each carrying the values it checks                   | the driver builds cases template by template following this list                         |

The five scenario classes that can appear in `templates`, and what to pass when constructing them:

| Scenario class                   | Constructor arguments (listed directly in `__init__`)                                                                    |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `ElementwiseIntegerValueRules`   | **the integer input case list** (in the order the cases are emitted in the source) + this instruction's `evaluate`       |
| `ElementwiseSaturatingBoundary`  | `SaturatingExpectation` (which end to clamp to) + `CasePlan` (which blocks push it there)                                |
| `ElementwiseFloatNominal`        | this instruction's `evaluate_float`; comparison classes additionally pass `comparison=True`                              |
| `ElementwiseFloatSpecialValues`  | arithmetic classes pass `FloatArithmeticRole`, comparison classes pass `FloatSpecialRole.COMPARE_TRUE` / `COMPARE_FALSE` |
| `ElementwiseFloatSemanticsSweep` | `FloatArithmeticRole` (the invalid-operation vector)                                                                     |

Each scenario receives **its own constructor arguments**, with no wrapper types: the saturating pair
takes an expectation and an operand plan, and the special-value scenario takes a single role —
`FloatArithmeticRole` (the invalid-operation vector) or `FloatSpecialRole` (special-case behavior,
where the two comparison outcomes each have their own member, so "whether the comparison holds"
needs no second optional argument). One template, one value, so the "or" relationship of "the
special-value scenario might read `special`, or might read `role`" no longer exists: the single
value the instruction passes to it states what it is (none of the 46 instructions needs both). The
two 128-bit ones belong to the same pair and must have the same values —
`test_elementwise_template_table_parity.py` verifies that both the expectation and the plan match.

**How to read a class**: take `madd.ew`. AME has no hardware floating point; floating-point
semantics are provided by the software model `fp_semantics.py` — it stores a set of nominal bit
patterns for every floating-point dtype (under E4M3, `a`=0x3C, i.e. 1.5, `b`=0x40, i.e. 2.0, and
`add`=0x46, i.e. 3.5). The softfloat scenario is exactly this: load `a`/`b` as FP8/FP16, run
`madd.ew`, and compare bit by bit whether the result is `FLOAT_OPERATION_VALUES[DTYPE]["add"]`. So
the `def evaluate_float(...)` in the class reads as "**this instruction's softfloat nominal answer
is the `add` entry in the table**", and the template line
`ElementwiseFloatNominal(evaluate_float)` simply hands it over; the same
`FloatArithmeticRole.ADD` appears in both the special-value scenario and the rounding sweep entry
(they are the invalid-operation vectors of ADD), and the two entries sit side by side, directly
visible in the instruction class. `madd.ew` is both integer addition and, in this test suite,
softfloat addition. The fastest way to tell whether an instruction supports floating point is
`python3 -m mmul_gen --list`: `madd.ew` lists 3 softfloat scenarios, the `formed_softfloat` domain
and the six dtypes FP16/BF16/FP32/FP64/E4M3/E5M2.

Not being written into `templates` means **that behavior does not exist** and the corresponding
template does not run — that is how a family expresses "this instruction does not have this case".
The vocabulary does not go wrong silently: a misspelled class name is a `NameError`, and entries in
`templates` must be one of the seven scenario classes
(`mmul_gen/tests/test_elementwise_declarations.py`). The whole architecture is guarded by
`mmul_gen/tests/test_architecture.py`: the classes of **all 141 instructions** may have no members
other than identity, formula and elementwise's own `form`, and no template may read back family data
— including hiding a name with `getattr(instruction, "…")`. The real backstop is still the
byte-for-byte comparison across the 120 configurations.

The integer list is also a template argument, written as a composition: the four generic cases
(`small_values` / `boundaries` / `power_of_two` / `bit_patterns`) are family-wide invariants, and
`BASE_INTEGER_INPUT_CASES` is written once in the family base class; instructions with an overflow
case append it, and those without it write only `BASE_INTEGER_INPUT_CASES`, so opening any
instruction file shows **all** the inputs it runs.
`overflow(kind, downward=...)` decides the **operand pair** of the overflow case and which end
`dest` takes, and the two cannot be derived from each other (`mmulsub` uses the multiply recipe yet
lands on floor), so both are declared by the instruction. The 128-bit scenario narrows the scalar
form down to the single `small_values` entry; that is a scenario rule, not an instruction fact, and
it lives in `integer_cases()`. The integer scenario has no "always on" special case either: the list
is exactly the argument it receives at construction time. `templates` is a required declaration
(`Instruction.__init_subclass__` requires it to be non-empty at class-definition time); forgetting
the integer entry is caught by the parity test and by `input_case_names` (which raises when no
integer template is found). The `input_cases` printed by `python3 -m mmul_gen --list` is another way
of asking the same fact: `Instruction.input_case_names` asks the templates it constructed
(`Template.input_cases`), so the list is written only in `templates`, and there is no second
declaration on the instruction class that could drift.

## The `evaluate` contract

- It returns the **exact result**, which may exceed the element width. Re-encoding to the width
  (`convert_result`) is the job of `integer_expected`, so no declaration has to take the modulus
  itself, and no overflow wrap-around is missed.
- The `elements` argument translates **form** into **role**:
  - `lhs` / `rhs` / `dest`: architectural values, already read back at the element width;
  - `lhs_raw` / `rhs_raw`: the same bits read as unsigned (this is what the bit-manipulation
    instructions use);
  - `mask`: all ones at the element width, i.e. the "true" a comparison instruction must produce.
- For the scalar form (`.x`), `lhs` is that scalar, and for the ternary M form, `dest` and `lhs` are
  the same block. Therefore the same formula is written identically in `madd.ew` and `madd.ew.x`,
  and the difference is carried entirely by `form`.
- Every integer elementwise instruction **must** declare it, and **must hand it to both integer
  templates**: the templates store it at construction time, and `integer_expected` calls the copy
  the template holds. So forgetting to pass it is a `TypeError` at class-definition time (one
  positional argument missing), and passing a different function is verified instruction by
  instruction by
  `test_elementwise_declared_evaluation.py::test_every_instruction_hands_its_formula_to_both_integer_templates`,
  which checks that "what the two templates hold is exactly the function declared in the class". The
  other checks on class names, values and ordering live in `test_elementwise_declarations.py` and
  `test_elementwise_template_table_parity.py` rather than hidden in an `__init_subclass__` hook:
  they are visible from the instruction file, and they report all violations at once. No default
  implementation is left here — an instruction that "passes the tests without writing a formula" is
  unacceptable.
- Floating-point nominal follows the same path: the class declares
  `def evaluate_float(self, dtype_name, element_bits) -> int` and hands it to
  `ElementwiseFloatNominal`. The body is usually a one-line table lookup
  (`FLOAT_OPERATION_VALUES[dtype_name]["add"]`; comparison classes return
  `(1 << element_bits) - 1` or 0), so **`evaluate` does not have to be computed**; forgetting to pass
  it likewise raises a `TypeError` at class-definition time, and passing the wrong one is verified
  instruction by instruction by
  `test_elementwise_declared_evaluation.py::test_every_instruction_hands_its_float_formula_to_its_nominal_template`,
  which checks that "what the nominal scenario holds is exactly the function in the class".
- `evaluate_float` covers only the nominal cell (one answer per dtype). The special-value and
  rounding cells have no "single answer" and return a case vector, and the instruction declares a
  role there — see the table in the previous section.
- Consistency between the declarations and the shared oracle `numeric_reference` is guarded point by
  point, exhaustively, by `mmul_gen/tests/test_elementwise_declared_evaluation.py` (the full 4-bit
  cube + all 8-bit pairs, for both signs); any inconsistency is a test failure. `numeric_reference`
  is the reference implementation shared by expected-value computation and the byte-for-byte
  comparison.

## Family conventions

- `instructions/<family>/base.py` holds the family base class and the enums;
  `<family>/__init__.py` contains only a docstring; each concrete instruction occupies its own file.
- Instruction files import the declaration vocabulary (`ElementwiseForm`, `IntegerElements`,
  `FLOAT_OPERATION_VALUES`, `FloatSpecialRole`, etc.) from `<family>.base` and take it from nowhere
  else.
- Adding an instruction = add one file + register the class in `instructions/__init__.py` + hook the
  instance into the family list in `mmul_gen/catalog.py`; no existing instruction file needs
  changing, and the scenario table does not need touching — unless it brings a **new behavior**, in
  which case one row is added to the table.
- Shared modules may provide machinery, but **must not branch on instruction names**: this is
  guarded by an invariant in `mmul_gen/tests/test_complexity_budget.py`.
