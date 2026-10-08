# Generator tests

This directory holds the Python unit tests for the generator's shared reference modules. The
canonical suite entry point is:

```sh
cd sail-ame/test/ztt/gen
python3 -m tests
```

The runner discovers every `test_*.py` module in this directory. When reviewing a change you can
run a single focused module:

```sh
python3 -m unittest tests.test_numeric_reference
python3 -m unittest tests.test_manual_sync
python3 -m unittest tests.test_matrix_geometry
```

The Python files under the parent directory `gen/` are generator implementations or validation
tools: `mmul_gen/` is the assembly generator, and `check_manual_sync.py` compares the local inputs
against the machine-readable manual. Runtime JSON configurations are validated by Sail, not by the
test generator. These files are not test suites, and they can be imported directly from the
generator root.

`tests/test_mmul_gen.py` dispatches to the generator suite under `gen/mmul_gen/tests/`, so the
command above covers it as well. When changing the generator specifically, run that suite directly:

```sh
cd sail-ame/test/ztt/gen
python3 -m mmul_gen.tests
```
