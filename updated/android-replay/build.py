#!/usr/bin/env python3
"""Build the task-owned replay APK using explicit installed Android/JDK tools.

No downloads, dependency resolution, account operations, device operations or archived
build scripts. Outputs and the disposable debug signing key stay outside the repo.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def run(args):
    subprocess.run([str(item) for item in args], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--build-tools", default="35.0.0")
    parser.add_argument("--platform", default="android-35")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output.expanduser().resolve()
    if output == root or root in output.parents:
        parser.error("Build output must be outside the repository")
    sdk = args.sdk.expanduser().resolve()
    tools = sdk / "build-tools" / args.build_tools
    android = sdk / "platforms" / args.platform / "android.jar"
    javac, keytool = shutil.which("javac"), shutil.which("keytool")
    if not javac or not keytool:
        parser.error("A trusted local JDK with javac/keytool must be on PATH")
    for item in [tools / name for name in ("aapt2", "d8", "zipalign", "apksigner")] + [android]:
        if not item.is_file():
            parser.error(f"Missing explicit SDK tool/input: {item}")
    asset = root / "app/src/main/assets/replay.json"
    document = json.loads(asset.read_text())
    if document.get("schema") != "beam-replay-v1" or not document.get("scenes"):
        parser.error("Generate the validated synthetic replay.json first")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("classes", "generated", "dex"):
        location = output / name
        if location.exists():
            shutil.rmtree(location)
        location.mkdir()
    resources = output / "compiled-resources.zip"
    unsigned = output / "resources.apk"
    run([tools / "aapt2", "compile", "--dir", root / "app/src/main/res", "-o", resources])
    run([tools / "aapt2", "link", "-I", android, "--manifest", root / "app/src/main/AndroidManifest.xml",
         "--java", output / "generated", "-A", root / "app/src/main/assets", "-o", unsigned])
    sources = sorted((root / "app/src/main/java").rglob("*.java")) + sorted((output / "generated").rglob("*.java"))
    run([javac, "-encoding", "UTF-8", "-source", "8", "-target", "8", "-bootclasspath", android,
         "-d", output / "classes", *sources])
    classes = sorted((output / "classes").rglob("*.class"))
    run([tools / "d8", "--lib", android, "--min-api", "26", "--output", output / "dex", *classes])
    # zipfile appends only fresh dex, leaving the aapt2-generated manifest/resources intact.
    import zipfile
    with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as package:
        for dex in sorted((output / "dex").glob("*.dex")):
            package.write(dex, dex.name)
    aligned = output / "beam-replay-aligned.apk"
    run([tools / "zipalign", "-f", "-p", "4", unsigned, aligned])
    key = output / "task-debug.keystore"
    if not key.exists():
        run([keytool, "-genkeypair", "-keystore", key, "-storepass", "android", "-keypass", "android",
             "-alias", "task-debug", "-keyalg", "RSA", "-keysize", "2048", "-validity", "365",
             "-dname", "CN=Local Synthetic Replay Debug,O=Task Validation,C=XX"])
        key.chmod(0o600)
    apk = output / "beam-replay-debug.apk"
    run([tools / "apksigner", "sign", "--ks", key, "--ks-key-alias", "task-debug",
         "--ks-pass", "pass:android", "--key-pass", "pass:android", "--out", apk, aligned])
    run([tools / "apksigner", "verify", "--verbose", apk])
    report = {"schema": "beam-replay-build-v1", "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
              "fixture_sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
              "source_java_files": len(sources), "build_tools": args.build_tools, "platform": args.platform,
              "min_api": 26, "target_api": 35, "device_execution": False,
              "signing": "task-owned disposable debug key outside repository"}
    (output / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(apk)


if __name__ == "__main__":
    main()
