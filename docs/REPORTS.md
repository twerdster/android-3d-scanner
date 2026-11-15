# Reports and the scanning idea

## Original student report

[Mobile 3D scanner final report](mobile-3d-scanner-report.pdf) is the seven-page report preserved with the Godlin/Kligman project site. The document creation/modification metadata is dated **24 May 2014**. Its PDF Author field says “Alex”; this is document metadata, not a substitute for the project credits: Arkadi Godlin and Alex Kligman, lab engineer Alon Zvirin, supervisor Aaron Wetzler.

The report describes a Samsung Galaxy Beam with a right-angle prism attached to its projector (p. 1), controlled stripe illumination (pp. 1–2), calibrated camera/projector projection matrices and ray/plane triangulation (pp. 2–5), and the application sequence of Gray-code projection, software-synchronized capture, XYZ reconstruction and 3D display (p. 5). Page 6 shows a qualitative reconstructed face point cloud and discusses Android/OpenCV integration and the lack of hardware synchronization.

That figure demonstrates what the report presented; the document contains no numerical accuracy, runtime, scan-distance or benchmark table. Its qualitative result must not be replaced by the new replay’s error measurements. The report’s broad CPU-endianness assertion on p. 7 is not independently established and is not repeated as a current technical finding.

The PDF is included **unchanged**, 511,484 bytes, SHA-256:

```text
62319c49f34c5659b9a750fd3a728a42dd8113cd8fa6a1f971dc1643e41f89a9
```

It came from the preserved project website folder; no currently working original public URL was verified. All seven pages were read and rendered. The publication review found no attachments, annotations, forms, JavaScript or active actions, and no concrete private identifiers, credentials or machine paths. The [document provenance record](../validation/report-document.json) preserves these checks and metadata. Inclusion preserves this historical report; no new license is assigned to it.

## Related lab demonstration

Aaron Wetzler, Rom Herskovitz, Nofar Carmeli and Ron Kimmel, [*What Can You Do with a Beam and a Reflecting Prism?*](https://twerdster.github.io/WetzlerHerskovitzCarmeliKimmel-ECCVDemo-2014.pdf), 2014 lab/demo poster. This one-page poster also explicitly uses a **Samsung Galaxy Beam** and prism. It presents projected Pong/hand detection alongside coded-light 3D reconstruction. It reports no quantitative reconstruction benchmark.

This is related lab context, with its own author list. It is not the Godlin/Kligman final report and does not establish authorship of every later Android edit. The separately archived Objective-C++ iOS renderer is also not an Android version or evidence that either document describes an iPhone scanner.

## Current executable illustration

The [synthetic replay](../updated/README.md) uses independent camera rays, known surfaces and projector visibility to generate captures. Actual saved corrected-replay points, not ground-truth vertices, form the rotating clouds in the [pipeline GIF](../assets/beam-reconstruction.gif). The depth step and shadow scenes make discontinuities and missing illumination visible; calibration is supplied. The [media guide](MEDIA.md) records how the animation is generated and verified. The [numerical model](SIMULATION.md) records errors, conditions, explicit corrections and failures.
