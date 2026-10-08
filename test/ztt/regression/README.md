# AME regression tests

Fixed minimal tests for the behavior of single AME instructions, complementing the generated matrix
(`gen/mmul_gen/`): the generated ELFs have broad coverage, while these files pin down individual
deterministic cases and catch regressions without needing regeneration.

Run:

```sh
./run_repro.sh                                  # use the default simulator path
./run_repro.sh /path/to/sail_riscv_sim          # override the sail binary
```

Spike is run via `spike_ztt_runner.py`, which already wires in an AME-enabled spike build.

## Regression guards

| File                          | Configuration | Coverage                                                                                                                                                                                                              |
| ----------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spike_int128_mhdiff_x_m32.S` | n8/uds16/m32  | Rounding direction of the 128-bit `mhdiff.ew.x`. `halve_mag_rm` rounds the magnitude first for RNU/RDN, which flips the tie direction of negative quotients (-2.5 RNU must be -2, not -3). Both simulators must pass. |

All tests should pass on both simulators.
