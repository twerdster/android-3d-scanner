# Android replay validation

Checked on 2026-11-15. The scope is the numerical stage before historical coordinate clipping and OpenCV Z-only median filtering, using supplied synthetic calibration and observations. No physical scanner, camera capture, calibration estimation or historical Android application is validated here.

The offline adaptation verifier passes the archived file SHA-256 and all four selected method bodies, ignoring whitespace. Six authored Java source files plus generated `R.java` compiled with OpenJDK 21.0.11 against Android API 35. The manual build used Android build tools 35.0.0; `apksigner` verified APK v2 and v3 signatures. The APK requires API 26+ and targets API 35. Compilation reports obsolete Java 8 source/target options and a deprecated display-density accessor; there were no build errors.

The debug APK installed and launched on a task-owned Android 14/API 34 ARM64 emulator. It decoded all 13 bundled scenes and exported both aggregate metrics and each reconstructed coordinate. The output records the fixture hash. The default corrected plane depth screen was visually inspected for readable labels, metrics and rendering.

Independent review compared every pixel in all 26 scene/mode combinations: 80,098 pixel results. Finite/invalid masks agreed exactly. Historical mode was compared with the unchanged archived class executed by the desktop JVM; corrected mode was compared with the separately implemented Python pivoted solver. The maximum coordinate difference divided by `max(1, abs(desktop_coordinate))` was `2.1375343537410885e-6`, below the stated `3e-5` bound. A separately hand-specified center-ray/Gray-integer-426 case also matched its closed-form depth without using the scene generator helper. These comparisons bind to the exact fixture and APK hashes below.

Independent emulator UI checks also passed: selecting Historical showed the actual plane result of 576/2256 accepted points; selecting Corrected, sphere and Point cloud changed the displayed scene, and dragging visibly rotated it. Observation mode and the slider selected capture 7/12, Gray bit 5. Force-stop/relaunch and Replay reproduced the numerical metrics exactly. Screenshots and a screen recording were retained as private validation evidence. This was an emulator test, not a physical Galaxy Beam, camera or projector test.

Validated artifact identities:

- Fixture SHA-256: `adb86d2045a383883b568c5d7a7d7bd669d9e50e231c491490daa84cba9c8585`.
- APK SHA-256: `de5fda95a802584232b549806db4e86faddd2b825f57faafb2fadac1e7285b15`.

Representative actual Android results, in metres:

| Scene | Corrected accepted / visible | Corrected 3D RMSE | Historical accepted / visible | Historical 3D RMSE |
| --- | ---: | ---: | ---: | ---: |
| Plane | 2256 / 2256 | 0.00317848 | 576 / 2256 | 2.10719 |
| Sphere plus background | 2256 / 2256 | 0.00539048 | 576 / 2256 | 27.43947 |
| Rotated/translated calibration | 1963 / 1963 | 0.00388833 | 471 / 1963 | 5.27550 |
| Nonlinear radial correction | 1904 / 1904 | 0.00365649 | 459 / 1904 | 3.60159 |
| Bright reference contrast | 2256 / 2256 | 0.00317848 | 0 / 2256 | Undefined |
| Low reference contrast | 0 / 2256 | Undefined | 576 / 2256 | 2.10719 |
| Corrupted Gray bit | 2247 / 2256 | 0.47663811 | 576 / 2256 | 2.08202 |
| Zero baseline | 0 / 2304 | Undefined | 528 / 2304 | 0.99771 |

All 13 corrected scenes returned zero finite points outside the supplied visibility mask. The corrupted-bit case still produces severe outliers: unsigned handling, confidence checks and geometry guards do not add Gray-code error correction. Undefined error with zero accepted points must be interpreted alongside coverage. Clean-scene millimetre errors include quantized projector stripe locations; they are not measurements of physical device accuracy.

The signed APK, disposable signing key, emulator state, build intermediates, full exported coordinates and screenshots remain task-owned validation outputs outside the repository. The source build command regenerates a newly signed APK; its byte hash can differ because of signing key and ZIP timestamps. Do not publish the private debug key.
