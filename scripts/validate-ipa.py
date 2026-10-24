#!/usr/bin/env python3
"""Validate an upstream launcher-only IPA; requires macOS for signature checks."""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import plistlib
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_macho(data):
    """Parse the arm64 Mach-O header and load commands without third-party code."""
    require(len(data) >= 32, "Executable is shorter than a Mach-O header")
    header = struct.unpack_from("<IiiIIIII", data)
    magic, cpu, subtype, file_type, command_count, command_bytes, flags, reserved = header
    require(magic == 0xFEEDFACF, "Expected a thin little-endian 64-bit Mach-O executable")
    require(cpu == 0x0100000C, "Executable architecture must be arm64")
    require(file_type == 2, "Mach-O file type must be MH_EXECUTE")
    require(32 + command_bytes <= len(data), "Truncated Mach-O load commands")
    cursor, platforms, sections, encryption, entrypoint, signature = 32, [], [], [], False, False
    for _ in range(command_count):
        require(cursor + 8 <= 32 + command_bytes, "Truncated load command")
        command, size = struct.unpack_from("<II", data, cursor)
        require(size >= 8 and cursor + size <= 32 + command_bytes, "Invalid load command size")
        if command == 0x32:  # LC_BUILD_VERSION
            require(size >= 24, "Truncated LC_BUILD_VERSION")
            platform, minimum, sdk = struct.unpack_from("<III", data, cursor + 8)
            platforms.append({"platform": platform, "minimum_os": version(minimum), "sdk": version(sdk)})
        elif command == 0x19:  # LC_SEGMENT_64
            require(size >= 72, "Truncated LC_SEGMENT_64")
            number_sections = struct.unpack_from("<I", data, cursor + 64)[0]
            require(72 + 80 * number_sections <= size, "Truncated Mach-O sections")
            for index in range(number_sections):
                position = cursor + 72 + 80 * index
                section, segment = struct.unpack_from("<16s16s", data, position)
                pair = (segment.split(b"\0")[0].decode("ascii"), section.split(b"\0")[0].decode("ascii"))
                sections.append(pair)
        elif command == 0x2C:  # LC_ENCRYPTION_INFO_64
            require(size >= 24, "Truncated encryption information")
            crypt_id = struct.unpack_from("<I", data, cursor + 16)[0]
            encryption.append(crypt_id)
            require(crypt_id == 0, "Encrypted executables cannot be re-signed for sideloading")
        elif command == 0x80000028:  # LC_MAIN
            entrypoint = True
        elif command == 0x1D:  # LC_CODE_SIGNATURE
            require(size >= 16, "Truncated code signature command")
            offset, length = struct.unpack_from("<II", data, cursor + 8)
            require(length > 0 and offset + length <= len(data), "Code signature data is invalid")
            signature = True
        cursor += size
    require(cursor == 32 + command_bytes, "Mach-O command sizes do not match its header")
    require(platforms and all(item["platform"] == 2 for item in platforms), "Expected iOS device platform, not iOS Simulator")
    require(("__TEXT", "__text") in sections, "Executable has no __TEXT,__text section")
    require(("__GAME", "__code") not in sections, "Unexpected embedded game code in a launcher-only artifact")
    require(entrypoint, "Executable has no LC_MAIN entry point")
    require(signature, "Executable has no code signature")
    return {"architecture": "arm64", "format": "Mach-O 64-bit MH_EXECUTE", "platforms": platforms,
            "sections": [list(pair) for pair in sections], "encryption_ids": encryption,
            "embedded_game_code_section": False}


def version(value):
    return "%d.%d.%d" % (value >> 16, (value >> 8) & 255, value & 255)


