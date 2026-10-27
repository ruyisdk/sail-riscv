#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The frozen excerpt set: freeze it, and re-check it against the checkout.

The manifest exists so the gate still bites on a machine without the
specification.  Two things keep it honest, and both live here:

* :func:`emit_manifest` freezes a template's quote *with the position it was
  really found at*, which is what reviewers read in the diff;
* :func:`verify_manifest_against_spec` re-checks the frozen text and file
  digests against a live checkout, so a specification bump cannot leave the
  manifest quietly describing a sentence that no longer exists.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Mapping

from mmul_gen.spec_citations.constants import (
    FIELD_LABELS,
    MANIFEST_VERSION,
    STRUCTURAL_SKIP,
)
from mmul_gen.spec_citations.environment import select_templates
from mmul_gen.spec_citations.model import (
    Corpus,
    DeclaredRange,
    load_corpus,
    normalize,
    parse_citation_block,
    read_module_docstring,
    template_quote,
)
from mmul_gen.spec_citations.rules import check_declared_ranges


def _dict_entries(raw: object) -> list[dict[str, object]]:
    """The object entries of a manifest list; junk entries are ignored here."""
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def verify_manifest_against_spec(data: Mapping[str, object], spec_root: Path) -> list[str]:
    """Return one problem per frozen excerpt the live specification contradicts."""
    live = load_corpus(spec_root)
    problems: list[str] = []
    recorded_files = data.get("files", {})
    if not isinstance(recorded_files, dict):
        return ["manifest 'files' is not an object"]
    for name, meta in sorted(recorded_files.items()):
        corpus = live.get(str(name))
        if corpus is None:
            problems.append(f"{name}: recorded in the manifest but absent from {spec_root / 'src'}")
            continue
        if isinstance(meta, dict) and "length" in meta and int(meta["length"]) != corpus.line_count:
            problems.append(f"{name}: manifest records {meta['length']} lines, the checkout has {corpus.line_count}")
        if isinstance(meta, dict) and "sha256" in meta:
            actual = hashlib.sha256(corpus.text.encode("utf-8")).hexdigest()
            if actual != meta["sha256"]:
                problems.append(
                    f"{name}: text changed since the manifest was frozen "
                    f"({meta['sha256'][:12]} -> {actual[:12]})"
                )
    for entry in _dict_entries(data.get("excerpts")):
        name, text = str(entry.get("file")), normalize(str(entry.get("text")))
        corpus = live.get(name)
        if corpus is None:
            problems.append(f"{name}: excerpt cites a file the checkout does not have")
            continue
        if text not in corpus.text:
            problems.append(f"{name}: frozen excerpt is no longer verbatim in the checkout: {text[:60]!r}")
    return problems


def _locate_quote(corpus: Mapping[str, Corpus], declared: list[DeclaredRange], quote: str) -> tuple[str, int] | None:
    """Where the quote really occurs: inside a declared range, otherwise anywhere."""
    for entry in declared:
        source = corpus.get(entry.file)
        if source is None:
            continue
        for occurrence in re.finditer(re.escape(quote), source.text):
            line = source.line_of(occurrence.start())
            if entry.start <= line <= entry.end:
                return entry.file, line
    for name, source in sorted(corpus.items()):
        offset = source.text.find(quote)
        if offset >= 0:
            return name, source.line_of(offset)
    return None


def emit_manifest(templates: Path, spec_root: Path, destination: Path) -> int:
    """Freeze every template's quote together with its source position."""
    corpus = load_corpus(spec_root)
    excerpts: list[dict[str, object]] = []
    seen: set[tuple[str, int, str]] = set()
    for path in select_templates(templates, ()):
        if path.name in STRUCTURAL_SKIP:
            continue
        block = parse_citation_block(read_module_docstring(path))
        if block.duplicates or not all(block.values.get(label) for label in FIELD_LABELS):
            print(f"ERROR: {path.name} has no usable citation block; fix it before freezing", file=sys.stderr)
            return 2
        quote = template_quote(path)
        declared, _ = check_declared_ranges(block.values.get("Spec", ""), corpus)
        found = _locate_quote(corpus, declared, quote)
        if found is None:
            print(f"ERROR: quote of {path.name} is not in the specification: {quote[:60]!r}", file=sys.stderr)
            return 2
        key = (found[0], found[1], quote)
        if key in seen:
            continue
        seen.add(key)
        excerpts.append({"file": found[0], "line": found[1], "text": quote})
    files = {
        name: {
            "length": source.line_count,
            "sha256": hashlib.sha256(source.text.encode("utf-8")).hexdigest(),
        }
        for name, source in sorted(corpus.items())
        if any(entry["file"] == name for entry in excerpts)
    }
    payload = {"spec_version": MANIFEST_VERSION, "files": files, "excerpts": excerpts}
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(excerpts)} excerpt(s) covering {len(files)} file(s) to {destination}")
    return 0
