# Historical source recovery

Recovered on 14 November 2026 from preserved project backups. No original implementation or resource bytes were edited. [manifest.json](../recovery/manifest.json) lists every included original file, its byte count, SHA-256, source member/path, and Git blob/commit where applicable. Private archive locations, email identifiers and original Git configuration are not part of this repository.

## Submitted Eclipse snapshot

`source/` contains 62 files selected from `3Dscanner.rar` (5,487,636 bytes; SHA-256 `818286352a7695f255c9cb5f5c777888c349bf191769ec0918cbd07bcee92c4f`). The 27 previously published Java/XML/configuration files retain their exact bytes. Recovery adds 24 projection BMPs and 11 PNG images, including the web icon, density-specific launcher icons and solid-color resources. It preserves the complete selected Java/XML/configuration/image set rather than only the 16 top-level/class files recovered in an initial extraction.

The archive has copies in the original Beam backup, the historic project-web directory and a previously recovered email attachment. Their archive hashes match. Captured/calibration data, raw `res/raw/x`, `y`, `z` arrays, generated `bin`/`gen` content, library JARs, repository internals and IDE state are omitted. Those omissions are not missing authored Java classes.

## Earlier Git version

`versions/eclipse-2014/` comes from commit `90ee4ef65ec90afa38a4798b6dd9ffaa29efd40d`, dated 23 February 2014, subject “Latest working”. The four reachable historical commits name Alex Kligman as author. A private full-history integrity check passed; the original Git bundle and author email/configuration are not published here.

This snapshot uses package `com.example.dv1` and six Java implementation files. The submitted snapshot uses `com.project` and 11 classes, including mesh display classes. Files differ beyond newline style, so the earlier version is retained as its own tree instead of replacing the submission. The 54 selected files contain Java, XML, project descriptions and 35 images; generated `R.java`/`BuildConfig.java`, binaries and libraries are excluded.

## Android Studio import

`versions/android-studio/` preserves selected files from `AndroidStudioImport/3D` in the same Beam backup. Its app uses the same 11 class names as the submitted layout, with changed capture buffers, normalization and other source differences. Modification authorship/date are not inferred from folder placement or timestamps. The original student-project credits remain the historical credits; they do not assign every later edit to those students.

The 63 files include all selected app Java/XML and top-level drawable images, three Gradle descriptions, wrapper properties, and two wrapper scripts. The wrapper JAR, OpenCV module contents, generated output, local SDK properties and IDE state remain excluded. Two nested alternative pattern directories were omitted: `calib_800_480` duplicates the top-level Studio patterns and `calib_640_360` duplicates the submitted version's patterns. The selected pixel bytes are unchanged; no images were resized or transposed.

## Related iOS renderer

`related/ios-fusion/viewer/FusionRenderer.mm` is a single renderer implementation found under the backup's separate `Fusion` directory. Its header names Rom Herskovitz, 8 August 2014, and Technion copyright. It contains OpenGL ES volume/depth/ICP processing and references absent `FusionRenderer.h`, `Shaders.h`, `Consts.h` and depth input data.

Colocation alone does not demonstrate that it implements Galaxy Beam structured-light capture. It is labeled a related fragment, not a fourth Android version, a runnable app, or code by the Android student authors. The signing-bearing Xcode project and datasets are omitted; no signing values were copied into a sanitized replacement.

## Review and preservation

All 180 included original files retain their recorded hashes and `transformation: none`. `.gitattributes` disables text conversion and trailing-space/mixed-indentation checks only for original snapshot files, preserving their historical CRLF and whitespace; the manifest enforces exact bytes and new documentation keeps normal whitespace checks. No original file needed content sanitization. Instead, local properties, signing-bearing configuration, dependency binaries, raw arrays and private evidence were excluded entirely. The public manifest records only relative historical source paths.

The 104 image instances were decoded and a contact sheet of all 53 distinct image hashes was reviewed: synthetic stripe/solid-color patterns and application/launcher icons. PNG textual chunks contain only historical creation/modification timestamps; these are retained and strictly checked by the verifier. This review does not establish new licensing for launcher artwork. Existing third-party code comments and notices remain intact.
