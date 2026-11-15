# Pipeline animation

[beam-reconstruction.gif](../assets/beam-reconstruction.gif) is a **12-second, 1000 × 620** loop showing three generated scenes: sphere/background, depth step and projector shadow. The left panel cycles through the actual twelve black/white/Gray capture buffers; the middle shows final decoded columns and depth; the right rotates the final reconstructed cloud. It does not imply that partial capture prefixes produce a complete reconstruction, or that the physical phone has been run.

The camera captures and calibration are the committed replay fixture. Point positions come from the saved corrected-replay PLYs and are checked against decoding those captures. No ground-truth vertices replace the reconstruction. Capture brightness has a fixed display-only gain of two; depth and cloud colors share the 0.35–1.0 virtual-metre scale. The view rotates around each fixed point set; the scene geometry is not animated or re-estimated. This media introduces no new reconstruction algorithm.

## Regenerate

The media renderer needs Python 3.10+ and **Pillow**; the numerical replay’s standard-library requirements are unchanged. Run from the repository root:

```sh
python3 tools/generate_demo_gif.py --scratch /path/to/task-scratch/beam-frames
```

The generator searches for system Arial or DejaVu Sans; pass `--font /path/to/font.ttf` when needed. It records the selected font’s name/hash without copying the font or a machine-specific path into the repository. PNG frame scratch stays outside Git. The existing numerical source, fixture, PLYs and metrics are inputs and are not regenerated or modified.

Outputs are the GIF, a [static poster](../assets/beam-reconstruction-poster.png) and [media provenance/validation](../validation/demo-media.json). A private contact sheet and all source PNG frames support visual review. The report records renderer/input/output hashes, Pillow/Python versions, dimensions, durations, palette and each decoded frame’s RGB hash.

## Verification

All 180 encoded frames are decoded and compared byte-for-byte with the intended palette-rendered RGB frames. The loop lasts exactly 12,000 ms and each of the three cloud crops has 60 distinct motion frames. The 1,733,980-byte GIF uses one fixed 192-color palette without dithering to keep labels and colors stable. Readable labels and the capture/depth/cloud content were also inspected at full resolution and on a contact sheet. Numerical bindings remain separate and unchanged.

The original preview photograph is preserved unchanged and remains a historical setup image. Report figures and the related poster were reviewed for context but are not composited into this generated animation. No new license is assigned to historical photographs, report figures or source by creating the GIF.
