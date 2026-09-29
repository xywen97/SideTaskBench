# Compute metrics

This package computes publication tables from completed, immutable coding runs. It never
modifies an input run directory.

The CLI supports three roles:

- `--main-run MODEL CONDITION DIRECTORY`: one-attempt condition comparison;
- `--analysis-run MODEL DIRECTORY`: complete wrapped repeats for reference-count and
  clean-adjusted LLM-call analysis;
- `--pass-run MODEL K DIRECTORY`: an independently executed `K`-repeat experiment.

Use the `wrapped_boundary` main-table label for a wrapped run whose recorded defense is
`boundary`; its underlying source condition remains `wrapped`.

Repeat the same option when one logical experiment is split across directories. Run
`./cal_acc.sh` for the repository's current DeepSeek and Qwen configuration.

Outputs include machine-readable JSON, Markdown, and separate CSV tables. `Block Seen` and
the runtime `exposed` field use the same definition: the current atomic task id and the
configured block marker must occur in model-visible tool output.
