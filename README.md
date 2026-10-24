# Muguet launcher-only iOS build

Prepared for upstream commit `1b4600b052b864c78fe36180073ff406663b7e0b` of [c22dev/muguet](https://github.com/c22dev/muguet/tree/1b4600b052b864c78fe36180073ff406663b7e0b).

**Status: prepared and checked statically on Windows; no macOS compilation or iPhone test has been performed by this package.** A workflow file is not a built IPA. Successful runs produce an actual arm64 Release IPA, its size/SHA-256 manifest, archive/architecture/signature reports, the matching upstream source snapshot and license, and these build scripts.

## What this builds

`Muguet-launcher-only.ipa` contains the upstream launcher/runtime with an ad-hoc signature, intended for re-signing with a sideloading tool. It contains no GTA V game code or data and **cannot play GTA V**. Importing a game-data ZIP afterward cannot add the missing game code: upstream compiles compatible web-port `game.wasm` into the iOS executable during the build. A playable build needs a rebuild with that compatible code plus matching `data/` and `b/<build>/shaders/` files. This package accepts no game-file inputs and fetches no game files. It does not provide a PC-to-web-port conversion tool.

The build keeps upstream's Release optimizations, Metal renderer, 5 GiB sideload heap default, and runtime graphics defaults. It makes no untested claims about maximum graphics quality, iPhone stability, memory entitlement availability, or gameplay completeness. Upstream targets iOS 15+, arm64. Device installation and operation still need testing.

## Run on GitHub

1. Put the contents of this directory at the root of a **public** GitHub repository. Review the files before publishing; there are no credentials or game assets in this package.
2. In Actions, enable workflows if prompted, then manually run **Build Muguet launcher-only IPA**. No push, pull-request, or scheduled event starts this workflow.
3. A successful run exposes the `Muguet-launcher-only-1b4600b052b864c78fe36180073ff406663b7e0b` artifact. Download/extract it and verify `SHA256SUMS`. It includes the `.ipa`, `manifest.json`, `architecture-report.json`, source, license, dependency metadata/lockfile, and toolchain report.
4. Re-sign/provision the IPA with your existing sideloading tool. No Apple signing credentials are requested or uploaded. An ad-hoc signature alone does not authorize installation on an ordinary iPhone.

The workflow's job-level public-repository guard is evaluated before a macOS runner is allocated, and the preparation script checks again. A private repository skips the build. It uses the standard `macos-26` arm64 runner, never a paid larger runner. GitHub documents standard public-repository runners as free. Artifacts expire after seven days; account policies, storage allowances, runner availability, and GitHub Actions permissions still apply.

## Checks and provenance

The workflow selects Rust `1.98.1`, installs `aarch64-apple-ios`, verifies Xcode 26+, and installs Homebrew `cmake` and `xcodegen`. It runs upstream's host unit tests with a locked dependency graph, then the unchanged `./make-ios.sh --ipa`. It checks that `Cargo.lock` and tracked source remain unchanged. Installed Xcode/Homebrew versions are recorded; the whole environment is not bit-for-bit pinned.

Validation checks ZIP CRCs and paths, Info.plist, executable permissions, a thin arm64 Mach-O `MH_EXECUTE` targeting iOS devices, a code entry point, absence of the upstream game-code section and `.wasm`/`.cwasm` files, no encryption, the ad-hoc code signature, and exact upstream sideload entitlements. It records the real IPA size and SHA-256 only after validation succeeds. These checks establish archive/build properties; they do not establish iPhone operation.

Official action tags were resolved directly with `git ls-remote` on 2026-10-24: checkout `v4.3.1` -> `34e114876b0b11c390a56381ad16ebd13914f8d5`; upload-artifact `v4.6.2` -> `ea165f8d65b6e75b540449e92b4886f43607fa02`.

References: [GitHub standard runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [upstream build script](https://github.com/c22dev/muguet/blob/1b4600b052b864c78fe36180073ff406663b7e0b/make-ios.sh), [upstream iOS project](https://github.com/c22dev/muguet/blob/1b4600b052b864c78fe36180073ff406663b7e0b/ios/project.yml), [upstream game-code implementation](https://github.com/c22dev/muguet/blob/1b4600b052b864c78fe36180073ff406663b7e0b/src/main.rs), [upstream GPL license](https://github.com/c22dev/muguet/blob/1b4600b052b864c78fe36180073ff406663b7e0b/LICENSE).
