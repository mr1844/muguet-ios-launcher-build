#!/usr/bin/env bash
set -euo pipefail

[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || {
  echo 'An Apple Silicon macOS runner is required.' >&2
  exit 1
}
[[ "${GITHUB_EVENT_NAME:-}" == workflow_dispatch ]] || {
  echo 'This script is intended for an explicitly dispatched GitHub Actions job.' >&2
  exit 1
}

python3 - <<'PY'
import json, os
with open(os.environ['GITHUB_EVENT_PATH'], encoding='utf-8') as stream:
    event = json.load(stream)
assert event['repository']['private'] is False, 'Public repository required; do not incur private-runner charges.'
PY

xcodebuild -version
xcrun --sdk iphoneos --show-sdk-version
xcode_major="$(xcodebuild -version | awk '/^Xcode / {split($2, parts, "."); print parts[1]}')"
[[ "$xcode_major" =~ ^[0-9]+$ && "$xcode_major" -ge 26 ]] || {
  echo 'Select a complete Xcode 26 or newer installation before building.' >&2
  exit 1
}

brew install cmake xcodegen
export PATH="/opt/homebrew/opt/rustup/bin:$HOME/.cargo/bin:$PATH"
if ! command -v rustup >/dev/null 2>&1; then
  brew install rustup
  rustup-init -y --no-modify-path --default-toolchain none
fi
rustup toolchain install "${RUST_TOOLCHAIN:?}" --profile minimal
rustup target add aarch64-apple-ios --toolchain "$RUST_TOOLCHAIN"
rustup default "$RUST_TOOLCHAIN"
printf '%s\n' /opt/homebrew/opt/rustup/bin "$HOME/.cargo/bin" >> "$GITHUB_PATH"
rustc "+$RUST_TOOLCHAIN" --version
cmake --version
xcodegen --version
