# Manual prose import

`instructions.json` is the structured interface extracted from the Ztt prose manual. It is generated
by `../generators/import_manual_prose.rb`: by default that script reads `src/instructions.adoc`
under the pinned manual checkout and parses the encoding allocation tables. Use `--source` when the
manual checkout is elsewhere.

The current snapshot is manual tag `v0.6` (commit `8d27acdcee7a189aad4e2907412e0c40a9d4b9e2`),
containing 138 instructions. The JSON records the source commit, the instruction order and
classification, the prose summary/operation, the WaveDrom encodings, and the derived decoder
`mask`/`match`.

To refresh the snapshot after the manual checkout is updated:

```bash
ruby ../generators/import_manual_prose.rb
```

The prose snapshot is the only input to the current generator.
