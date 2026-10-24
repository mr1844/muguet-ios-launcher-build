# Preparation checks

Checked on Windows on 2026-10-24, before any cloud build:

- `bash -n` passed for `scripts/prepare-macos.sh` and `scripts/build-and-validate.sh` using Git for Windows Bash.
- Python 3.9 bytecode compilation passed for `scripts/validate-ipa.py`.
- YAML parsed successfully with PyYAML 6.0.3 using YAML 1.2-compatible handling of the `on` key. Assertions confirmed the manual-only trigger, public-repository guard, standard `macos-26` runner, and 40-character action commit pins.
- Eight structural/safety fixture checks passed: valid minimal arm64 Mach-O parsing, rejection of x86_64, rejection of iOS Simulator, rejection of the embedded game-code section, rejection of encrypted code, valid synthetic IPA structure, rejection of ZIP path traversal, and refusal to claim full signature validation on Windows. Synthetic fixtures were temporary and removed. They were not real applications or build artifacts.
- The two action commit pins were resolved from the official GitHub action repositories' release tag references. The pinned Muguet commit matches the local pristine upstream checkout.

At preparation time, upstream tests, iOS compilation, packaging, native validation and real artifact size/hash were pending. These subsequently passed in [run 40086156405](https://github.com/mr1844/muguet-ios-launcher-build/actions/runs/40086156405): two host tests passed and an actual arm64 IPA was produced and verified. Device testing has not occurred; gameplay is unavailable in this launcher-only build. See `BUILD-RESULT.md` for the completed result.
