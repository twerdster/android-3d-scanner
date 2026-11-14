# Android 3D scanner recovery context

Read this file before SKILL.md. Updated 2026-11-14.

This repository archives the Galaxy Beam/prism structured-light student project credited to Arkadi Godlin and Alex Kligman, lab engineer Alon Zvirin and supervisor Aaron Wetzler. Publication base is `d35bac0012fc479d98fe06ac8e2538a24704b4da`; preserve its Alex Kligman correspondence paragraph and preview image.

Recovery now contains 180 original file instances / 70,600,050 bytes: submitted Eclipse `source/` 62, earlier `versions/eclipse-2014/` 54, later `versions/android-studio/` 63 and a separately labeled related iOS renderer 1. These counts include repeated versioned configuration/resources. The 27 previously published `source/` files are unchanged; 35 RAR image resources were added. All original imported bytes remain unchanged and are hashed in `recovery/manifest.json`.

Independent review matched all 180 published files to their original archive members/Git blobs/backup files and found no concrete secret/private-path/private-endpoint issue in the bounded publication scan. Detailed private evidence remains outside this repository. `.gitattributes` preserves original line endings/whitespace; only original snapshot paths have whitespace exceptions, while hashes enforce their exact bytes.

The earlier Git snapshot is Alex Kligman's `90ee4ef65ec90afa38a4798b6dd9ffaa29efd40d` (2014-02-23). The later Studio import's modification authorship is not established. The related renderer header credits Rom Herskovitz/Technion; backup colocation is its limited relationship evidence, not an assertion that it is the same Android scanner or a restored iOS app.

`docs/RECOVERY.md` records selection/provenance and exclusions. Raw XYZ/capture/calibration datasets, dependency/SDK binaries, wrapper JAR, generated outputs, local SDK/IDE state and signing-bearing Xcode configuration stay excluded. No original file content was sanitized; excluded files were not copied into replacements. Preserve existing notices, third-party references and no-blanket-license wording.

`tools/verify_recovery.py` performs offline manifest hashes, image structure/CRC/metadata, XML/resource/activity mapping and bounded public-text checks. Results are in `validation/static-checks.json`. All 104 image instances were decoded, and all 53 unique hashes were visually reviewed as synthetic projection/solid-color patterns and icons. PNG text is limited to historical creation/modification timestamps.

Five pure-Java helper instances compile with OpenJDK 21.0.11; see `validation/java-helpers.json`. Android SDK was unavailable at the checked standard paths; complete app compilation, APK/device execution, OpenCV linking and reconstruction accuracy remain unverified. Original build descriptions/version mismatches are documented, not repaired. No modernization, dependency installation or runtime claim is part of this recovery.

Before any commit, reread and synchronize SUMMARY.md and SKILL.md, rerun the static verifier and inspect the exact staged files. The independent source/publication review passed. The canonical repository remains `twerdster/android-3d-scanner` on `main`; use normal commits and verify the public commit/tree after publishing. The original source repositories/backups remain read only. Keep private recovery locations and raw correspondence outside the public repository.
