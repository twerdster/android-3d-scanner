# Structured-light replay: model, evidence and findings

The simulation is new 2026 work. It validates selected recovered numerical methods using supplied synthetic calibration and capture images. It does not restore a camera/projector workflow or reproduce a hardware experiment.

## Camera, projector and scenes

`updated/synthetic.py` forms camera rays from the recovered row/column coordinate convention. Scene geometry is intersected by those rays: an explicit plane, tilted plane, sphere with a background plane, two depth planes, or an opaque box. The camera takes the nearest surface. Projector visibility is evaluated independently by forward projection and, in the box scene, a segment/box intersection from projector center to surface. A 1e-12 normalized-coordinate tolerance retains analytically on-boundary rays despite floating-point roundoff.

The calibrated case rotates and translates both devices in world space. The distortion case additionally uses center `(0.04, -0.03)`, aspect `1.15` and radial coefficients `(0.92, 0.08, 0.015)`. Scene rays evaluate this model in polar coordinates; the decoder evaluates its Cartesian radial factor. A separately calculated test fixes a nominal ray, center/aspect/radial coefficients and the expected corrected coordinate, rather than only comparing two whole-pipeline outputs. Full matrices and per-scene parameters are in [the metrics file](../updated/results/metrics.json).

The virtual projector has 1,024 horizontal address positions and ten Gray bits. The camera receives a black reference, white reference, then bits from most to least significant. Intensities include spatially varying ambient level and contrast. The noise scene adds deterministic independent Gaussian intensity perturbations of standard deviation 3 in the 0–255 domain. Shadow/out-of-field pixels receive ambient intensity without projected modulation. Strong bit corruption deliberately inverts one captured stripe for selected illuminated pixels.

Default images are 64 × 48; the radial-center scene is 65 × 49. Geometry uses metres, a standard 0.12 m camera/projector baseline and a 0.72 m front plane. The transformed pair has its explicitly recorded different baseline. These virtual camera/projector resolutions and dimensions are chosen for an inspectable experiment, not asserted Galaxy Beam parameters. Photometry does not model a lens PSF, blur, saturation transport, materials, interreflection or rolling shutter.

## Recovered equations

The decoder accumulates a binary integer by prefix-XOR of the captured Gray bits. The source stores it as a weighted fraction `q / 2^bits`. Its camera correction maps nominal row/column coordinates through elliptical radius `rd` and `ru = k1 rd + k2 rd² + k3 rd³`.

The three reconstruction rows are:

```text
xc * C[2,:] - C[0,:]
yc * C[2,:] - C[1,:]
xp * P[2,:] - P[1,:]
```

The first three columns multiply XYZ and the fourth is the homogeneous constant. The projector uses its **second** projection row, consistent with the recovered calibration convention. The original code solves this 3 × 3 system by explicit cofactors. The Python correction uses pivoted elimination of the same constraints. Camera and projector matrices are 3 × 4 in row-major order; supplied calibration is not estimated.

## Findings retained as separate behaviors

- **Signed byte arithmetic:** the original casts reference and pattern differences back to Java `byte`. Valid positive differences above 127 wrap negative; the high-contrast fixture exposes this with all 1,024 Gray addresses. The new path subtracts unsigned 0–255 values.
- **Normalization:** the submitted twelve-capture path contains two references and ten Gray bits. Its scale uses `2^12` rather than `2^10`, yielding a fourfold decoded-pixel scaling discrepancy. Independent inspection of the submitted BMPs confirms that `calib1/2` are black/white, `calib3..12` encode horizontal addresses 0–359 using ten bits. The new scale uses the decoded integer and actual projector columns. This is an explicit behavior change. The separate Studio decoder defaults to ten textures, taking eight leading bits and ignoring the last two frames if its capture default remains twelve; its scale can represent coarse four-pixel addresses. That version-specific relationship is not tested or silently repaired here.
- **Visibility/confidence:** the original calculates `W` but does not reject by it. The new path rejects reference contrast below 10 levels and minimum bit distance from threshold below 0.1. It does not receive the visibility mask. Noisy dark pixels can therefore reveal false valid reconstructions in the historical mode while the new path rejects them.
- **Radial center:** the historical `ru/rd` division produces NaN at exact zero radius. The new path uses the analytic limit. A zero-baseline pair has no observable metric depth; invalid, singular or nonpositive projected-depth solutions are rejected.
- **Bit corruption:** a convincing wrong stripe can decode to a different address and leave a large, finite outlier. The new path does not claim to correct that error.

Neither comparison applies `Clear`'s hard coordinate interval `[-1,1]` or OpenCV's 5 × 5 median filter on Z alone. Historical diagnostics, point display, capture synchronization and calibration parsing are also outside the headless numerical execution. Exact original bytes remain enforced by the manifest.

## Validation and outputs

[Numerical tests](../validation/numerical-tests.json) cover independent geometric surface equations and world-to-device forward projection, the actual unchanged Java methods, all 1,024 unsigned Gray addresses, low contrast/noise/occlusion, center and calibration degeneracy, malformed binary/capture input and documented corrupt-bit failures. The oracle-coordinate test bypasses capture decoding and supplies exact projector forward projections to isolate triangulation; its micrometre-scale numerical error must not be advertised as end-to-end accuracy.

[Metrics JSON](../updated/results/metrics.json) records visible ground-truth counts, accepted coverage, 3D Euclidean RMSE, maximum/p95 error, wrong finite points outside illumination, integer-code agreement and reject reasons. A mode rejecting all points has `null` error. Coverage and dark-pixel acceptance remain visible beside survivor error metrics. It also records source, fixture and output hashes.

The report offers each scene's twelve captured frames, truth/historical/corrected depth and corrected error. Its interactive cloud switches modes and exports are provided as ASCII PLY. The [Android replay](../updated/android-replay/README.md) uses the same deterministic capture fixture and separately exports every pixel's result for independent comparison. Application build/runtime evidence must name the fixture hash, tool/device versions and measured comparison scope; the historical app remains separately blocked.

The [recorded Android comparison](../validation/android-independent-parity.json) passes 26 scene/modes and 80,098 pixel records with exact validity masks. Historical app-adaptation output is compared against the actual unchanged Java implementation, while corrected app output is compared against the independent Python path. The maximum coordinate difference divided by `max(1, abs(reference_coordinate))` is 2.14e-6, below the recorded tolerance 3e-5. It also checks a hand-specified center ray against a closed-form depth independent of scene-generation helpers. This establishes bounded numerical parity for the bundled captures, not camera/hardware or universal implementation equivalence.
