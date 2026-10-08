#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Export the generated tables and appendices of the Ztt test design document.

The script reads the generator's own declarations (``mmul_gen/catalog.py``,
``mmul_gen/machine.py``, ``mmul_gen/templates/``, ``mmul_gen/instructions/``)
and one real generation pass, then writes the main test-design document and the
definition-level data appendix (template x datatype) with real assembly
excerpts.  Both are Chinese deliverables under the repository's ``doc/``
directory; their file names and their prose come from
``doc/appendix_zh_layout.py`` and ``doc/ztt_case_text_zh.json``, because this
repository is English-only and the delivered wording has to live somewhere the
documents own.

Every number, datatype name, template name, and assembly line in the generated
regions comes from the generator or from the generated ``.S`` sources.  The
script is deterministic and idempotent: running it twice yields identical
files.  It fails loudly (naming the offending module, template, instruction,
or case) rather than emitting a placeholder.

Usage (from the repository root or from this directory)::

    python3 sail-ame/test/ztt/gen/export_design_appendix.py
    python3 export_design_appendix.py            # cwd = sail-ame/test/ztt/gen
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import re
import sys
import tempfile
import types
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, fields, is_dataclass, replace
from pathlib import Path

# Importing the generator must not leave bytecode caches in the source tree.
sys.dont_write_bytecode = True

SCRIPT_PATH = Path(__file__).resolve()
GEN_DIR = SCRIPT_PATH.parent
REPO_ROOT = GEN_DIR.parents[3]
if str(GEN_DIR) not in sys.path:
    sys.path.insert(0, str(GEN_DIR))

from mmul_gen.asm import asm_header  # noqa: E402
from mmul_gen.catalog import ALL_INSTRUCTIONS, INSTRUCTION_FAMILIES  # noqa: E402
from mmul_gen.instruction import Instruction  # noqa: E402
from mmul_gen.macros import parse_dtypes  # noqa: E402
from mmul_gen.machine import ALL_DOMAINS, DTypeDomain, MachineConfig  # noqa: E402
from mmul_gen.templates.base import CaseOutput, Template  # noqa: E402

TEST_DIR = GEN_DIR.parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import run_ztt_tests  # noqa: E402

TEMPLATES_DIR = GEN_DIR / "mmul_gen" / "templates"
CATALOG_PATH = GEN_DIR / "mmul_gen" / "catalog.py"
DEFAULT_MACRO_FILE = GEN_DIR.parent / "src" / "ame_macros.inc"

#: The delivered documents are Chinese; this repository is English-only, so the
#: prose they are written in lives beside them.  ``doc`` is imported rather than
#: transcribed: a fragment the document needs and does not find raises.
DOC_DIR = REPO_ROOT / "doc"
if str(DOC_DIR) not in sys.path:
    sys.path.insert(0, str(DOC_DIR))

import appendix_zh_layout as zh  # noqa: E402

#: Where the Chinese prose of every generator declaration is stored, keyed by
#: the identifier it was declared under.  A missing or empty entry fails rather
#: than falling back to the declaration's English text or to a placeholder.
CASE_TEXT_PATH = DOC_DIR / "ztt_case_text_zh.json"

MAIN_DOC = DOC_DIR / zh.MAIN_DOC_NAME
DATA_DOC = DOC_DIR / zh.DATA_DOC_NAME

#: The tables ``CASE_TEXT_PATH`` must carry.  ``case_description_text`` is added
#: by the export that moved the prose out of this repository.
CASE_TEXT_TABLES = (
    "instruction_summary",
    "template_summary",
    "module_doc",
    "domain_description",
    "case_description",
    "input_case_description",
    "manual_zh",
    "case_description_text",
    "case_description_prefix",
)

#: The single source of the Chinese rendering of every manual instruction
#: block.  One entry per manual mnemonic; a missing or empty entry fails rather
#: than falling back to the English manual text.
MANUAL_TEXT_PATH = DOC_DIR / "instruction_manual_zh.json"

#: The authoritative manual.  The narrative blocks of section 4 are read from
#: these files at generation time; no manual fact is transcribed by hand.
MANUAL_SRC = REPO_ROOT / "riscv-attached-matrix-extension" / "src"
MANUAL_INSTRUCTIONS = MANUAL_SRC / "instructions.adoc"
MANUAL_ENCODING = MANUAL_SRC / "instruction-encoding-allocations.adoc"

_CASE_TEXT_CACHE: dict[str, dict[str, str]] | None = None


