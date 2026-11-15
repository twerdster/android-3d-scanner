# Numerical source and explicit changes

The historical algorithm in this replay comes from the submitted Galaxy Beam/prism scanner, credited to Arkadi Godlin and Alex Kligman, with lab engineer Alon Zvirin and supervisor Aaron Wetzler. The archived source is [`../../source/src/com/project/logic/Reconstructor.java`](../../source/src/com/project/logic/Reconstructor.java), SHA-256 `720351709b2c5f6219cf2779ff5bef7c09380d934d601b1625b966e9e972ad4b`.

`HistoricalNumerics.java` mechanically selects four method bodies: `DecodeGraySimpleBW` (original lines 105–139), `NormalizeDecodedValues` (141–158), `CorrectOpticalDistortionCPU` (160–196), and `ReconstructCPU` (213–258). Their Java statements, constants, arithmetic order, casts and logging are retained; line endings and trailing whitespace are normalized. A small constructor replaces application globals with supplied synthetic capture/calibration data. `verify_adaptation.py` checks the original file hash and all four method bodies, ignoring whitespace. These methods retain their historical authorship and terms; this adaptation does not assign them a new license.

Both replay modes stop before the historical `Clear` and OpenCV Z-only 5×5 median. The old application clips each coordinate to `[-1,1]` and filters only Z, which is not an appropriate metric bound for arbitrary synthetic metric scenes. Neither action is simulated or described as an exact full-application replay. Original camera capture, timing, external calibration-file loading and hardware projection are also outside this app.

`CorrectedNumerics.java` explicitly changes observation decoding and guards while reusing the historical scalar triangulation:

- Unsigned 8-bit differences replace signed-byte wrapping.
- The prefix-XOR Gray decoder produces an integer from `pattern_count - 2` captured bits. Its normalized projector coordinate is `2 * integer / (projector_columns - 1) - 1`, removing the historical factor-four scale mismatch.
- Reference contrast below 10 intensity levels and normalized Gray bits within 0.1 of the decision threshold are rejected. These thresholds are explicit synthetic-test choices, not historically recovered calibration parameters.
- Radial scaling uses the analytic center limit. A scale-invariant normalized determinant below `1e-7`, nonfinite/malformed calibration, singular camera/projector left 3×3 matrices, and zero radial aspect scale are rejected. Reconstructed points must have finite coordinates and positive camera/projector projected depths. Zero baseline produces a degenerate triangulation and is rejected.

Camera pixel coordinates retain the historical row/column normalization. Calibration arrays are row-major 3×4 matrices; camera constraints use rows 0/1, and the projector stripe coordinate uses row 1. These conventions must match the independent forward renderer. The fixture provides the true calibration; the replay does not estimate camera/projector calibration or claim to validate its estimation.

The factor-four finding is scoped to the submitted default 12-capture path and these fixtures: black/white plus all ten Gray bits. It is not a claim about every historical configuration. The later Studio decoder defaults to ten textures, taking only eight leading bits of its ten-bit texture bank; the Studio capture class still defaults to twelve images. With those defaults, the decoder ignores the final two captures, and its existing `2^10` scaling can represent coarse coordinates `4 * floor(projector_x / 4)`. That different capture/pattern relationship is not replayed or silently repaired here.

The UI, fixture loading, explicit corrected preprocessing, scoring and manual build tool are new support code. No blanket license is introduced. The app includes no vendor SDK, old binary, captured data, signing key, account connection, or network/camera permission.