def inspect_archive(ipa):
    with zipfile.ZipFile(ipa) as archive:
        require(archive.testzip() is None, "ZIP member failed its CRC check")
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate ZIP entries are not permitted")
        for entry in archive.infolist():
            name = pathlib.PurePosixPath(entry.filename)
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in entry.filename,
                    "Unsafe ZIP member path: " + entry.filename)
            require(not stat.S_ISLNK(entry.external_attr >> 16), "Unexpected symbolic link in launcher archive")
            require(not entry.filename.endswith((".wasm", ".cwasm")), "Unexpected game code file")
        candidates = [name for name in names if name.startswith("Payload/") and name.endswith(".app/Info.plist") and name.count("/") == 2]
        require(len(candidates) == 1, "IPA must contain exactly one Payload/*.app/Info.plist")
        info = plistlib.loads(archive.read(candidates[0]))
        app_root = candidates[0].rsplit("/", 1)[0]
        executable = info.get("CFBundleExecutable", "")
        require(isinstance(executable, str) and executable and "/" not in executable and "\\" not in executable,
                "Invalid CFBundleExecutable")
        require(info.get("CFBundlePackageType") == "APPL", "Bundle package type must be APPL")
        require(info.get("CFBundleIdentifier") == "ch.cclerc.muguet.ios", "Unexpected bundle identifier")
        require("$(" not in json.dumps(info), "Info.plist still contains unexpanded build settings")
        require(info.get("LSRequiresIPhoneOS") is True, "Bundle must require iOS")
        require("iPhoneOS" in info.get("CFBundleSupportedPlatforms", []), "Bundle platform must be iPhoneOS")
        require(1 in info.get("UIDeviceFamily", []), "Bundle does not support iPhone")
        require(app_root + "/embedded.mobileprovision" not in names, "Unexpected provisioning profile in ad-hoc build")
        path = app_root + "/" + executable
        executable_info = archive.getinfo(path)
        require(executable_info.external_attr >> 16 & 0o111 != 0, "Archived executable has no execute permission")
        report = inspect_macho(archive.read(path))
        report["bundle_identifier"] = info["CFBundleIdentifier"]
        report["bundle_version"] = info.get("CFBundleVersion")
        report["minimum_os_plist"] = info.get("MinimumOSVersion")
        return report, app_root, executable


def command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, check=False)
    require(result.returncode == 0, "Command failed: " + " ".join(arguments) + "\n" + result.stdout + result.stderr)
    return result.stdout + result.stderr


def validate_on_macos(ipa, app_root, executable):
    require(sys.platform == "darwin", "Full IPA validation requires macOS codesign, lipo, and otool")
    with tempfile.TemporaryDirectory(prefix="muguet-ipa-validation-") as folder:
        with zipfile.ZipFile(ipa) as archive:
            archive.extractall(folder)
            for entry in archive.infolist():
                mode = (entry.external_attr >> 16) & 0o777
                if mode:
                    os.chmod(pathlib.Path(folder, entry.filename), mode)
        app = str(pathlib.Path(folder, app_root))
        binary = str(pathlib.Path(app, executable))
        architecture = command(["xcrun", "lipo", "-archs", binary]).strip()
        require(architecture == "arm64", "lipo did not confirm a thin arm64 executable")
        verification = command(["codesign", "--verify", "--deep", "--strict", "--verbose=2", app])
        signature = command(["codesign", "-d", "--verbose=4", app])
        require("Signature=adhoc" in signature, "Expected upstream's ad-hoc signature")
        result = subprocess.run(["codesign", "-d", "--entitlements", ":-", app], capture_output=True, check=False)
        require(result.returncode == 0 and result.stdout, "Could not extract signed entitlements")
        entitlements = plistlib.loads(result.stdout)
        require(entitlements == {"com.apple.developer.kernel.increased-memory-limit": True},
                "Signed entitlements differ from upstream's sideload entitlements")
        return {"lipo": architecture, "file": command(["file", binary]), "codesign_verify": verification,
                "signature": signature, "entitlements": entitlements,
                "otool_load_commands": command(["xcrun", "otool", "-l", binary])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipa", type=pathlib.Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-directory", type=pathlib.Path, required=True)
    arguments = parser.parse_args()
    require(len(arguments.source_commit) == 40 and all(c in "0123456789abcdef" for c in arguments.source_commit), "Invalid source commit")
    report, app_root, executable = inspect_archive(arguments.ipa)
    report["macos_tools"] = validate_on_macos(arguments.ipa, app_root, executable)
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    (arguments.output_directory / "architecture-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "artifact": arguments.ipa.name,
        "artifact_kind": "Muguet launcher only; no game code or game assets",
        "size_bytes": arguments.ipa.stat().st_size,
        "sha256": hashlib.sha256(arguments.ipa.read_bytes()).hexdigest(),
        "upstream_repository": "https://github.com/c22dev/muguet",
        "upstream_commit": arguments.source_commit,
        "build_infrastructure_commit": os.environ.get("GITHUB_SHA"),
        "build_run": "https://github.com/{}/actions/runs/{}".format(os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_RUN_ID", "")),
        "validated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "architecture": "arm64", "target": "aarch64-apple-ios", "configuration": "Release",
        "signing": "ad-hoc; must be re-signed/provisioned with the user's sideloading tool",
        "automated_archive_and_signature_validation": "passed",
        "iphone_tested": False, "gameplay_available": False,
        "game_code_embedded": False, "game_assets_included": False,
        "runtime_requirements": ["iOS 15+", "valid iPhone provisioning/signature for installation"],
        "gameplay_requirements": ["A rebuild embedding a compatible, lawfully obtained web-port game.wasm", "Matching data/ and b/<build>/shaders/ assets"],
        "important_limit": "Importing data into this launcher-only IPA cannot add the missing precompiled game code; this IPA cannot play GTA V."
    }
    (arguments.output_directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
