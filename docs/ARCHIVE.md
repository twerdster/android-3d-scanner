# Archive, versions and validation

The [README](../README.md) introduces the scanning method and runnable results. This guide collects the archival and build details without making them the project’s opening narrative.

| Snapshot | Selected files | Scope |
| --- | ---: | --- |
| [Submitted Eclipse app](../source/) | 62 | Eleven Java classes, configuration/XML, 24 projection BMPs and eleven PNG resources |
| [Earlier Eclipse version](../versions/eclipse-2014/) | 54 | Alex Kligman’s `90ee4ef65ec90afa38a4798b6dd9ffaa29efd40d`, 23 February 2014; six Java classes |
| [Later Studio import](../versions/android-studio/) | 63 | Eleven Java classes, changed buffers/default dimensions, resources and historical Gradle descriptions |
| [Related iOS renderer](../related/ios-fusion/) | 1 | Incomplete Rom Herskovitz/Technion Objective-C++ fragment; not an Android version or restored app |

These 180 instances include repeated versioned files, not 180 distinct algorithms. The original 27 published source/configuration files remain unchanged. All imported bytes are enforced by [the recovery manifest](../recovery/manifest.json); provenance and exclusions are described in [RECOVERY.md](RECOVERY.md).

The submitted/earlier projection images are 360 × 640; Studio’s are 480 × 800. Their 24 patterns are synthetic projector inputs, not captured scenes or reconstruction results. New generated camera captures/results are separately labeled under `updated/`.

The submitted code projects/captures stripes, decodes Gray code, applies radial coordinate correction and solves camera/projector constraints for XYZ. Its interleaved points feed an OpenGL display; the `MeshViewActivity` name does not establish enabled triangle-mesh export. Historical diagnostic BMPs target external storage’s `Project/Decode/`. The capture/calibration setup expects `Project/config.xml` and `Project/calibration_CB_Ex.log`; real datasets/calibration, vendor libraries and SDK binaries are not part of the recovery.

## What was checked

- [Static integrity](../validation/static-checks.json): all 180 hashes, 104 image instances, XML/resources/activity mappings and a bounded public-text scan.
- [Historical build attempts](../validation/historical-build-attempt.json): concrete compiler/wrapper-entry diagnostics, including Android API 35; no historical APK produced. [BUILDABILITY.md](BUILDABILITY.md) lists missing dependencies and version disagreements.
- [Desktop numerical replay](../validation/numerical-tests.json): thirteen tests of actual unchanged submitted Java methods and an explicitly corrected path on independent geometry. [SIMULATION.md](SIMULATION.md) defines the scope and the clipping/median stage excluded from both comparisons.
- [New Android replay](../validation/android-independent-parity.json): 80,098 per-pixel comparisons, exact validity masks and separately recorded [UI actions](../validation/android-ui.json). This is supplied-capture replay, not physical camera/projector validation.

Offline archive verification:

```sh
python3 tools/verify_recovery.py
```

Original notices and scoped correspondence remain in the README. No blanket software or report license has been added. Source snapshots, the historical report, new synthetic outputs and the related lab poster retain distinct provenance.
