# 3D Scanner on Android

Turn a phone and projector into a structured-light 3D scanner. A **Samsung Galaxy Beam**, fitted with a right-angle reflecting prism, projects coded stripes into its camera’s field of view. Decoding those stripes identifies a projector coordinate for each camera pixel; calibrated triangulation recovers the surface.

Students: Arkadi Godlin, Alex Kligman. Lab engineer: Alon Zvirin (historical website spelling: Alon Zivrin). Supervision: Aaron Wetzler.

![Actual synthetic capture sequence, decoded depth and rotating reconstructed clouds for a sphere, depth step and projector shadow](assets/beam-reconstruction.gif)

**New synthetic replay:** sphere, depth step and projector shadow, reconstructed from generated captures with supplied calibration. The corrected path has 3.1–5.4 mm RMSE in these scenes; this is software simulation, not measured Galaxy Beam accuracy. [Interactive results and PLY clouds](updated/results/index.html) · [Full conditions and limitations](docs/SIMULATION.md).

## How it works

1. **Project and capture.** Display a sequence of Gray-code patterns and photograph each one with software synchronization.
2. **Decode correspondence.** Recover the stripe address at each illuminated camera pixel.
3. **Triangulate.** Intersect its camera ray with the calibrated projector plane, then display the resulting XYZ points.

The [original student report](docs/mobile-3d-scanner-report.pdf) explains this pipeline and shows a qualitative face reconstruction. The new replay makes its central calculations inspectable on known geometry, including shadows, noise and failure cases.

## Run

Python 3.10+ and a JDK providing `java` and `javac`; no Python packages are needed for the numerical replay.

```sh
python3 -m updated.cli simulate --output updated/results
python3 updated/run_checks.py
```

Open `updated/results/index.html`. The [Android replay app](updated/android-replay/README.md) displays the same generated captures and point clouds; its build/run instructions are separate. The historical APK remains blocked by missing dependencies; see [build details](docs/BUILDABILITY.md).

## Contents and references

| Content | Location |
| --- | --- |
| Submitted Android scanner | [source/](source/) |
| Earlier Eclipse and later Studio versions | [versions/](versions/) |
| Runnable replay, tests and results | [updated/](updated/) |
| Original report and related lab demo | [Report notes](docs/REPORTS.md) |
| Archive provenance, dependencies and validation | [Archive guide](docs/ARCHIVE.md) |

Related lab demonstration: Aaron Wetzler, Rom Herskovitz, Nofar Carmeli and Ron Kimmel, *What Can You Do with a Beam and a Reflecting Prism?* (2014). [Poster](https://twerdster.github.io/WetzlerHerskovitzCarmeliKimmel-ECCVDemo-2014.pdf). Its author list is distinct from this student project’s credits.

## Attribution and reuse

<p align="center">
  <img src="assets/project-preview.jpg" alt="Mannequin head lit by projected light and dark stripe patterns, with a phone held in a clamp mount pointing at it" width="380">
</p>

No blanket software license has been added. Retain the original notices and third-party terms. The `Quaternion` implementation includes an attribution to the Bones framework for JPCT; it remains in the source. The related iOS renderer retains its 2014 Technion copyright and “All rights reserved” notice. Launcher graphics and projection resources are preserved from the historical snapshots; their inclusion does not assign new rights.

On 2026-11-12, Alex Kligman agreed to Aaron Wetzler keeping the archival project page and repository. This records Alex Kligman's response only; no software license is added. The recovered subset and historical hardware/dependency limitations are unchanged.

That dated record describes the earlier snapshot; it does not extend the correspondence to the additional versions recovered on 14 November 2026.

Original authors can open an issue to contribute updates or request corrections or removal of their material. [Project entry on Aaron Wetzler's website](https://twerdster.github.io/#3d-scanner-on-android).

Figure provenance: `assets/project-preview.jpg` is the original student-project photograph from the archived project page on Aaron Wetzler's website, copied without modification. It shows the capture setup, not a reconstruction produced during recovery.
