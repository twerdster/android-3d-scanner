# Run the Beam scanner calculations

This new replay path runs the recovered scanner's numerical methods on generated structured-light captures. Camera rays intersect known planes, a sphere, a depth step and an opaque box; an independent virtual projector illuminates those surfaces with Gray-coded stripes. The resulting byte images go through both the **unchanged historical Java calculations** and an **explicitly corrected adaptation**.

The [interactive report](results/index.html) contains rotatable point clouds, captured-stripe montages, reconstructed/ground-truth depth and error images. [PLY point clouds](results/plane.ply), [CSV metrics](results/metrics.csv) and [full conditions and hashes](results/metrics.json) make the output inspectable outside the app.

## Quickstart

The desktop path needs Python **3.10+** and a JDK with `java` and `javac` on PATH. It uses only the Python and Java standard libraries; no pip installation, Android SDK, OpenCV, Gradle, camera or emulator is required.

Run from the repository root:

```sh
python3 updated/run_checks.py
python3 -m updated.cli simulate --output updated/results
```

Open `updated/results/index.html` in a browser. It is self-contained except for the adjacent montage PNGs and metrics link; no server or network access is required. Drag to rotate the point cloud and use the mouse wheel to zoom. PLY coordinates and all error metrics are in **virtual metres**, with a 0.12 m baseline for the standard scenes; these units do not establish the units of any missing historical calibration.

The [new Android replay application](android-replay/README.md) displays the same capture sequences, historical/corrected point clouds, depth, ground truth and measured errors. It is a separately built Java/Canvas app, not a restored historical Galaxy Beam APK. Its direct SDK build and emulator commands are in that guide.

The final fixture was built and executed on an Android 14 ARM64 emulator. [Independent pixel comparison](../validation/android-independent-parity.json) covers both modes across all 13 scenes: **80,098 pixels**, exact validity masks and maximum scaled coordinate difference **2.14e-6**. The historical Android adaptation is compared with the actual unchanged desktop Java class; corrected Android output is compared with the independent Python path. [Build evidence](../validation/android-replay-build.json) and [on-device metrics](../validation/android-replay-results.json) retain the fixture binding. These are numerical replay results, separate from UI interaction and hardware validation.

To regenerate its complete deterministic fixture alongside the desktop report:

```sh
python3 -m updated.cli simulate --output updated/results \
  --android-asset updated/android-replay/app/src/main/assets/replay.json
```

After exporting the app's private `replay-points.json`, repeat the comparison with existing compiled headless classes:

```sh
python3 -m updated.compare_android --android-points /path/to/replay-points.json
```

Do not rebuild the shared headless classes while another comparison is running.

## What actually executes

[build_headless.py](build_headless.py) compiles the **original `source/` Reconstructor.java and CalibrationFile.java directly**, without editing or copying their method bodies. It checks their hashes against the recovery manifest before compiling. New compile-only Android/OpenCV shims supply constructor inputs; unavailable capture/UI/OpenCV methods throw if invoked. [BeamHeadless.java](headless/BeamHeadless.java) invokes only `DecodeGraySimpleBW`, `NormalizeDecodedValues`, `CorrectOpticalDistortionCPU` and `ReconstructCPU` through reflection. The original arithmetic therefore executes in the JVM, rather than being approximated by the Python reference.

Both comparison modes stop before the original `Clear` coordinate clipping and OpenCV Z-only median filtering. Those operations would change point acceptance and boundary behavior and have not been reproduced here. The Android adaptation separately verifies the selected original method bodies against the same source. [Build evidence](../validation/headless-build.json) and [Android method provenance](android-replay/SOURCE_PROVENANCE.md) record this scope.

The corrected path retains prefix-XOR Gray decoding, the radial-coordinate model and the original three camera/projector projection constraints. It explicitly changes unsigned image differences, decoded-bit normalization, contrast/confidence rejection, the radial-center limit, singularity guards and positive camera/projector depth checks. Calibration and capture array shapes/ranges must also be valid. See [the detailed model and findings](../docs/SIMULATION.md).

## Results and limitations

Thirteen deterministic scenes cover front/tilted planes, sphere/background, depth step, rotated/translated camera/projector calibration, nonlinear radial correction with nonzero center and aspect, geometric projector shadows, 3-level intensity noise, high/low contrast, corrupted Gray bits, zero baseline and the exact radial center. Ground-truth visibility is used for scoring, never for deciding whether to reconstruct a pixel.

At the published 64 × 48 camera resolution and 10-bit virtual projector resolution, the corrected path retains every illuminated point in the clean geometric scenes. 3D RMSE is **3.18 mm** for the 0.72 m front plane, **3.45 mm** for the tilted plane, **5.39 mm** for sphere/background, **3.89 mm** for rotated/translated calibration and **3.66 mm** with nonlinear radial correction. These errors include stripe-coordinate quantization. The shadow case has no accepted unilluminated points. Low-contrast and zero-baseline scenes correctly return no valid depth; their error is undefined, not zero.

The unchanged submitted path exposes signed-byte overflow and a factor-of-four projector-coordinate scaling discrepancy in this black/white-plus-ten-bit capture convention. This finding is not generalized to Studio's different capture/decoder defaults. An isolated test supplies exact forward-projected coordinates to the unchanged triangulation, recovering independently generated geometry to within **20 micrometres** over the tested full field of view; this is a numerical-method check with oracle inputs, not achieved scanner accuracy.

Strongly corrupted Gray bits can still look certain and produce large outliers: the published corruption case has roughly **0.477 m RMSE**. This decoder is not an error-correcting code. No claims are made about arbitrary image noise, blur, interreflection, reflective/translucent materials, calibration estimation, inter-frame motion, real capture, the Galaxy Beam prism/projector or hardware accuracy.

[Thirteen tests](../validation/numerical-tests.json) check the actual original Java methods, independent ray/surface geometry, every 10-bit code across the unsigned-byte boundary, calibration and malformed-input guards, geometric occlusions, noise, degenerate cases and the documented outliers. Original source hashes and historical build attempts remain separate from the new application and simulation validation.

[Android UI checks](../validation/android-ui.json) also exercised historical/corrected mode selection, sphere point-cloud rotation, actual captured-frame browsing and force-stop/relaunch/replay reproducibility. They validate the new replay interface, not physical capture.

No blanket license has been added to historical algorithms or their adaptations. Preserve the original project credits and third-party notices. New replay software and generated scenes are labeled separately from archived source and physical results.
