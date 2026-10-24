#!/usr/bin/env bash
set -euo pipefail

task_root="${GITHUB_WORKSPACE:?}"
source_root="$task_root/upstream"
infra_root="$task_root/infrastructure"
output_root="$task_root/artifacts"
expected_commit=1b4600b052b864c78fe36180073ff406663b7e0b
[[ "${UPSTREAM_COMMIT:?}" == "$expected_commit" ]]
[[ "$(git -C "$source_root" rev-parse HEAD)" == "$expected_commit" ]]
[[ -z "$(git -C "$source_root" status --porcelain)" ]]
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]]
mkdir -p "$output_root"

# The source checkout is pristine, no input game path is accepted, and no JIT is
# compiled into the iOS target. Keep upstream's Release and 5 GiB sideload defaults.
unset MUGUET_GAME_CODE TEAM FREE RUSTFLAGS
export PATH="/opt/homebrew/opt/rustup/bin:$HOME/.cargo/bin:$PATH"
export MUGUET_IOS_HEAP_GB=5
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
cd "$source_root"

lock_before="$(shasum -a 256 Cargo.lock | awk '{print $1}')"
cargo "+${RUST_TOOLCHAIN:?}" fetch --locked
cargo "+$RUST_TOOLCHAIN" metadata --locked --format-version 1 > "$output_root/cargo-metadata.json"
# Runs upstream host unit tests. It does not simulate an iPhone or validate GTA V.
cargo "+$RUST_TOOLCHAIN" test --locked --bin muguet
./make-ios.sh --ipa
[[ "$(shasum -a 256 Cargo.lock | awk '{print $1}')" == "$lock_before" ]]
[[ -z "$(git status --porcelain --untracked-files=no)" ]]

cp build/Muguet.ipa "$output_root/Muguet-launcher-only.ipa"
git archive --format=tar.gz --prefix=muguet-source/ HEAD > "$output_root/muguet-source-$expected_commit.tar.gz"
cp LICENSE "$output_root/Muguet-LICENSE"
cp Cargo.lock "$output_root/Cargo.lock"
# Include the build/validation instructions that produced this exact artifact.
tar -czf "$output_root/build-infrastructure.tar.gz" -C "$infra_root" .github scripts README.md .gitattributes .gitignore
{
  sw_vers
  xcodebuild -version
  xcrun --sdk iphoneos --show-sdk-version
  rustc "+$RUST_TOOLCHAIN" --version --verbose
  cargo "+$RUST_TOOLCHAIN" --version
  cmake --version
  xcodegen --version
  git -C "$infra_root" rev-parse HEAD
} > "$output_root/toolchain.txt"

python3 "$infra_root/scripts/validate-ipa.py" \
  "$output_root/Muguet-launcher-only.ipa" \
  --source-commit "$expected_commit" \
  --output-directory "$output_root"

cd "$output_root"
find . -maxdepth 1 -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 shasum -a 256 > SHA256SUMS
cat manifest.json >> "$GITHUB_STEP_SUMMARY"
