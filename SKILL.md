# Maintain the recovered Android scanner

Read SUMMARY.md, then this file, README.md, docs/RECOVERY.md, docs/BUILDABILITY.md and the manifest before changes. Preserve the original student credits, Alex Kligman's scoped correspondence paragraph and preview-image bytes.

Keep the three Android snapshots separate: `source/` is the submitted Eclipse snapshot, `versions/eclipse-2014/` is commit `90ee4ef65ec90afa38a4798b6dd9ffaa29efd40d`, and `versions/android-studio/` is the later import. Preserve all 27 originally published source files. Do not merge historical algorithm changes or modernize dependencies silently. Explain newly recovered versions and report original hashes plus any explicit sanitization.

Preserve `.gitattributes` for original snapshot paths so checkout/formatting cannot silently change archived CRLF, trailing spaces or mixed indentation. The manifest verifies their exact bytes; new documentation and tooling keep normal whitespace checks.

`related/ios-fusion/` is one incomplete renderer with its own header attribution/notice. It is not an Android variant or a runnable iOS scanner. Preserve that limited relationship and the no-new-license wording. Do not copy personal signing configuration to make the fragment appear complete.

Use `recovery/manifest.json` as the selected-file allowlist. No raw archives, Git bundles/configuration, email identifiers, private endpoints, local SDK paths, signing/key material, dependency binaries, generated source/classes/build outputs or captured/raw XYZ data belong in public commits. Synthetic pattern/icon resources are included with original bytes and their version-specific dimensions; preserve their existing provenance and terms. Keep further private evidence outside the repository.

Run `python3 tools/verify_recovery.py` after recovery changes and save its result under validation/. It checks original bytes, source-tree allowlists, images, XML/resources/activity declarations and concrete public-text risks. If an original file is intentionally sanitized, record original/current hashes, exact reason and scope; update the verifier deliberately instead of hiding mismatches. For changed media, decode/inspect all newly distinct resources and metadata. Link validation results without implying hardware or reconstruction accuracy.

Pure-Java helpers can be compiled with a trusted local JDK into an external output directory. Keep variants in separate invocations. Do not run archived build scripts or binaries as inspection tools. A full app build requires explicit restoration work, compatible Android/OpenCV dependencies and recorded tool versions; successful helper compilation is not an APK or camera/projector test. Preserve failed/blocked checks and dependency-version disagreements.

Before every commit reread and synchronize SUMMARY.md and SKILL.md, run the static verifier, check all README/docs links and `git diff --cached --check`, inspect newly staged files and verify the original 27 source hashes. Preserve unrelated changes and use normal history; no archive/source history rewrite. Use `twerdster/android-3d-scanner` on `main` as the canonical repository. Verify a permitted publishing identity before account operations and read back the public commit/tree after pushing. Keep website source/resources/version links synchronized with the published structure.
