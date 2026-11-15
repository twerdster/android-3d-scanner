# Android synthetic capture replay

A dependency-free Java/Canvas Android app processes bundled synthetic grayscale captures through mechanically selected historical numerical methods and an explicitly corrected mode. It shows depth, rotatable point clouds and the actual capture intensities. Ground truth is separately selectable, and all views share the visible truth depth range. This is a supplied-calibration numerical replay, not a restored Galaxy Beam camera/projector app or calibration estimator.

Read [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md) for the preserved methods, source hash, coordinate conventions and exact corrections. Both modes omit historical coordinate clipping and OpenCV Z-only median filtering.

The parent simulation generator supplies `app/src/main/assets/replay.json` with schema `beam-replay-v1`. Each scene contains camera dimensions, projector columns, black/white plus Gray capture frames, radial parameters, row-major camera/projector 3×4 calibration, independent world XYZ ground truth, and the camera/projector visibility mask. Frames contain unsigned intensities; the historical mode deliberately converts them to Java byte buffers and retains the original wrapping bug.

Run the offline source check and use installed trusted tools to build outside the repository:

```sh
python3 updated/android-replay/verify_adaptation.py
python3 updated/android-replay/build.py --sdk "$BEAM_ANDROID_SDK" --output "$BEAM_ANDROID_OUTPUT"
```

The SDK must provide platform `android-35` and build tools `35.0.0`; a local JDK provides `javac` and `keytool`. The build uses `aapt2`, `javac`, `d8`, `zipalign` and `apksigner` directly. It downloads nothing. Android API 26+ is required. Output includes `beam-replay-debug.apk`, `build-report.json` and a task-owned disposable debug keystore; keep all of them outside version control. The app is explicitly debuggable for private test evidence extraction.

On a separately authorized emulator/device, select the explicit serial for every command:

```sh
adb -s "$BEAM_SERIAL" install -r "$BEAM_ANDROID_OUTPUT/beam-replay-debug.apk"
adb -s "$BEAM_SERIAL" shell am start -n org.technion.beamreplay/.ReplayActivity
adb -s "$BEAM_SERIAL" exec-out run-as org.technion.beamreplay cat files/replay-results.json
```

The activity immediately decodes every scene in both modes and writes metrics to its private `files/replay-results.json` and per-pixel coordinates to `files/replay-points.json`. Both record the bundled fixture SHA-256 for independent comparison. The Replay button recomputes them from the capture intensities. Optional integer launch extras `scene`, `mode` (0 historical, 1 corrected, 2 truth), and `view` (0 depth, 1 cloud, 2 observations) select reproducible screenshots. The slider chooses the displayed capture. No account, internet, camera or shared-storage permission is used.

Scoring reports accepted and rejected visible truth points, 3D Euclidean RMSE/max error for accepted visible points, and finite reconstructions outside the visibility mask. A mode that rejects everything has undefined error (`null`) and zero accepted coverage; it cannot pass by reporting zero RMSE. These metrics are a bounded synthetic experiment. They do not establish hardware accuracy, robustness to every material or lighting condition, or equivalence to the old full app.

The manual build, 13-scene Android emulator run, independent comparison of all 80,098 scene/mode pixel results and emulator UI interaction checks passed. Exact artifact identities, numerical bounds, tested controls, observed results and scope limits are in [VALIDATION.md](VALIDATION.md).