def case_text() -> dict[str, dict[str, str]]:
    """The delivered Chinese prose, read once from ``CASE_TEXT_PATH``."""

    global _CASE_TEXT_CACHE
    if _CASE_TEXT_CACHE is None:
        if not CASE_TEXT_PATH.is_file():
            fail(
                f"{CASE_TEXT_PATH} is missing; the delivered Chinese prose has no source"
            )
        payload = json.loads(CASE_TEXT_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            fail(f"{CASE_TEXT_PATH} must hold a JSON object")
        for name in CASE_TEXT_TABLES:
            table = payload.get(name)
            if not isinstance(table, dict) or not table:
                fail(f"{CASE_TEXT_PATH}: {name!r} must be a non-empty object")
        _CASE_TEXT_CACHE = payload
    return _CASE_TEXT_CACHE


def require_chinese(table: str, key: str, what: str) -> str:
    """The delivered Chinese prose for one generator identifier, or a failure.

    There is deliberately no fallback to the identifier's English declaration:
    a missing Chinese entry is a defect in ``CASE_TEXT_PATH``, not something the
    exporter may paper over with a placeholder or with the text the document
    must not show.
    """

    entry = case_text()[table].get(key)
    text = entry.strip() if isinstance(entry, str) else ""
    if not text:
        fail(f"{what} has no Chinese text under {table!r} in {CASE_TEXT_PATH}")
    return text


def chinese_case_description(description: str) -> str:
    """The delivered Chinese rendering of one generated case description.

    The generator emits its ``# input:`` comments in English; the document keeps
    the wording it was delivered with, so the English text is the lookup key.

    Most descriptions are listed whole.  A few templates compose one around a
    configuration-dependent tail -- a dtype pair, a register span -- so those
    are listed as fragments and substituted; a description that no fragment
    touches fails rather than leaving English prose in the document.
    """

    table = case_text()["case_description_text"]
    entry = table.get(description)
    if isinstance(entry, str) and entry.strip():
        return entry.strip()
    rendered = description
    for english, chinese in case_text()["case_description_prefix"].items():
        rendered = rendered.replace(english, chinese)
    if rendered == description:
        fail(
            f"case description {description!r} has no Chinese text in "
            f"{CASE_TEXT_PATH}"
        )
    return rendered


# ---------------------------------------------------------------------------
# Fail-fast helper
# ---------------------------------------------------------------------------


def fail(message: str) -> None:
    raise RuntimeError(message)


# ---------------------------------------------------------------------------
# Source introspection
# ---------------------------------------------------------------------------


def module_path_to_name(path: Path) -> str:
    relative = path.resolve().relative_to(GEN_DIR)
    return ".".join(relative.with_suffix("").parts)


@dataclass(frozen=True)
class ModuleFacts:
    """AST facts about one template module, read without importing it."""

    path: Path
    name: str
    docstring: str
    description: str
    imports: dict[str, tuple[str, ...]]
    classes: tuple[str, ...]
    functions: tuple[str, ...]


def read_module_facts(path: Path) -> ModuleFacts:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    doc = ast.get_docstring(tree)
    if doc is None or not doc.strip():
        fail(f"module {path} has no docstring; every template module must document itself")
    name = module_path_to_name(path)
    imports: dict[str, list[str]] = defaultdict(list)
    classes: list[str] = []
    functions: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports[node.module].append(alias.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
    return ModuleFacts(
        path=path,
        name=name,
        docstring=doc.strip(),
        description=require_chinese("module_doc", name, f"template module {name!r}"),
        imports={key: tuple(value) for key, value in imports.items()},
        classes=tuple(classes),
        functions=tuple(functions),
    )


def build_module_facts() -> dict[str, ModuleFacts]:
    paths = sorted(TEMPLATES_DIR.glob("*.py"))
    if not paths:
        fail(f"no template modules found under {TEMPLATES_DIR}")
    facts = [read_module_facts(path) for path in paths]
    return {fact.name: fact for fact in facts}


DEFAULT_N = 8
DEFAULT_UDS = 8
DEFAULT_M = 32
DEFAULT_ACC = 4

#: How many lines of a real case an appendix excerpt keeps before it says how
#: many lines it dropped.  The omission is counted, never silent.
SNIPPET_LIMIT = 26
DATA_SNIPPET_LIMIT = 12

#: Template instances whose input/expect symbols are classified from the
#: module's imports.
_ASM_ASSERT_PREFIX = "check_"
_ASM_INPUT_HELPERS = frozenset(
    {
        "data_directive",
        "data_element_line",
        "data_element_lines",
        "dst_square_lines",
        "element_byte_values",
        "hex_value",
        "load_byte_lines",
        "pack_nibbles",
        "repeated_square_lines",
        "row_col_values",
        "sign_extend",
        "square_lines",
    }
)
_STIMULUS_MODULES = frozenset({"mmul_gen.inputs"})
_EXPECT_MODULES = frozenset(
    {"mmul_gen.reference", "mmul_gen.float_formats", "numeric_reference"}
)
_SEMANTIC_MODULES = frozenset({"fp_semantics"})

INSTANCE_INSTRUCTIONS = (
    "mmulacc.2d",
    "mmulaccneg.2d",
    "mmulatacc.2d",
    "mmulataccneg.2d",
    "mmulbtacc.2d",
    "mmulbtaccneg.2d",
)


# ---------------------------------------------------------------------------
# Source introspection


def build_import_graph(facts: dict[str, ModuleFacts]) -> dict[str, set[str]]:
    """Template-module -> template-modules it imports (for helper closure)."""

    known = set(facts)
    return {
        name: {module for module in fact.imports if module in known}
        for name, fact in facts.items()
    }


def importing_modules(graph: dict[str, set[str]], target: str) -> list[str]:
    """Every module that reaches ``target`` directly or transitively."""

    found: set[str] = set()
    frontier = {target}
    while frontier:
        current = frontier.pop()
        for module, imports in graph.items():
            if module in found or module == target:
                continue
            if current in imports:
                found.add(module)
                frontier.add(module)
    return sorted(found)


# ---------------------------------------------------------------------------
# Stable, compact rendering of generator values
# ---------------------------------------------------------------------------


def stable_repr(value: object, depth: int = 0) -> str:
    """A deterministic rendering of a generator value (never an address)."""

    if depth > 4:
        return "..."
    if value is None or isinstance(value, (int, float, bool, str)):
        return repr(value)
    if isinstance(value, (types.FunctionType, types.MethodType, types.BuiltinFunctionType)):
        return getattr(value, "__qualname__", repr(value))
    if isinstance(value, tuple):
        return "(" + ", ".join(stable_repr(item, depth + 1) for item in value) + ")"
    if isinstance(value, list):
        return "[" + ", ".join(stable_repr(item, depth + 1) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(
            f"{stable_repr(key, depth + 1)}: {stable_repr(value[key], depth + 1)}"
            for key in sorted(value, key=repr)
        ) + "}"
    if is_dataclass(value) and not isinstance(value, type):
        body = ", ".join(
            f"{field.name}={stable_repr(getattr(value, field.name), depth + 1)}"
            for field in fields(value)
        )
        return f"{type(value).__name__}({body})"
    rendered = repr(value)
    if " at 0x" in rendered:
        fail(
            f"cannot render {type(value).__name__} deterministically: {rendered!r}"
        )
    return rendered


def compact(value: object, max_items: int = 4, depth: int = 0) -> str:
    """A bounded rendering used inside table cells."""

    if depth > 3:
        return "..."
    if value is None or isinstance(value, (int, float, bool, str)):
        return repr(value)
    if isinstance(value, (types.FunctionType, types.MethodType, types.BuiltinFunctionType)):
        return getattr(value, "__qualname__", repr(value))
    if isinstance(value, (tuple, list)):
        items = list(value)
        if len(items) <= max_items:
            return "[" + ", ".join(compact(item, max_items, depth + 1) for item in items) + "]"
        head = ", ".join(compact(item, max_items, depth + 1) for item in items[:max_items])
        return zh.template("compact_items_more").format(head=head, count=len(items))
    if is_dataclass(value) and not isinstance(value, type):
        body = ", ".join(
            f"{field.name}={compact(getattr(value, field.name), max_items, depth + 1)}"
            for field in fields(value)
        )
        return f"{type(value).__name__}({body})"
    return stable_repr(value, depth)


def param_label(instance: object) -> str:
    """A short, deterministic label for one template instance's parameters."""

    attributes = {
        key: value for key, value in vars(instance).items() if not key.startswith("_")
    }
    if not attributes:
        return ""
    parts = []
    for key, value in attributes.items():
        if isinstance(value, (tuple, list)):
            parts.append(zh.template("param_list_items").format(key=key, count=len(value)))
        else:
            rendered = compact(value, max_items=3)
            if len(rendered) > 60:
                rendered = rendered[:57] + "..."
            parts.append(f"{key}={rendered}")
    return ", ".join(parts)


def merged_imports(
    data: DesignData, module_name: str
) -> dict[str, tuple[str, ...]]:
    """Imports of one module plus every template module it reaches.

    A family's template often delegates its data construction or its checks to a
    sibling ``*_common`` module, so the symbols that describe the template are
    the closure of its own imports.
    """

    modules = {module_name}
    frontier = {module_name}
    while frontier:
        current = frontier.pop()
        for module in data.graph.get(current, ()):
            if module not in modules:
                modules.add(module)
                frontier.add(module)
    merged: dict[str, list[str]] = defaultdict(list)
    for module in sorted(modules):
        for source, names in data.facts[module].imports.items():
            merged[source].extend(names)
    return {source: tuple(sorted(set(names))) for source, names in merged.items()}


def stimulus_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    names: list[str] = []
    for module in _STIMULUS_MODULES:
        names.extend(imports.get(module, ()))
    return tuple(sorted(set(names)))


def expect_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    names: list[str] = []
    for module in _EXPECT_MODULES:
        names.extend(imports.get(module, ()))
    return tuple(sorted(set(names)))


def semantic_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    names: list[str] = []
    for module in _SEMANTIC_MODULES:
        names.extend(imports.get(module, ()))
    return tuple(sorted(set(names)))


def asm_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(sorted(set(imports.get("mmul_gen.asm", ()))))


def input_helper_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(name for name in asm_symbols(imports) if name in _ASM_INPUT_HELPERS)


def check_helper_symbols(imports: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    return tuple(name for name in asm_symbols(imports) if name.startswith(_ASM_ASSERT_PREFIX))


# ---------------------------------------------------------------------------
# Case extraction
# ---------------------------------------------------------------------------

_ASSERT_RE = re.compile(r"^\s*(EXPECT|EXPECT_TRAP)\b")
_GUARD_RE = re.compile(r"^\s*(TRAP_GUARD_ARM|TRAP_GUARD_DISARM)\b")
_LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*):\s*$")
_LA_RE = re.compile(r"^\s*la\s+\w+,\s*([A-Za-z_][A-Za-z0-9_.]*)\s*$")
_INSN_RE = re.compile(r"^\s*([a-z][a-z0-9_.]*)\s")


@dataclass
class CaseRecord:
    instruction: str
    instruction_file: str
    number: int
    template_name: str
    template_module: str
    template_class: str
    param: str
    domain: str | None
    dtype: str | None
    description: str | None
    layout: str | None
    payload: object
    text_lines: tuple[str, ...]
    data_lines: tuple[str, ...]

    @property
    def assertions(self) -> tuple[str, ...]:
        return tuple(line.strip() for line in self.text_lines if _ASSERT_RE.match(line))


def label_digest(data_lines: tuple[str, ...] | list[str]) -> tuple[tuple[str, str], ...]:
    """One ``(label, body summary)`` pair per labelled data block."""

    blocks: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    for line in data_lines:
        match = _LABEL_RE.match(line)
        if match is not None:
            current = (match.group(1), [])
            blocks.append(current)
        elif current is not None and line.strip():
            current[1].append(line.strip())
    digest = []
    for label, body in blocks:
        if not body:
            fail(f"data label {label!r} has an empty body")
        repeated = next((line for line in body if line.startswith(".rept")), None)
        if repeated is not None:
            inner = body[body.index(repeated) + 1] if body.index(repeated) + 1 < len(body) else ""
            summary = f"{repeated.split()[1]} x `{inner}`"
        else:
            summary = body[0]
            if len(body) > 1:
                summary += zh.template("label_body_lines").format(count=len(body))
        digest.append((label, summary))
    return tuple(digest)


def assertion_digest(text_lines: tuple[str, ...] | list[str]) -> str:
    """A compact description of every ``EXPECT`` in one case body."""

    by_register: "OrderedDict[str, list[str]]" = OrderedDict()
    trap_values: list[str] = []
    for line in text_lines:
        stripped = line.strip()
        if stripped.startswith("EXPECT_TRAP"):
            trap_values.append(stripped.split(None, 1)[1] if " " in stripped else "")
            continue
        if not stripped.startswith("EXPECT"):
            continue
        body = stripped.split(None, 1)[1] if " " in stripped else ""
        register, _, value = body.partition(",")
        register = register.strip()
        value = value.strip()
        bucket = by_register.setdefault(register, [])
        if value not in bucket:
            bucket.append(value)
    parts = []
    for register, values in by_register.items():
        shown = ", ".join(values[:6])
        if len(values) > 6:
            shown += zh.template("assertion_values_more").format(count=len(values))
        parts.append(f"`{register}`: {shown}")
    if trap_values:
        parts.append(
            zh.template("assertion_trap_register").format(values=", ".join(trap_values))
        )
    if not parts:
        guards = tuple(line.strip() for line in text_lines if _GUARD_RE.match(line))
        if guards:
            return zh.template("assertion_guards_only").format(
                guards=zh.ENUM_SEPARATOR.join(f"`{guard}`" for guard in guards)
            )
        fail("case body carries no EXPECT/EXPECT_TRAP assertion")
    return zh.CLAUSE_SEPARATOR.join(parts)


def first_asserting_case(cases: tuple[CaseRecord, ...]) -> CaseRecord | None:
    return next((case for case in cases if case.assertions), None)


def assertion_anchor(text_lines: tuple[str, ...] | list[str]) -> str:
    """What immediately precedes the first assertion of a case body."""

    lines = list(text_lines)
    first = next(
        (index for index, line in enumerate(lines) if _ASSERT_RE.match(line)), None
    )
    if first is None:
        fail("case body carries no assertion to anchor")
    anchor = zh.text("anchor_case_body_start")
    for index in range(first - 1, -1, -1):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _INSN_RE.match(lines[index])
        anchor = match.group(1) if match else stripped
        break
    label = zh.text("none")
    for index in range(first - 1, -1, -1):
        match = _LA_RE.match(lines[index])
        if match is not None:
            label = match.group(1)
            break
    return zh.template("anchor_with_data_label").format(anchor=anchor, label=label)


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass
class TemplateInstanceRecord:
    key: str
    name: str
    module: str
    class_name: str
    param: str
    summary: str
    domain_name: str | None
    domain_description: str | None
    domain_dtypes: tuple[str, ...]
    input_cases: tuple[str, ...]
    users: tuple[str, ...]
    cases: tuple[CaseRecord, ...]

    @property
    def first_case(self) -> CaseRecord | None:
        return self.cases[0] if self.cases else None


@dataclass
class InstructionRecord:
    name: str
    summary: str
    family: str
    file_name: str
    class_name: str
    class_module: str
    source_path: str
    source_line: int
    base_module: str
    template_keys: tuple[str, ...]
    supported_dtypes: tuple[str, ...]
    cases_by_template: "OrderedDict[str, tuple[CaseRecord, ...]]"
    total_cases: int

    @property
    def cases(self) -> tuple[CaseRecord, ...]:
        return tuple(
            case for cases in self.cases_by_template.values() for case in cases
        )


@dataclass
class DesignData:
    machine: MachineConfig
    facts: dict[str, ModuleFacts]
    graph: dict[str, set[str]]
    instructions: tuple[InstructionRecord, ...]
    instances: tuple[TemplateInstanceRecord, ...]
    source_lines: int
    source_bytes: int

    @property
    def instances_by_key(self) -> dict[str, TemplateInstanceRecord]:
        return {instance.key: instance for instance in self.instances}


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def instance_key(template: Template) -> str:
    return f"{type(template).__module__}.{type(template).__name__}#{param_label(template)}"


def instance_key_of(record: CaseRecord) -> str:
    return f"{record.template_module}.{record.template_class}#{record.param}"


def _render_cases(
    machine: MachineConfig, instruction: Instruction
) -> tuple[list[CaseRecord], str]:
    """Render every case once, then require the per-case view to rebuild the source."""

    generated = instruction.gen(machine)
    if generated is None:
        fail(f"instruction {instruction.name!r} produced no source on this configuration")

    records: list[CaseRecord] = []
    index = 0
    for template, case in instruction.cases(machine):
        case = replace(case, number=index)
        index += 1
        output = CaseOutput()
        prefix: list[str] = []
        if case.description is not None:
            prefix.append(f"    # input: {case.description}")
        if case.layout is not None:
            prefix.extend(case.layout.comment_lines())
        template.render(machine, instruction, case, output)
        records.append(
            CaseRecord(
                instruction=instruction.name,
                instruction_file=instruction.file_name,
                number=case.number,
                template_name=template.name,
                template_module=type(template).__module__,
                template_class=type(template).__name__,
                param=param_label(template),
                domain=template.dtypes.name if isinstance(template.dtypes, DTypeDomain) else None,
                dtype=case.dtype.name if case.dtype is not None else None,
                description=case.description,
                layout=(
                    " / ".join(case.layout.comment_lines()).strip()
                    if case.layout is not None
                    else None
                ),
                payload=case.payload,
                text_lines=tuple(prefix + output.text),
                data_lines=tuple(output.data),
            )
        )

    rebuilt_lines = list(
        asm_header(
            instruction.banner(machine),
            acquire_backend=instruction.acquires_backend,
        )
    )
    for record in records:
        rebuilt_lines.extend(record.text_lines)
    rebuilt_lines.extend(["    RVMODEL_HALT_PASS", ""])
    footer = instruction.data_footer(machine)
    data_lines = [line for record in records for line in record.data_lines]
    if data_lines or footer or instruction.always_emits_data:
        rebuilt_lines.append(".data")
        rebuilt_lines.extend(data_lines)
        rebuilt_lines.extend(footer)
    rebuilt = "\n".join(rebuilt_lines)
    if rebuilt != generated.text:
        _report_source_mismatch(instruction, rebuilt, generated.text)
    return records, generated.text


def source_matches(stored: str | None, generated: str) -> bool:
    """``write_source`` normalises to exactly one trailing newline."""

    if stored is None:
        return False
    return stored == generated or stored == generated + "\n"


def _report_source_mismatch(instruction: Instruction, rebuilt: str, real: str) -> None:
    rebuilt_lines = rebuilt.split("\n")
    real_lines = real.split("\n")
    for index, (left, right) in enumerate(zip(rebuilt_lines, real_lines)):
        if left != right:
            fail(
                f"per-case reconstruction of {instruction.name!r} diverges at line {index + 1}: "
                f"rebuilt {left!r} vs generated {right!r}"
            )
    fail(
        f"per-case reconstruction of {instruction.name!r} has {len(rebuilt_lines)} lines, "
        f"generated has {len(real_lines)}"
    )


def collect_design_data(machine: MachineConfig, sources: dict[str, str]) -> DesignData:
    facts = build_module_facts()
    graph = build_import_graph(facts)

    instances: "OrderedDict[str, TemplateInstanceRecord]" = OrderedDict()
    instruction_records: list[InstructionRecord] = []

    for instruction in ALL_INSTRUCTIONS:
        records, generated_text = _render_cases(machine, instruction)
        if not source_matches(sources.get(instruction.file_name), generated_text):
            fail(
                f"generated source for {instruction.name!r} differs from the file written to "
                f"the scratch directory"
            )
        cases_by_template: "OrderedDict[str, tuple[CaseRecord, ...]]" = OrderedDict()
        for template in instruction.templates:
            key = instance_key(template)
            cases_by_template[key] = tuple(
                record for record in records if instance_key_of(record) == key
            )
        classified = sum(len(cases) for cases in cases_by_template.values())
        if classified != len(records):
            fail(
                f"instruction {instruction.name!r}: {len(records)} cases rendered but "
                f"{classified} classified by declared templates; a case belongs to no template"
            )

        for template in instruction.templates:
            key = instance_key(template)
            if key not in instances:
                domain = template.dtypes
                if domain is not None and not isinstance(domain, DTypeDomain):
                    fail(
                        f"template {template.name!r} declares a datatype domain that is not a "
                        f"DTypeDomain: {domain!r}"
                    )
                domain_dtypes = (
                    tuple(dtype.name for dtype in domain(machine)) if domain else ()
                )
                instances[key] = TemplateInstanceRecord(
                    key=key,
                    name=template.name,
                    module=type(template).__module__,
                    class_name=type(template).__name__,
                    param=param_label(template),
                    summary=require_chinese(
                        "template_summary",
                        f"{type(template).__module__}.{type(template).__name__}",
                        f"template {template.name!r}",
                    ),
                    domain_name=domain.name if domain else None,
                    domain_description=(
                        require_chinese(
                            "domain_description", domain.name, f"datatype domain {domain.name!r}"
                        )
                        if domain
                        else None
                    ),
                    domain_dtypes=domain_dtypes,
                    input_cases=tuple(template.input_cases),
                    users=(),
                    cases=(),
                )
            instance = instances[key]
            instances[key] = replace(
                instance, cases=tuple(instance.cases) + cases_by_template[key]
            )

        cls = type(instruction)
        try:
            source_path = inspect.getsourcefile(cls)
            _, source_line = inspect.getsourcelines(cls)
        except (OSError, TypeError) as error:
            fail(f"cannot locate source of instruction class {cls.__name__}: {error}")
        base = cls.__mro__[1]
        instruction_records.append(
            InstructionRecord(
                name=instruction.name,
                summary=require_chinese(
                    "instruction_summary", cls.__name__, f"instruction {instruction.name!r}"
                ),
                family="",
                file_name=instruction.file_name,
                class_name=cls.__name__,
                class_module=cls.__module__,
                source_path=(
                    str(Path(source_path).resolve().relative_to(GEN_DIR))
                    if source_path
                    else "<unknown>"
                ),
                source_line=source_line,
                base_module=base.__module__ if base is not Instruction else "mmul_gen.instruction",
                template_keys=tuple(instance_key(template) for template in instruction.templates),
                supported_dtypes=tuple(
                    dtype.name for dtype in instruction.supported_dtypes(machine)
                ),
                cases_by_template=cases_by_template,
                total_cases=len(records),
            )
        )

    users_by_key: dict[str, list[str]] = defaultdict(list)
    for record in instruction_records:
        for key in record.template_keys:
            users_by_key[key].append(record.name)
    for key, instance in list(instances.items()):
        instances[key] = replace(instance, users=tuple(users_by_key[key]))

    family_names_in_order = [
        family.name for family in INSTRUCTION_FAMILIES for _ in family.instructions
    ]
    if len(family_names_in_order) != len(instruction_records):
        fail(
            f"catalog family order lists {len(family_names_in_order)} instructions but "
            f"{len(instruction_records)} were collected"
        )
    final_records = tuple(
        replace(record, family=family_name)
        for record, family_name in zip(instruction_records, family_names_in_order)
    )
    return DesignData(
        machine=machine,
        facts=facts,
        graph=graph,
        instructions=final_records,
        instances=tuple(instances.values()),
        source_lines=sum(text.count("\n") for text in sources.values()),
        source_bytes=sum(len(text.encode("utf-8")) for text in sources.values()),
    )


# ---------------------------------------------------------------------------
# Assembly excerpts
# ---------------------------------------------------------------------------


def excerpt(lines: tuple[str, ...] | list[str], limit: int) -> list[str]:
    lines = list(lines)
    if len(lines) <= limit:
        return lines
    head = limit // 2
    tail = limit - head
    return [
        *lines[:head],
        zh.template("excerpt_omitted_lines").format(count=len(lines) - limit),
        *lines[-tail:],
    ]


#: A generated ``# input:`` comment, captured as (indent plus marker, text).
INPUT_COMMENT_RE = re.compile(r"^(\s*# input: )(.*)$")


def delivered_text_line(line: str) -> str:
    """One generated line as the delivered document shows it.

    The generated sources are English and the document is Chinese.  The one
    generated comment the document also states in Chinese is the ``# input:``
    case description, so that comment is rendered from the same doc-side table
    the rest of the prose comes from; every other line is the generated text
    verbatim.  An unmapped description fails rather than leaving English prose.
    """

    match = INPUT_COMMENT_RE.match(line)
    if match is None:
        return line
    return match.group(1) + chinese_case_description(match.group(2))


def delivered_excerpt(
    lines: tuple[str, ...] | list[str], limit: int
) -> list[str]:
    """The delivered rendering of one generated excerpt."""

    return excerpt([delivered_text_line(line) for line in lines], limit)


def fenced_asm(lines: list[str]) -> list[str]:
    return ["```asm", *lines, "```"]


def inline_list(values: tuple[str, ...], limit: int = 8) -> str:
    if not values:
        return ""
    if len(values) <= limit:
        return zh.ENUM_SEPARATOR.join(f"`{value}`" for value in values)
    return zh.ENUM_SEPARATOR.join(
        f"`{value}`" for value in values[:limit]
    ) + zh.template("inline_more").format(count=len(values))


def cell_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def combo_label(machine: MachineConfig) -> str:
    return f"n{machine.n}/u{machine.uds}/m{machine.num_m_regs}/a{machine.num_acc_regs}"


# ---------------------------------------------------------------------------
# Manual source
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManualInstruction:
    """One instruction's facts as the authoritative manual states them."""

    anchor: str
    mnemonic: str
    synopsis: str
    description: str
    operation: str
    common_rules: tuple[str, ...]
    encoding_format: str
    funct7: int
    funct3: int
    opcode: int
    match: int
    mask: int


_MANUAL_ANCHOR_RE = re.compile(r"^\[#ame:doc:inst:([A-Za-z0-9_]+)\]\s*$")
_MANUAL_HEADING_RE = re.compile(r"^=== `([^`]+)`\s*$")
_MANUAL_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z ]*)::\s*$")
_MANUAL_COMMON_RE = re.compile(r"<<(ame-common-[a-z-]+)>>")
_ENCODING_ATTR_RE = re.compile(r"^:([A-Za-z0-9-]+):\s*(0x[0-9a-fA-F]+|\d+)\s*$")
_WAVEDROM_RE = re.compile(r'^\{"reg":')
_ENCODING_FORMATS = {3: "R3", 2: "R2", 1: "R1", 0: "Fixed"}

_MANUAL_CACHE: dict[str, ManualInstruction] | None = None
_MANUAL_TEXT_CACHE: dict[str, str] | None = None


def manual_field(chunk: list[str], name: str) -> list[str]:
    """The lines of one ``Name::`` field, up to the next field or the block end."""

    start = next(
        (index + 1 for index, line in enumerate(chunk) if line.strip() == f"{name}::"),
        None,
    )
    if start is None:
        fail(f"manual block has no {name}:: field")
    end = len(chunk)
    for index in range(start, len(chunk)):
        if _MANUAL_FIELD_RE.match(chunk[index].strip()):
            end = index
            break
    return chunk[start:end]


def manual_text(lines: list[str]) -> str:
    """A field's prose with the AsciiDoc continuation markers removed."""

    kept = [line.strip() for line in lines if line.strip() and line.strip() != "+"]
    if not kept:
        fail("manual field is empty")
    return " ".join(kept)


def manual_code(lines: list[str]) -> str:
    """The body of the first ``----`` delimited block of a field."""

    inside = False
    body: list[str] = []
    for line in lines:
        if line.strip() == "----":
            inside = not inside
            continue
        if inside:
            body.append(line.rstrip())
    if not body:
        fail("manual field has no ``----`` code block")
    return "\n".join(body)


def manual_encoding_attributes() -> dict[str, int]:
    """The selector values the manual's encoding registry declares."""

    attributes: dict[str, int] = {}
    for line in MANUAL_ENCODING.read_text(encoding="utf-8").splitlines():
        match = _ENCODING_ATTR_RE.match(line.strip())
        if match is not None:
            attributes[match.group(1)] = int(match.group(2), 0)
    if "ame-enc-funct3" not in attributes:
        fail(f"{MANUAL_ENCODING} declares no ame-enc-funct3 selector")
    return attributes


def manual_encoding(chunk: list[str], attributes: dict[str, int]) -> dict[str, object]:
    """Decode one instruction's encoding from its wavedrom and the registry."""

    lines = manual_field(chunk, "Encoding")
    wavedrom = next((line.strip() for line in lines if _WAVEDROM_RE.match(line.strip())), None)
    if wavedrom is None:
        fail("manual Encoding field has no wavedrom block")
    for name, value in attributes.items():
        wavedrom = wavedrom.replace("{" + name + "}", str(value))
    # The manual writes its fixed selector values as C-style hex literals, which
    # JSON does not accept; every such literal is an unquoted number.
    wavedrom = re.sub(
        r"0x([0-9a-fA-F]+)", lambda match: str(int(match.group(0), 16)), wavedrom
    )
    try:
        payload = json.loads(wavedrom)
    except json.JSONDecodeError as error:
        fail(f"cannot parse the manual wavedrom encoding: {error}")
    fields = payload["reg"]
    total = sum(field["bits"] for field in fields)
    if total != 32:
        fail(f"manual encoding is {total} bits wide, not 32")
    # The manual's wavedrom lists its fields least-significant first.
    offset = 0
    fixed: dict[int, tuple[int, int]] = {}
    variable = 0
    mask = 0
    match = 0
    for field in fields:
        name = field["name"]
        if isinstance(name, int):
            fixed[offset] = (field["bits"], name)
            mask |= ((1 << field["bits"]) - 1) << offset
            match |= name << offset
        else:
            variable += 1
        offset += field["bits"]
    if variable not in _ENCODING_FORMATS:
        fail(f"manual encoding has {variable} variable register fields")
    for needed in (25, 12, 0):
        if needed not in fixed:
            fail(f"manual encoding has no fixed field at bit {needed}")
    return {
        "encoding_format": _ENCODING_FORMATS[variable],
        "funct7": fixed[25][1],
        "funct3": fixed[12][1],
        "opcode": fixed[0][1],
        "match": match,
        "mask": mask,
    }


def manual_instructions() -> dict[str, ManualInstruction]:
    """Every instruction block of the manual, keyed by mnemonic."""

    global _MANUAL_CACHE
    if _MANUAL_CACHE is not None:
        return _MANUAL_CACHE
    lines = MANUAL_INSTRUCTIONS.read_text(encoding="utf-8").splitlines()
    starts = [index for index, line in enumerate(lines) if _MANUAL_ANCHOR_RE.match(line)]
    if not starts:
        fail(f"{MANUAL_INSTRUCTIONS} declares no instruction blocks")
    attributes = manual_encoding_attributes()
    parsed: dict[str, ManualInstruction] = {}
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        chunk = lines[start:end]
        anchor = _MANUAL_ANCHOR_RE.match(chunk[0]).group(1)
        heading = next(
            (
                _MANUAL_HEADING_RE.match(line).group(1)
                for line in chunk[1:4]
                if _MANUAL_HEADING_RE.match(line)
            ),
            None,
        )
        if heading is None:
            fail(f"manual anchor {anchor!r} has no instruction heading")
        mnemonic_text = manual_text(manual_field(chunk, "Mnemonic"))
        mnemonic = re.search(r"`([^`]+)`", mnemonic_text)
        if mnemonic is None:
            fail(f"manual block {heading!r} has no backticked mnemonic")
        parsed[heading] = ManualInstruction(
            anchor=anchor,
            mnemonic=mnemonic.group(1),
            synopsis=manual_text(manual_field(chunk, "Synopsis")),
            description=manual_text(manual_field(chunk, "Description")),
            operation=manual_code(manual_field(chunk, "Operation")),
            common_rules=tuple(
                dict.fromkeys(_MANUAL_COMMON_RE.findall("\n".join(chunk)))
            ),
            **manual_encoding(chunk, attributes),  # type: ignore[arg-type]
        )
    _MANUAL_CACHE = parsed
    return parsed


def manual_instruction(name: str) -> ManualInstruction:
    parsed = manual_instructions()
    if name not in parsed:
        fail(f"the manual declares no instruction {name!r}")
    return parsed[name]


def manual_rendering_table() -> dict[str, str]:
    """The Chinese rendering of every manual instruction block.

    The table is the single source of the Chinese manual prose; a mnemonic the
    manual declares but the table does not render is a defect, not something the
    exporter may paper over with the English text.
    """

    global _MANUAL_TEXT_CACHE
    if _MANUAL_TEXT_CACHE is not None:
        return _MANUAL_TEXT_CACHE
    if not MANUAL_TEXT_PATH.is_file():
        fail(f"{MANUAL_TEXT_PATH} is missing; the Chinese manual renderings are required")
    raw = json.loads(MANUAL_TEXT_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        fail(f"{MANUAL_TEXT_PATH} must hold an object keyed by mnemonic")
    table: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str) or not value.strip():
            fail(f"{MANUAL_TEXT_PATH}: {key!r} has no Chinese rendering")
        table[key] = value.strip()
    missing = tuple(name for name in manual_instructions() if name not in table)
    if missing:
        fail(f"{MANUAL_TEXT_PATH} renders no manual text for {missing!r}")
    _MANUAL_TEXT_CACHE = table
    return table


# ---------------------------------------------------------------------------
# Instruction tables
# ---------------------------------------------------------------------------


def clause(text: str) -> str:
    """A summary used as one clause of a joined cell: drop the final period."""

    return text[: -len(zh.SENTENCE_END)] if text.endswith(zh.SENTENCE_END) else text


def cell_input_mode(imports: dict[str, tuple[str, ...]], instance: TemplateInstanceRecord) -> str:
    parts: list[str] = [clause(instance.summary)]
    if instance.input_cases:
        parts.append(zh.text("input_cases_label") + inline_list(instance.input_cases))
    stimulus = stimulus_symbols(imports)
    if stimulus:
        parts.append(zh.text("stimulus_label") + inline_list(stimulus))
    helpers = input_helper_symbols(imports)
    if helpers:
        parts.append(zh.text("data_construction_label") + inline_list(helpers))
    return cell_text(zh.CLAUSE_SEPARATOR.join(parts))


def cell_expect_rule(imports: dict[str, tuple[str, ...]], instance: TemplateInstanceRecord) -> str:
    parts: list[str] = []
    expected = expect_symbols(imports)
    if expected:
        parts.append(zh.text("reference_label") + inline_list(expected))
    semantic = semantic_symbols(imports)
    if semantic:
        parts.append(zh.text("semantic_table_label") + inline_list(semantic))
    checks = check_helper_symbols(imports)
    if checks:
        parts.append(zh.text("assertion_label") + inline_list(checks))
    representative = first_asserting_case(instance.cases)
    if representative is not None:
        parts.append(
            zh.text("expectation_label") + assertion_digest(representative.text_lines)
        )
    if not parts:
        parts.append(clause(instance.summary))
    return cell_text(zh.CLAUSE_SEPARATOR.join(parts))


def cell_domain(instance: TemplateInstanceRecord) -> str:
    if instance.domain_name is None:
        return zh.text("dtype_free")
    if not instance.domain_dtypes:
        return zh.template("domain_no_dtypes").format(domain=instance.domain_name)
    return zh.template("domain_with_dtypes").format(
        domain=instance.domain_name,
        dtypes=inline_list(instance.domain_dtypes, limit=6),
    )


# ---------------------------------------------------------------------------
# Manual-sourced narrative blocks
# ---------------------------------------------------------------------------


def render_manual_narrative(data: DesignData, record: InstructionRecord) -> list[str]:
    """The manual-sourced block that precedes one instruction's coverage table.

    Every instruction the manual declares carries one.  Every fact here is read
    from the manual or from the generator; the authored sentences are the Chinese
    glosses of the cited common rules, and the Chinese requirement comes from
    :data:`MANUAL_TEXT_PATH`, so a missing rendering fails instead of falling back
    to the English manual text.  A generator-only recipe with no manual block
    reports that absence instead of inventing a narrative.
    """

    manual = manual_instructions().get(record.name)
    if manual is None:
        return [
            zh.text("manual_requirement_header"),
            "",
            zh.template("manual_block_absent").format(
                name=record.name,
                path=record.source_path,
                line=record.source_line,
                class_name=record.class_name,
            ),
            "",
        ]
    if manual.mnemonic.split()[0] != record.name:
        fail(
            f"manual mnemonic {manual.mnemonic!r} does not match instruction {record.name!r}"
        )
    manual_rendering = manual_rendering_table()[record.name]
    lines = [
        zh.text("manual_requirement_header"),
        "",
        manual_rendering,
        "",
        zh.text("manual_operation_header"),
        "",
        "```text",
        manual.operation,
        "```",
        "",
        zh.text("encoding_header"),
        "",
        zh.text("table_header_item_value"),
        "| --- | --- |",
        zh.template("manual_row_mnemonic").format(value=manual.mnemonic),
        zh.template("manual_row_format").format(value=manual.encoding_format),
        zh.template("manual_row_funct7").format(value=f"0x{manual.funct7:02x}"),
        zh.template("manual_row_funct3").format(value=f"0x{manual.funct3:x}"),
        zh.template("manual_row_opcode").format(value=f"0x{manual.opcode:02x}"),
        zh.template("manual_row_match_mask").format(
            value=f"`0x{manual.match:08x}` / `0x{manual.mask:08x}`"
        ),
        "",
    ]
    if manual.common_rules:
        lines.extend([zh.text("common_rules_header"), ""])
        for rule in manual.common_rules:
            gloss = zh.COMMON_RULE.get(rule)
            if gloss is None:
                fail(f"common rule {rule!r} has no Chinese gloss")
            lines.append(zh.template("common_rule_item").format(rule=rule, gloss=gloss))
        lines.append("")
    lines.extend(render_generation_path(data, record))
    lines.extend(render_verdict(data, record))
    lines.extend(render_coverage_gaps(data, record, manual))
    return lines


def render_generation_path(data: DesignData, record: InstructionRecord) -> list[str]:
    instances = data.instances_by_key
    templates = zh.ENUM_SEPARATOR.join(
        zh.template("template_case_count").format(
            name=instances[key].name, count=len(record.cases_by_template[key])
        )
        for key in record.template_keys
    )
    return [
        zh.text("generation_path_header"),
        "",
        zh.template("generation_path").format(
            path=record.source_path,
            line=record.source_line,
            class_name=record.class_name,
            base_module=record.base_module,
            combo=combo_label(data.machine),
            count=len(record.template_keys),
            templates=templates,
        ),
        "",
    ]


def render_verdict(data: DesignData, record: InstructionRecord) -> list[str]:
    expect = sum(
        1
        for case in record.cases
        for line in case.assertions
        if not line.startswith("EXPECT_TRAP")
    )
    traps = sum(
        1
        for case in record.cases
        for line in case.assertions
        if line.startswith("EXPECT_TRAP")
    )
    guards = sorted(
        {
            line.strip()
            for case in record.cases
            for line in case.text_lines
            if _GUARD_RE.match(line)
        }
    )
    checks = sorted(
        {
            symbol
            for key in record.template_keys
            for symbol in check_helper_symbols(
                merged_imports(data, data.instances_by_key[key].module)
            )
        }
    )
    trap_clause = (
        zh.template("verdict_traps").format(traps=traps)
        if traps
        else zh.text("verdict_no_traps")
    )
    lines = [zh.text("verdict_header"), ""]
    lines.append(
        zh.template("verdict_line").format(
            cases=record.total_cases, expect=expect, traps=trap_clause
        )
    )
    if checks:
        lines.extend(
            [
                "",
                zh.template("verdict_assertion_helpers").format(
                    helpers=inline_list(tuple(checks))
                ),
            ]
        )
    if guards:
        lines.extend(
            [
                "",
                zh.template("verdict_trap_guards").format(guards=inline_list(tuple(guards))),
            ]
        )
    lines.append("")
    return lines


def render_coverage_gaps(
    data: DesignData, record: InstructionRecord, manual: ManualInstruction
) -> list[str]:
    all_dtypes = tuple(dtype.name for dtype in data.machine.dtypes)
    missing = tuple(name for name in all_dtypes if name not in record.supported_dtypes)
    lines = [zh.text("coverage_gaps_header"), ""]
    covered = zh.template("coverage_dtypes_covered").format(
        count=len(record.supported_dtypes),
        dtypes=inline_list(record.supported_dtypes, limit=8),
    )
    if missing:
        lines.append(
            zh.template("coverage_dtypes_missing").format(
                covered=covered, count=len(missing), missing=inline_list(missing)
            )
        )
    else:
        lines.append(zh.template("coverage_dtypes_all").format(covered=covered))
    match_hex = f"0x{manual.match:08x}"
    asserted = any(
        match_hex in line for case in record.cases for line in case.text_lines
    )
    if not asserted:
        lines.append(
            zh.template("coverage_encoding").format(
                mnemonic=manual.mnemonic,
                match=match_hex,
                mask=f"0x{manual.mask:08x}",
            )
        )
    has_trap = any(
        line.startswith("EXPECT_TRAP") for case in record.cases for line in case.assertions
    )
    if not has_trap:
        lines.append(zh.text("coverage_trap_paths"))
    lines.append(zh.text("coverage_custom_tuple"))
    lines.append("")
    return lines


def render_instruction_section(
    data: DesignData, record: InstructionRecord, number: str
) -> list[str]:
    instances = data.instances_by_key
    lines = [
        f"#### {number} {record.name}",
        "",
        record.summary,
        "",
    ]
    lines.extend(render_manual_narrative(data, record))
    lines.extend(
        [
            zh.text("instruction_table_header"),
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for key in record.template_keys:
        instance = instances[key]
        imports = merged_imports(data, instance.module)
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{instance.name}`",
                    cell_domain(instance),
                    cell_input_mode(imports, instance),
                    cell_expect_rule(imports, instance),
                    str(len(record.cases_by_template[key])),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            zh.template("instruction_summary_note").format(
                combo=combo_label(data.machine),
                cases=record.total_cases,
                path=record.source_path,
                line=record.source_line,
                class_name=record.class_name,
                base_module=record.base_module,
            ),
            "",
        ]
    )
    return lines


def family_shared_modules(records: list[InstructionRecord]) -> tuple[str, ...]:
    modules = {
        record.base_module
        for record in records
        if record.base_module != "mmul_gen.instruction"
    }
    return tuple(sorted(modules))


def catalog_registration_lines() -> dict[str, int]:
    text = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    found: dict[str, int] = {}
    pattern = re.compile(r'Family\(\s*"([a-z_]+)"')
    for index, line in enumerate(text, start=1):
        match = pattern.search(line)
        if match is not None:
            found[match.group(1)] = index
    return found


def render_family_section(
    data: DesignData, family, index: int, registration: dict[str, int]
) -> list[str]:
    records = [record for record in data.instructions if record.family == family.name]
    if not records:
        fail(f"family {family.name!r} has no collected instruction records")
    shared = family_shared_modules(records)
    total_cases = sum(record.total_cases for record in records)
    templates = tuple(
        dict.fromkeys(key for record in records for key in record.template_keys)
    )
    all_dtypes = tuple(dtype.name for dtype in data.machine.dtypes)
    covered = tuple(
        name
        for name in all_dtypes
        if any(name in record.supported_dtypes for record in records)
    )
    design = zh.FAMILY_DESIGN.get(family.name)
    if design is None:
        fail(f"family {family.name!r} has no Chinese design sentence")
    family_name = zh.FAMILY_NAME.get(family.name)
    if family_name is None:
        fail(f"family {family.name!r} has no Chinese name")
    lines = [
        zh.template("family_heading").format(
            index=index, family=family_name, name=family.name
        ),
        "",
        zh.template("family_intro").format(
            name=family.name,
            records=len(records),
            combo=combo_label(data.machine),
            cases=total_cases,
            line=registration.get(family.name, 0),
        ),
        "",
        zh.template("family_design_heading").format(index=index),
        "",
        design,
        "",
        zh.template("family_design_body").format(
            base_modules=inline_list(
                tuple(sorted({record.base_module for record in records}))
            )
        ),
        "",
        zh.template("family_interface_heading").format(index=index),
        "",
        zh.template("family_interface_body").format(
            records=len(records),
            names=inline_list(tuple(record.name for record in records)),
            templates=len(templates),
            template_names=inline_list(templates),
        ),
        "",
        zh.template("family_reuse_heading").format(index=index),
        "",
        zh.template("family_reuse_body").format(
            shared=(
                inline_list(shared)
                if shared
                else zh.template("family_no_shared_module")
            )
        ),
        "",
        zh.template("family_compat_heading").format(index=index),
        "",
        zh.template("family_compat_body").format(
            combo=combo_label(data.machine),
            covered=len(covered),
            total=len(all_dtypes),
            detail=(
                zh.template("family_covered_detail").format(
                    dtypes=inline_list(covered, limit=8)
                )
                if covered
                else ""
            ),
        ),
        "",
    ]
    for offset, record in enumerate(records, start=5):
        lines.extend(render_instruction_section(data, record, f"5.{index}.{offset}"))
    return lines


# ---------------------------------------------------------------------------
# Appendix A: template modules
# ---------------------------------------------------------------------------


def instances_by_module(data: DesignData) -> dict[str, list[TemplateInstanceRecord]]:
    grouped: dict[str, list[TemplateInstanceRecord]] = defaultdict(list)
    for instance in data.instances:
        grouped[instance.module].append(instance)
    return grouped


def render_appendix_a_index(data: DesignData) -> list[str]:
    """The main document's Appendix A: an index into the data appendix."""

    grouped = instances_by_module(data)
    lines = [
        zh.text("appendix_a_heading"),
        "",
        zh.text("generated_by_note"),
        "",
        zh.template("appendix_a_index_intro").format(
            modules=len(data.facts), data_doc=DATA_DOC.name
        ),
        "",
        zh.text("appendix_a_index_header"),
        "| --- | --- | --- | --- |",
    ]
    for module_name in sorted(data.facts):
        facts = data.facts[module_name]
        owned = sorted(grouped.get(module_name, ()), key=lambda item: (item.name, item.key))
        summary_line = facts.description.splitlines()[0].strip()
        if owned:
            template_cell = zh.ENUM_SEPARATOR.join(
                zh.template("appendix_template_cell").format(
                    name=name, count=sum(len(item.cases) for item in group)
                )
                for name, group in (
                    (group[0].name, group) for group in group_instances_by_name(owned)
                )
            )
            users = len({user for instance in owned for user in instance.users})
            user_cell = str(users)
        else:
            defined = [*facts.classes, *facts.functions]
            template_cell = zh.text("shared_mechanism_prefix") + (
                inline_list(tuple(defined), limit=4)
                if defined
                else zh.text("no_top_level_symbols")
            )
            user_cell = zh.text("not_used_by_instructions")
        lines.append(
            f"| `{facts.path.relative_to(GEN_DIR)}` | {cell_text(summary_line)} | "
            f"{template_cell} | {user_cell} |"
        )
    lines.append("")
    return lines


def render_appendix_a_full(data: DesignData) -> list[str]:
    lines = [
        zh.text("appendix_a_full_heading"),
        "",
        zh.text("generated_by_note"),
        "",
        zh.text("appendix_a_full_intro"),
        "",
    ]
    grouped = instances_by_module(data)
    for index, module_name in enumerate(sorted(data.facts), start=1):
        facts = data.facts[module_name]
        lines.extend(
            [
                f"### A.{index} `{facts.path.relative_to(GEN_DIR)}`",
                "",
                zh.text("module_description_header"),
                "",
                facts.description,
                "",
            ]
        )
        owned = sorted(grouped.get(module_name, ()), key=lambda item: (item.name, item.key))
        if owned:
            lines.extend([zh.text("template_content_header"), ""])
            for group in group_instances_by_name(owned):
                lines.extend(render_template_group(group))
            representative = next(
                (
                    case
                    for instance in owned
                    for case in instance.cases
                    if case.assertions
                ),
                None,
            )
            if representative is not None:
                lines.extend(
                    [
                        zh.template("appendix_a_excerpt_note").format(
                            file=representative.instruction_file,
                            number=representative.number,
                            template=representative.template_name,
                            dtype=representative.dtype,
                        ),
                        "",
                        *fenced_asm(
                            delivered_excerpt(representative.text_lines, SNIPPET_LIMIT)
                        ),
                        "",
                    ]
                )
        else:
            lines.extend(render_helper_content(data, facts))
        lines.extend(render_module_assertions(data, module_name))
    return lines


def group_instances_by_name(
    instances: list[TemplateInstanceRecord],
) -> list[list[TemplateInstanceRecord]]:
    grouped: "OrderedDict[str, list[TemplateInstanceRecord]]" = OrderedDict()
    for instance in instances:
        grouped.setdefault(instance.name, []).append(instance)
    return list(grouped.values())


def render_template_group(group: list[TemplateInstanceRecord]) -> list[str]:
    head = group[0]
    parameters = [instance.param for instance in group if instance.param]
    if not parameters:
        parameter_text = zh.text("no_construction_params")
    elif len(parameters) == 1:
        parameter_text = zh.template("params_one").format(param=parameters[0])
    else:
        shown = zh.CLAUSE_SEPARATOR.join(parameters[:3])
        parameter_text = zh.template("params_many").format(
            count=len(group), shown=shown
        )
    users = tuple(
        sorted({user for instance in group for user in instance.users})
    )
    cases = [case for instance in group for case in instance.cases]
    lines = [
        zh.template("template_group_line").format(
            name=head.name,
            class_name=head.class_name,
            params=parameter_text,
            summary=head.summary,
        )
    ]
    if head.domain_name is not None:
        lines.append(
            zh.template("template_domain_line").format(
                domain=head.domain_name, description=head.domain_description
            )
        )
    else:
        lines.append(zh.text("template_no_domain_line"))
    if head.input_cases:
        lines.append(
            zh.template("template_input_cases_line").format(
                cases=inline_list(head.input_cases)
            )
        )
    lines.append(
        zh.template("template_users_line").format(
            users=(
                inline_list(users, limit=12)
                if users
                else zh.text("declared_without_cases")
            )
        )
    )
    lines.append(zh.template("template_case_count_line").format(count=len(cases)))
    return lines


def render_helper_content(data: DesignData, facts: ModuleFacts) -> list[str]:
    importers = importing_modules(data.graph, facts.name)
    defined = [*facts.classes, *facts.functions]
    lines = [zh.text("template_content_header"), ""]
    lines.append(
        zh.template("helper_content_line").format(
            defined=(
                inline_list(tuple(defined))
                if defined
                else zh.text("no_top_level_symbols")
            )
        )
    )
    if importers:
        lines.extend(
            [
                "",
                zh.template("helper_importers_line").format(
                    importers=inline_list(tuple(importers), limit=12)
                ),
            ]
        )
    lines.append("")
    return lines


def render_module_assertions(data: DesignData, module_name: str) -> list[str]:
    cases = [
        case
        for instance in data.instances
        if instance.module == module_name
        for case in instance.cases
    ]
    lines = [zh.text("assertion_placement_header"), ""]
    if not cases:
        lines.extend(
            [
                zh.text("module_no_cases_line"),
                "",
            ]
        )
        return lines
    anchors: "OrderedDict[str, int]" = OrderedDict()
    macros: "OrderedDict[str, int]" = OrderedDict()
    registers: "OrderedDict[str, int]" = OrderedDict()
    for case in cases:
        if not case.assertions:
            continue
        anchor = assertion_anchor(case.text_lines)
        anchors[anchor] = anchors.get(anchor, 0) + 1
        for assertion in case.assertions:
            macro = assertion.split(None, 1)[0]
            macros[macro] = macros.get(macro, 0) + 1
            body = assertion.split(None, 1)[1] if " " in assertion else ""
            register = body.partition(",")[0].strip()
            registers[register] = registers.get(register, 0) + 1
    lines.append(
        zh.template("assertion_macros_line").format(
            macros=zh.ENUM_SEPARATOR.join(
                zh.template("assertion_macro_item").format(macro=macro, count=count)
                for macro, count in macros.items()
            )
        )
    )
    lines.extend(
        [
            "",
            zh.template("assertion_registers_line").format(
                registers=zh.ENUM_SEPARATOR.join(
                    zh.template("assertion_macro_item").format(
                        macro=register, count=count
                    )
                    for register, count in registers.items()
                )
            ),
            "",
            zh.text("assertion_anchors_header"),
            "",
            zh.text("assertion_anchor_table_header"),
            "| --- | --- |",
        ]
    )
    for anchor, count in sorted(anchors.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {cell_text(anchor)} | {count} |")
    lines.append("")
    representative = first_asserting_case(tuple(cases)) or cases[0]
    lines.extend(
        [
            zh.template("representative_assertion_note").format(
                file=representative.instruction_file,
                number=representative.number,
                assertions=zh.CLAUSE_SEPARATOR.join(
                    f"`{item}`" for item in representative.assertions[:6]
                ),
            ),
            "",
        ]
    )
    return lines


# ---------------------------------------------------------------------------
# Appendix B: instance level
# ---------------------------------------------------------------------------


def render_appendix_b(data: DesignData) -> list[str]:
    lines = [
        zh.text("appendix_b_heading"),
        "",
        zh.text("generated_by_note"),
        "",
        zh.text("appendix_b_definition_heading"),
        "",
        zh.template("appendix_b_definition_intro").format(data_doc=DATA_DOC.name),
        "",
        zh.template("appendix_b_instance_heading").format(
            combo=combo_label(data.machine)
        ),
        "",
        zh.text("appendix_b_instance_intro"),
        "",
    ]
    for record in data.instructions:
        if record.name in INSTANCE_INSTRUCTIONS:
            lines.extend(render_instance_table(data, record))
    return lines


def render_instance_table(data: DesignData, record: InstructionRecord) -> list[str]:
    instances = data.instances_by_key
    lines = [
        f"#### B.2.{INSTANCE_INSTRUCTIONS.index(record.name) + 1} {record.name}",
        "",
        zh.template("instance_summary_line").format(
            summary=clause(record.summary), cases=record.total_cases
        ),
        "",
        zh.text("instance_table_header"),
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in record.template_keys:
        instance = instances[key]
        for case in record.cases_by_template[key]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(case.number),
                        f"`{case.instruction}`",
                        f"`{case.template_name}`",
                        f"`{case.dtype}`" if case.dtype else zh.text("none"),
                        cell_text(payload_input_summary(case, instance)),
                        cell_text(assertion_digest(case.text_lines)),
                    ]
                )
                + " |"
            )
    lines.append("")
    return lines


def payload_input_summary(case: CaseRecord, instance: TemplateInstanceRecord) -> str:
    # ``case.description`` is the generator's English ``# input:`` comment; the
    # document keeps the Chinese wording it was delivered with.
    mode = (
        chinese_case_description(case.description)
        if case.description
        else instance.summary
    )
    parts = [mode]
    if case.payload is not None:
        parts.append(compact(case.payload, max_items=3))
    if case.layout:
        parts.append(zh.text("layout_prefix") + layout_summary(case.layout))
    if len(parts) == 1:
        return parts[0]
    return zh.template("payload_with_detail").format(
        mode=parts[0], detail=zh.CLAUSE_SEPARATOR.join(parts[1:])
    )


def layout_summary(layout: str) -> str:
    """Turn the emitted layout comment lines into one cell-sized phrase."""

    fragments = [
        fragment.strip().lstrip("#").strip()
        for fragment in layout.split(" / ")
        if fragment.strip()
    ]
    return zh.CLAUSE_SEPARATOR.join(fragments)


# ---------------------------------------------------------------------------
# Data appendix (definition level)
# ---------------------------------------------------------------------------


def render_data_doc(data: DesignData) -> str:
    lines = [
        zh.text("data_doc_heading"),
        "",
        zh.template("data_doc_intro").format(combo=combo_label(data.machine)),
        "",
    ]
    lines.extend(render_appendix_a_full(data))
    lines.extend(
        [
            zh.text("data_doc_appendix_b_heading"),
            "",
            zh.text("data_doc_appendix_b_intro"),
            "",
        ]
    )
    by_module: dict[str, list[TemplateInstanceRecord]] = defaultdict(list)
    for instance in data.instances:
        by_module[instance.module].append(instance)
    for module_index, module_name in enumerate(sorted(by_module), start=1):
        facts = data.facts[module_name]
        instances = sorted(by_module[module_name], key=lambda item: (item.name, item.key))
        lines.extend(
            [
                f"### B.{module_index} `{facts.path.relative_to(GEN_DIR)}`",
                "",
                facts.description,
                "",
            ]
        )
        for instance_index, instance in enumerate(instances, start=1):
            lines.extend(
                render_data_instance(
                    data, facts, instance, f"B.{module_index}.{instance_index}"
                )
            )
    return "\n".join(lines).rstrip("\n") + "\n"


def render_data_instance(
    data: DesignData, facts: ModuleFacts, instance: TemplateInstanceRecord, number: str
) -> list[str]:
    lines = [
        zh.template("data_instance_heading").format(
            number=number,
            name=instance.name,
            class_name=instance.class_name,
            param=(
                zh.template("data_instance_param").format(param=instance.param)
                if instance.param
                else ""
            ),
        ),
        "",
        instance.summary,
        "",
    ]
    if instance.domain_name is not None:
        lines.append(
            zh.template("data_instance_domain_line").format(
                domain=instance.domain_name, description=instance.domain_description
            )
        )
    else:
        lines.append(zh.text("data_instance_no_domain_line"))
    lines.append("")
    lines.append(
        zh.template("data_instance_users_line").format(
            users=(
                inline_list(instance.users, limit=12)
                if instance.users
                else zh.text("none")
            )
        )
    )
    lines.append("")
    by_dtype: "OrderedDict[str, list[CaseRecord]]" = OrderedDict()
    for case in instance.cases:
        by_dtype.setdefault(case.dtype or zh.text("none"), []).append(case)
    if by_dtype:
        lines.extend(
            [
                zh.text("data_instance_table_header"),
                "| --- | --- | --- |",
            ]
        )
        for dtype, cases in by_dtype.items():
            first = first_asserting_case(tuple(cases)) or cases[0]
            inputs = (
                zh.CLAUSE_SEPARATOR.join(
                    f"`{label}`: {summary}" for label, summary in label_digest(first.data_lines)
                )
                or instance.summary
            )
            lines.append(
                f"| `{dtype}` | {cell_text(inputs)} | "
                f"{cell_text(assertion_digest(first.text_lines))} |"
            )
        lines.append("")
    else:
        lines.extend([zh.text("data_instance_no_cases"), ""])
    first = first_asserting_case(instance.cases) or instance.first_case
    if first is not None:
        lines.extend(
            [
                zh.template("data_instance_excerpt_note").format(
                    file=first.instruction_file, number=first.number, dtype=first.dtype
                ),
                "",
                *fenced_asm(delivered_excerpt(first.text_lines, SNIPPET_LIMIT)),
                "",
            ]
        )
        if first.data_lines:
            lines.extend(
                [
                    zh.text("data_instance_data_note"),
                    "",
                    *fenced_asm(excerpt(first.data_lines, DATA_SNIPPET_LIMIT)),
                    "",
                ]
            )
        else:
            lines.extend([zh.text("data_instance_no_data_note"), ""])
    return lines


# ---------------------------------------------------------------------------
# Assembly of the main document
# ---------------------------------------------------------------------------


def render_performance_section(data: DesignData) -> list[str]:
    """Chapter 6: the deterministic generation-time scale facts.

    Every number is read from the generator's own default sweep or from the
    sources a real generation pass produced; no runtime performance figure is
    stated because none is measured here.
    """

    combos = run_ztt_tests.all_combos()
    combo = combo_label(data.machine)
    total_cases = sum(record.total_cases for record in data.instructions)
    expect = sum(
        1
        for record in data.instructions
        for case in record.cases
        for line in case.assertions
        if not line.startswith("EXPECT_TRAP")
    )
    traps = sum(
        1
        for record in data.instructions
        for case in record.cases
        for line in case.assertions
        if line.startswith("EXPECT_TRAP")
    )
    dtypes = tuple(dtype.name for dtype in data.machine.dtypes)
    busiest = max(data.instructions, key=lambda record: (record.total_cases, record.name))
    return [
        zh.text("performance_heading"),
        "",
        zh.text("performance_table_header"),
        "| --- | --- |",
        zh.template("performance_combos").format(
            n=len(run_ztt_tests.N_VALUES),
            uds=len(run_ztt_tests.UDS_VALUES),
            m=len(run_ztt_tests.MREG_VALUES),
            acc=len(run_ztt_tests.ACC_VALUES),
            total=len(combos),
        ),
        zh.template("performance_source_files").format(count=len(data.instructions)),
        zh.template("performance_source_size").format(
            combo=combo, lines=data.source_lines, bytes=data.source_bytes
        ),
        zh.template("performance_cases").format(combo=combo, cases=total_cases),
        zh.template("performance_assertions").format(
            combo=combo,
            expect=expect,
            traps=(
                zh.template("performance_traps").format(traps=traps)
                if traps
                else zh.text("performance_no_traps")
            ),
        ),
        zh.template("performance_dtypes").format(combo=combo, count=len(dtypes)),
        zh.template("performance_busiest").format(
            combo=combo, name=busiest.name, cases=busiest.total_cases
        ),
        zh.text("performance_generation_mode"),
        zh.text("performance_runtime_cost"),
        "",
        zh.text("performance_footer"),
        "",
    ]


def render_main_doc(data: DesignData) -> str:
    registration = catalog_registration_lines()
    names = [record.name for record in data.instructions]
    unique_files = {record.file_name for record in data.instructions}
    unique_names = set(names)
    lines: list[str] = [zh.STATIC_FRONT.rstrip("\n"), ""]
    lines.extend(
        [
            zh.template("main_doc_inventory").format(
                records=len(data.instructions),
                files=len(unique_files),
                mnemonics=len(unique_names),
                families=len(INSTRUCTION_FAMILIES),
                combo=combo_label(data.machine),
                cases=sum(record.total_cases for record in data.instructions),
            ),
            "",
            zh.text("main_doc_note"),
            "",
        ]
    )
    for index, family in enumerate(INSTRUCTION_FAMILIES, start=1):
        lines.extend(render_family_section(data, family, index, registration))
    lines.extend(render_performance_section(data))
    lines.append(zh.STATIC_BACK.rstrip("\n"))
    lines.append("")
    lines.extend(render_appendix_a_index(data))
    lines.extend(render_appendix_b(data))
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Generation pass
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--macro-file", type=Path, default=DEFAULT_MACRO_FILE)
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--uds", type=int, default=DEFAULT_UDS)
    parser.add_argument("--m", type=int, default=DEFAULT_M)
    parser.add_argument("--acc", type=int, default=DEFAULT_ACC)
    parser.add_argument("--main-doc", type=Path, default=MAIN_DOC)
    parser.add_argument("--data-doc", type=Path, default=DATA_DOC)
    parser.add_argument("--check", action="store_true", help="verify outputs are current")
    return parser.parse_args(argv)


def generate_sources(machine: MachineConfig) -> dict[str, str]:
    """Write one real generation pass to a scratch directory and read it back."""

    from mmul_gen.__main__ import write_source

    sources: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="ztt-design-") as directory:
        out_dir = Path(directory)
        for instruction in ALL_INSTRUCTIONS:
            source = instruction.gen(machine)
            if source is None:
                fail(f"instruction {instruction.name!r} produced no source")
            write_source(out_dir, source)
            path = out_dir / source.name
            if not path.is_file():
                fail(f"generator did not write {source.name!r} to the scratch directory")
            sources[source.name] = path.read_text(encoding="utf-8")
    return sources


def _validate(data: DesignData) -> None:
    """Fail-fast invariants over the collected records."""

    if not data.instances:
        fail("no template instances collected")
    if len(data.instructions) != len(ALL_INSTRUCTIONS):
        fail(
            f"collected {len(data.instructions)} instructions, catalog declares "
            f"{len(ALL_INSTRUCTIONS)}"
        )
    for instance in data.instances:
        if not instance.summary.strip():
            fail(f"template {instance.name!r} has an empty Chinese summary")
        if instance.module not in data.facts:
            fail(f"template {instance.name!r} lives outside templates/: {instance.module}")
        for case in instance.cases:
            if case.dtype is None and instance.domain_name is not None:
                fail(
                    f"template {instance.name!r} declares domain {instance.domain_name!r} "
                    f"but produced a dtype-free case {case.number}"
                )
        if instance.cases and first_asserting_case(instance.cases) is None:
            fail(
                f"template {instance.name!r} produced {len(instance.cases)} cases but none "
                f"carries an EXPECT/EXPECT_TRAP assertion"
            )
    for fact in data.facts.values():
        if not fact.description.strip():
            fail(f"module {fact.name!r} has an empty Chinese description")
    manual = manual_instructions()
    table = manual_rendering_table()
    for record in data.instructions:
        if not record.summary.strip():
            fail(f"instruction {record.name!r} has an empty Chinese summary")
        if record.name in manual and not table[record.name].strip():
            fail(f"instruction {record.name!r} has an empty Chinese manual rendering")
    for domain in ALL_DOMAINS:
        if not isinstance(domain, DTypeDomain):
            fail(f"datatype domain {domain!r} is not a DTypeDomain")
        require_chinese(
            "domain_description", domain.name, f"datatype domain {domain.name!r}"
        )
    # The documents render a generated case description both in the
    # instance-level table and inside the assembly excerpts, so every case
    # description must have a Chinese rendering, or the delivered document would
    # carry English prose.
    for record in data.instructions:
        for case in record.cases:
            if case.description:
                chinese_case_description(case.description)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    machine = MachineConfig(
        dtypes=parse_dtypes(args.macro_file),
        n=args.n,
        uds=args.uds,
        num_m_regs=args.m,
        num_acc_regs=args.acc,
    )
    sources = generate_sources(machine)
    data = collect_design_data(machine, sources)
    _validate(data)
    main_text = render_main_doc(data)
    data_text = render_data_doc(data)

    outputs = {args.main_doc: main_text, args.data_doc: data_text}
    if args.check:
        stale = [
            str(path)
            for path, text in outputs.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != text
        ]
        if stale:
            fail("generated outputs are stale: " + ", ".join(stale))
        print("generated outputs are current")
        return 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    print(f"wrote {args.main_doc} ({main_text.count(chr(10))} lines)")
    print(f"wrote {args.data_doc} ({data_text.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
