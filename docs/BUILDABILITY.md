# Buildability and validation scope

These recovered versions are preserved unchanged. A real untouched-source build attempt is now recorded below; the historical Android application remains blocked. A separately maintained replay application and desktop numerical harness live in `updated/`. Their execution does not establish a restored historical APK or camera/projector capture. Do not execute archived binaries as inspection tools.

| Version | Recorded configuration | Missing or unresolved requirements |
| --- | --- | --- |
| `source/` | Eclipse/ADT, package `com.project`, project target API 11, manifest minimum API 8 / target API 11. Project properties reference OpenCV Library 2.4.4; startup requests OpenCV Manager 2.4.3. | OpenCV/support-library setup; external `Project/config.xml` and `Project/calibration_CB_Ex.log`; device geometry and calibrated capture. Version mismatch is preserved. |
| `versions/eclipse-2014/` | Eclipse/ADT, package `com.example.dv1`, project target API 11, manifest minimum API 8 / target API 11. Six-class earlier implementation. | A complete historic Android toolchain/build description and calibrated hardware inputs. Generated resource classes are intentionally absent. |
| `versions/android-studio/` | Android Gradle plugin 1.3.0, Gradle distribution 2.2.1, compile SDK 18, build tools 21.1.2. Gradle minimum API 8 / target API 10, while the copied manifest targets 11. | `openCVLibrary2410` (app dependency), additional `openCVLibrary246` listed in settings, binary Gradle wrapper JAR, referenced `app/proguard-rules.txt`, SDK configuration and calibration/capture inputs. Startup still requests OpenCV 2.4.3. |
| `related/ios-fusion/` | Objective-C++ / OpenGL ES renderer fragment. | Companion headers/shaders, application code, data and project configuration. Not independently buildable. |

The Android Studio `jcenter()` repositories and original wrapper/build descriptions are historical records. Their presence is not a verified dependency-resolution command. No dependencies were downloaded or installed for this recovery, and archived wrapper/build scripts were not executed.

## Checks actually performed

- SHA-256 and byte-count verification for every file in the 180-file recovery manifest; all original bytes match.
- XML parsing for 30 Android resource files and three manifests; local Java `R.*` references and declared activity-to-source mappings resolve in all three versions.
- Header/structure checks for 104 PNG/BMP instances. PNG CRCs and textual-metadata restrictions are checked. Full image decoding and visual inspection additionally reviewed all distinct resources.
- A bounded public-text scan for concrete private-key/token forms, credential assignments, machine-specific user paths and local/private endpoints found no matches. This is an explicit limited scan, not a guarantee that every possible secret format is detectable.
- OpenJDK 21.0.11 compiled five pure-Java helper file instances in three isolated invocations: `CalibrationFile` in each version, and `Quaternion` in submitted/Studio versions. All exited zero without diagnostics. This checks those helper classes only; it supplies no Android/OpenCV linking or algorithm/runtime evidence.

Results: [static-checks.json](../validation/static-checks.json) and [java-helpers.json](../validation/java-helpers.json). Reproduce the offline static checks from the repository root:

```sh
python3 tools/verify_recovery.py
```

To repeat the submitted helper compilation with a local JDK, choose an output directory outside the source tree:

```sh
javac -d /path/to/output \
  source/src/com/project/logic/CalibrationFile.java \
  source/src/com/project/mesh/logic/Quaternion.java
```

Use the corresponding Studio or earlier Eclipse paths for their separate helper checks. Do not combine identically named classes from different snapshots in one invocation.

A standard-path Android SDK was unavailable during the original recovery checks. The later application-validation work installed a task-scoped SDK and made concrete build attempts without modifying the historical sources.

## Later build and replay attempts

[historical-build-attempt.json](../validation/historical-build-attempt.json) records trusted Java/`javac` invocations. The original Studio wrapper entry fails because its wrapper JAR is absent; required OpenCV modules and the referenced ProGuard file are also absent. Compiling submitted sources against installed Android API 35 still fails on missing OpenCV classes and resource-generated `R` classes. Resource generation, a restored historical Gradle/ADT toolchain and the external OpenCV modules are unresolved; no historical APK is produced. The API 35 attempt replaces the earlier environment-only SDK limitation with actual diagnostics. The old Gradle scripts and archived binaries were not executed.

[headless-build.json](../validation/headless-build.json) records successful compilation of the unchanged submitted `Reconstructor.java` and `CalibrationFile.java` with new compile-only desktop shims. Four private numerical methods run in the JVM on independent ray-generated capture fixtures. This uses no Android or OpenCV runtime and deliberately stops before clipping/median postprocessing. The [simulation guide](SIMULATION.md) details corrections, ground-truth errors and limits.

The new [Android replay app](../updated/android-replay/README.md) has its own direct SDK build, assets, source-body provenance check and supplied-calibration scope. It has no camera/projector or network permission. Keep its build and device validation distinct from historical source preservation and from real hardware reconstruction accuracy.
