"""Animate actual dense captures and reconstructed points; no mesh/truth input."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
W, H, COUNT = 1100, 700, 96
BG, CARD, TEXT, MUTED, ACCENT = '#0a1321', '#101f30', '#f0f6f6', '#a4b9c9', '#67dec8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fonts(path=None):
    choices = [path] if path else [Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
              Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    font = next((p for p in choices if p and p.is_file()), None)
    if font is None:
        raise ValueError('Supply --font with a TrueType font')
    return [ImageFont.truetype(str(font), s) for s in (32, 22, 18, 15)], font


def load():
    results = ROOT/'showcase/results'
    with np.load(results/'reconstruction.npz', allow_pickle=False) as saved:
        points, valid = saved['xyz'], saved['valid']
    rig = json.loads((results/'rig.json').read_text())
    metrics = json.loads((results/'metrics.json').read_text())['metrics']
    c = np.asarray(rig['camera_matrix']).reshape(3, 4)
    camera_depth = points @ c[2, :3] + c[2, 3]
    p = points[valid]
    depth = camera_depth[valid]
    # Colors depend only on reconstructed camera depth. No source-model
    # normals, surface shading, truth vertices or inferred triangles are used.
    palette = np.array([[45, 103, 149], [56, 164, 164], [145, 215, 182], [249, 222, 157]])
    t = np.clip((depth-.78)/.24, 0, 1)*3
    index = np.minimum(t.astype(int), 2); fraction = (t-index)[:, None]
    color = np.rint(palette[index]*(1-fraction)+palette[index+1]*fraction).astype(np.uint8)
    captures = []
    for i in range(12):
        with Image.open(results/'captures'/f'{i:02d}.png') as image:
            captures.append(image.convert('RGB').resize((352, 264), Image.Resampling.LANCZOS))
    depth_image = Image.open(results/'depth.png').convert('RGB').resize((264, 198), Image.Resampling.LANCZOS)
    return p, color, rig, metrics, captures, depth_image


def cloud(points, colors, rig, phase):
    origin = np.array([0., .175, 0.])
    base = np.asarray(rig['camera_basis_rows_down_right_forward'])
    angle = math.radians(28)*math.sin(2*math.pi*phase)
    ca, sa = math.cos(angle), math.sin(angle)
    rotate = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
    local = (points-origin) @ rotate.T @ base.T
    # Orthographic presentation preserves point positions; no mesh, triangles,
    # hole filling, inferred backside or truth vertices are rendered.
    x = np.rint(328+local[:, 1]*1160).astype(int)
    y = np.rint(225+local[:, 0]*1160).astype(int)
    z = local[:, 2]
    inside = (x >= 1) & (x < 655) & (y >= 1) & (y < 515)
    order = np.argsort(z[inside])[::-1]
    xx, yy, rgb = x[inside][order], y[inside][order], colors[inside][order]
    image = np.zeros((516, 656, 3), dtype=np.uint8)
    image[:] = [16, 31, 48]
    # A 2×2 screen-space splat makes dense samples legible; geometry unchanged.
    for ox, oy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        image[yy+oy, xx+ox] = rgb
    return Image.fromarray(image)


def frame(data, i, f):
    points, color, rig, metrics, captures, depth = data
    title, large, medium, small = f
    image = Image.new('RGB', (W, H), BG); draw = ImageDraw.Draw(image)
    draw.text((24, 18), 'BEAM  /  Structured light on the Stanford Dragon', font=title, fill=TEXT)
    draw.text((26, 62), '512 × 384 camera · 12 generated captures · supplied calibration', font=medium, fill=MUTED)
    draw.rounded_rectangle((20, 106, 396, 646), radius=16, fill=CARD, outline='#2c4154')
    draw.rounded_rectangle((410, 106, 1080, 646), radius=16, fill=CARD, outline='#2c4154')
    draw.text((34, 120), '01  CAMERA OBSERVATIONS', font=medium, fill=ACCENT)
    index = (1+int(i*12/COUNT)) % 12
    image.paste(captures[index], (32, 157))
    label = 'Black reference' if index == 0 else 'White reference' if index == 1 else f'Gray bit {index-1} / 10'
    draw.text((35, 430), label, font=large, fill=TEXT)
    draw.text((35, 459), f'Capture {index+1:02d} / 12 · actual 8-bit buffer', font=small, fill=MUTED)
    image.paste(depth.resize((176, 132)), (34, 493))
    draw.text((225, 507), 'Decoded', font=medium, fill=TEXT)
    draw.text((225, 533), 'final depth', font=medium, fill=TEXT)
    draw.text((225, 573), '10 Gray bits', font=small, fill=MUTED)
    draw.text((225, 598), '1,024 columns', font=small, fill=MUTED)
    image.paste(cloud(points, color, rig, i/COUNT), (418, 130))
    draw.text((430, 120), '02  RECONSTRUCTED POINTS', font=medium, fill=ACCENT)
    draw.text((438, 592), f"{metrics['accepted_points']:,} points  ·  {metrics['rmse_m']*1000:.2f} mm RMSE", font=large, fill=TEXT)
    draw.text((438, 622), 'One camera view · final cloud orbit · no backside filling', font=small, fill=MUTED)
    draw.text((25, 667), 'SYNTHETIC  ·  Lambertian shading + shadows + read noise', font=small, fill=MUTED)
    draw.text((760, 667), 'Stanford CG Lab  ·  research-use asset', font=small, fill=MUTED)
    return image


def generate(scratch, font_path=None, preview=False):
    scratch.mkdir(parents=True, exist_ok=True)
    f, selected_font = fonts(font_path)
    data = load()
    numbers = [0, 24, 48, 72] if preview else range(COUNT)
    for i in numbers:
        frame(data, i, f).save(scratch/f'frame-{i:03d}.png')
    if preview:
        print(scratch/'frame-000.png'); return
    palette_sheet = Image.new('RGB', (W*2, H*2))
    for j, i in enumerate([0, 24, 48, 72]):
        palette_sheet.paste(Image.open(scratch/f'frame-{i:03d}.png'), ((j % 2)*W, (j//2)*H))
    palette = palette_sheet.quantize(colors=160)
    frames = [Image.open(scratch/f'frame-{i:03d}.png').convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE) for i in range(COUNT)]
    target = ROOT/'showcase/beam-dragon.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=True, disposal=1)
    poster = ROOT/'showcase/beam-dragon-poster.png'
    Image.open(scratch/'frame-000.png').save(poster)
    checks = []
    with Image.open(target) as gif:
        assert gif.n_frames == COUNT and gif.size == (W, H) and gif.info['loop'] == 0
        for i in range(COUNT):
            gif.seek(i); actual = gif.convert('RGB').tobytes()
            assert actual == frames[i].convert('RGB').tobytes()
            checks.append({'frame': i, 'duration_ms': gif.info['duration'], 'rgb_sha256': hashlib.sha256(actual).hexdigest()})
    inputs = [ROOT/'showcase/render_gif.py', ROOT/'showcase/results/reconstruction.npz', ROOT/'showcase/results/metrics.json', ROOT/'showcase/results/rig.json',
              ROOT/'showcase/results/depth.png', *sorted((ROOT/'showcase/results/captures').glob('*.png'))]
    record = {'schema': 'beam-dragon-media-v1', 'dimensions': [W, H], 'frames': COUNT,
        'duration_ms': sum(c['duration_ms'] for c in checks), 'gif_bytes': target.stat().st_size,
        'all_decoded_frames_match': True, 'loop': 0, 'palette_colors': 160, 'dither': False,
        'pillow_version': PILLOW_VERSION, 'font': {'name': selected_font.name, 'sha256': sha(selected_font)},
        'point_source': 'existing corrected decoder output; no mesh or truth input',
        'view': '±28 degree presentation orbit of one reconstructed camera view; 2x2 screen splats',
        'colors': 'reconstructed camera depth only; no mesh normals or truth',
        'input_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
        'output_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in [target, poster]}, 'frame_checks': checks}
    (ROOT/'showcase/media-validation.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k: record[k] for k in ['dimensions', 'frames', 'duration_ms', 'gif_bytes']}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scratch', required=True, type=Path)
    p.add_argument('--font', type=Path)
    p.add_argument('--preview', action='store_true')
    args = p.parse_args()
    generate(args.scratch, args.font, args.preview)
