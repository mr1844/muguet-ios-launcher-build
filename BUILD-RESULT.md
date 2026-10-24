# Muguet iOS build result — 24 October 2026

An actual **launcher-only IPA was compiled, packaged, downloaded and validated**. It contains the native Muguet application/runtime but **cannot play GTA V**, because compatible executable game code was unavailable. It has **not been installed or tested on an iPhone**. The requested playable GTA V outcome remains unfulfilled.

## Download and identity

- File: `Muguet-launcher-only.ipa`
- Size: **4,791,908 bytes** (4.79 MB / 4.57 MiB)
- SHA-256: `099ca47e5311e90c808a8a9b32c2b44809d6fbf638a12dd9cb63f6d5738219d1`
- Upstream: [c22dev/muguet](https://github.com/c22dev/muguet)
- Source commit: `1b4600b052b864c78fe36180073ff406663b7e0b`
- Build infrastructure commit: `2d8a7f558f556f31f72391b9dda68cebd7db4b13`
- [Successful build and logs](https://github.com/mr1844/muguet-ios-launcher-build/actions/runs/40086156405)
- [GitHub artifact including IPA, checksums and matching source](https://github.com/mr1844/muguet-ios-launcher-build/actions/runs/40086156405/artifacts/12557800430). GitHub reports expiration on **31 October 2026 at 11:38 Vienna time**; the local downloaded files do not depend on this expiration.

## What was verified

The workflow ran on GitHub's standard public-repository Apple Silicon `macos-26` runner. The public repository and source contain no GTA V game files or signing credentials. No paid larger runner was used. The environment was macOS 26.6.2, Xcode 26.6, Rust/Cargo 1.98.1, CMake 4.4.4 and XcodeGen 2.46.0.

Both available upstream host unit tests passed: real free-space reporting and save persistence across close/reopen. The unchanged upstream iOS build script then compiled an optimized Release executable targeting `aarch64-apple-ios`, generated the Xcode application, applied an ad-hoc signature and packaged the IPA. Tracked upstream source and `Cargo.lock` remained unchanged.

Archive and native Apple-tool validation passed:

- Valid ZIP with CRC-checked entries and a `Payload/Muguet.app` bundle.
- Expanded Info.plist, bundle identifier `ch.cclerc.muguet.ios`, iPhone support and iOS 15.0 minimum.
- Thin ARM64 Mach-O `MH_EXECUTE`, iOS device platform rather than Simulator, with executable code and an entry point.
- No encrypted executable, embedded game-code section, `.wasm` or `.cwasm` files.
- `codesign --verify --deep --strict` passed after extracting the actual IPA; `lipo` independently confirmed `arm64`.
- Ad-hoc signature and exactly the upstream sideload entitlement `com.apple.developer.kernel.increased-memory-limit=true`; no embedded provisioning profile.
- Downloaded artifact checksums matched; a separate local archive inspection and SHA-256 calculation confirmed the delivered file.
- An independent read-only check verified all 1,461 executable signature page hashes, the Info.plist and resource-manifest hashes, and the memory entitlement. All 32 linked libraries use system paths; no missing bundled third-party library was indicated.

These checks confirm compilation and package properties. They do not establish installation, launch behavior, graphics performance or stability on the iPhone 17 Pro Max.

## Installation requirements

Re-sign/provision this IPA using your existing sideloading process. The ad-hoc signature alone does not authorize installation on a normal iPhone. Upstream recommends [AltStore](https://github.com/c22dev/muguet#building) and notes signing-tool issues with the memory entitlement. The installed app must receive the appropriate provisioned entitlement; its presence in this artifact does not prove the final installation retains it. No Apple signing credentials were requested or uploaded during this build.

## Why this cannot play GTA V

Muguet supplies the native iOS host, Metal graphics integration, audio, controls and multiplayer support around a compatible web-port game executable. **`game.wasm` is the actual executable game logic**, not merely textures or optional content. For iOS, [upstream precompiles and embeds it during the build](https://github.com/c22dev/muguet/blob/1b4600b052b864c78fe36180073ff406663b7e0b/make-ios.sh#L33). Without it, the [launcher explicitly reports missing game code](https://github.com/c22dev/muguet/blob/1b4600b052b864c78fe36180073ff406663b7e0b/ios/Launcher.swift#L264).

A playable build requires a lawfully obtained compatible web-port package containing `b/<build>/game.wasm`, matching `data/` and `b/<build>/shaders/`. The code is needed at build time; the data and shaders must subsequently be imported. Importing files into this launcher-only IPA cannot supply the missing compiled game code. A rebuild is required.

Ordinary legally owned GTA V PC installation files are not directly compatible with the documented importer. No supported PC-to-web-port conversion tool or procedure was found in the official project. The [official release](https://github.com/c22dev/muguet/releases/tag/0.1) supplies only a macOS app. No trustworthy maintained prebuilt IPA was established; an unofficial candidate had unverifiable source/build provenance and acquired game code from an unrelated host, so it was not downloaded.

## Graphics and device limits

The build retains upstream's Release optimizations, Metal renderer, five-GiB sideload heap configuration and adaptive graphics defaults. The iOS launcher implements Quality (75% resolution, High textures, 60-fps cap) and Max (100%, Very High, 60-fps cap), alongside lower presets. Upstream warns that Max may slow down or terminate the app. No setting was forced without on-device stability evidence. This launcher-only IPA has no playable game on which to verify graphical quality.

An open upstream [iPhone 17 Pro Max issue](https://github.com/c22dev/muguet/issues/34) reports crashes after one or two minutes. The maintainer requested an actual crash/Jetsam log, so the cause remains unconfirmed. It would be inaccurate to promise stable gameplay on this device.

## Included evidence and source

`manifest.json`, `architecture-report.json`, `toolchain.txt`, `SHA256SUMS`, `Cargo.lock`, dependency metadata, the GPL license, matching upstream source archive and exact build-infrastructure archive accompany the IPA. The source snapshot includes the code used for this build. Build logs are available in the successful workflow above.
