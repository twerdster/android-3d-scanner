# 3D Scanner on Android

![Language](https://img.shields.io/badge/code-Java%20%2F%20Python-315b73) ![Demo](https://img.shields.io/badge/demo-saved%20output-236b66)

![Synthetic Gray-code captures of the Stanford Dragon and the decoded point cloud](showcase/beam-dragon.gif)

*Synthetic captures and the decoded cloud. This is not a hardware scan.*

This project built a structured-light scanner from a Samsung Galaxy Beam and a reflecting prism. The projector shows Gray-code stripes and the camera captures them. Decoding gives each pixel a projector correspondence, and calibrated triangulation recovers the points.

Students: Arkadi Godlin, Alex Kligman. Lab engineer: Alon Zvirin. Supervision: Aaron Wetzler. Dragon geometry: Stanford Computer Graphics Laboratory, under [research-use terms](showcase/STANFORD-ASSET-TERMS.md).

## Updated

[Open the interactive demo](https://twerdster.github.io/android-3d-scanner/). It rotates the saved decoded Dragon cloud and opens the existing 13-scene [interactive report](updated/results/index.html). The scanner does not run in the browser.

The unchanged original Java calculations run headless alongside a corrected Python path on 13 simulated scenes. A new Android replay app ran those fixtures on an emulator. The dense Dragon replay decodes 12 synthetic 512×384 exposures with supplied calibration. It produced 77,870 accepted points, 1.158 mm virtual correspondence RMSE and 99.578% illuminated coverage. Physical hardware accuracy has not been measured, and the original APK still does not build ([details](docs/BUILDABILITY.md)). Test records are in [validation/](validation/).

Requirements: Python 3.10+ and a JDK for the desktop regressions. The dense replay also needs NumPy and Pillow (`python3 showcase/check_showcase.py`). See [updated/README.md](updated/README.md) and [updated/DETAILS.md](updated/DETAILS.md).

## Original reference

The archival README is preserved in [ORIGINAL_PROJECT_REFERENCE.md](ORIGINAL_PROJECT_REFERENCE.md), including Alex Kligman's dated permission note and its scope. The 180 original file instances in [source/](source/) and [versions/](versions/) are unchanged, as recorded in the [archive guide](docs/ARCHIVE.md). Notices remain, and no blanket license is assigned.
