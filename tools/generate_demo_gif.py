"""Render a data-bound Beam pipeline GIF; numerical replay files stay unchanged.

Requires Pillow. Run from the repository root with --scratch outside Git.
The capture images, decoded maps and point clouds come from committed replay
inputs/results. Only display brightness, projection and color are changed.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from updated.synthetic import decode_corrected  # noqa: E402

WIDTH, HEIGHT, FPS = 1000, 620, 15
FRAMES_PER_SCENE = 60
SCENES = [('sphere', 'Sphere + background'), ('step', 'Depth step'),
          ('projector_shadow', 'Projector shadow')]
BG = '#0b1424'
CARD = '#111f32'
EDGE = '#293d55'
TEXT = '#eff5f7'
MUTED = '#9fb3c8'
ACCENT = '#55d5c6'
PALETTE = [(24, 39, 74), (37, 88, 133), (42, 153, 148),
           (140, 205, 159), (241, 225, 153)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def color(value, low=.35, high=1.0):
    t = max(0, min(1, (value-low)/(high-low))) * (len(PALETTE)-1)
    index = min(int(t), len(PALETTE)-2)
    fraction = t-index
    return tuple(round(a+(b-a)*fraction) for a, b in zip(PALETTE[index], PALETTE[index+1]))


def font_path(explicit):
    if explicit:
        return explicit.resolve()
    for name in ['/System/Library/Fonts/Supplemental/Arial.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                 'C:/Windows/Fonts/arial.ttf']:
        if Path(name).is_file():
            return Path(name)
    raise RuntimeError('Supply --font with a readable TrueType font.')


def ply_points(path):
    lines = path.read_text().splitlines()
    first = lines.index('end_header') + 1
    return [tuple(float(v) for v in line.split()) for line in lines[first:]]


def data():
    fixture = ROOT/'updated/android-replay/app/src/main/assets/replay.json'
    results = ROOT/'updated/results'
    source = json.loads(fixture.read_text())
    metrics = json.loads((results/'metrics.json').read_text())
    output = {}
    for name, title in SCENES:
        scene = next(s for s in source['scenes'] if s['name'] == name)
        decoded = decode_corrected(scene)
        computed = [r['xyz'] for r in decoded if r['xyz'] is not None]
        points = ply_points(results/(name+'.ply'))
        if len(points) != len(computed):
            raise ValueError('Saved PLY count differs: '+name)
        maximum = max(abs(a-b) for point, reference in zip(points, computed)
                      for a, b in zip(point, reference))
        if maximum > 6e-8:
            raise ValueError('Saved PLY differs from replay: '+name)
        output[name] = {'scene': scene, 'title': title, 'decoded': decoded,
                        'points': points, 'metrics': metrics['scenes'][name]['metrics']['corrected'],
                        'ply_max_coordinate_rounding_m': maximum}
    return output


def maps(item):
    scene, decoded = item['scene'], item['decoded']
    size = (scene['cols'], scene['rows'])
    depth = Image.new('RGB', size)
    depth.putdata([color(r['xyz'][2]) if r['xyz'] else (8, 15, 27) for r in decoded])
    address = Image.new('RGB', size)
    address.putdata([color(r['q'], 0, scene['projector_columns']-1)
                     if r['xyz'] else (8, 15, 27) for r in decoded])
    captures = []
    for frame in scene['frames']:
        gray = Image.new('L', size)
        # Fixed display-only gain keeps the actual dark captures legible.
        gray.putdata([min(255, v*2) for v in frame])
        captures.append(gray.convert('RGB').resize((272, 204), Image.Resampling.NEAREST))
    return depth.resize((272, 204), Image.Resampling.NEAREST), address.resize((120, 90), Image.Resampling.NEAREST), captures


def cloud(points, phase):
    image = Image.new('RGB', (288, 286), CARD)
    draw = ImageDraw.Draw(image)
    angle = .12+2*math.pi*phase
    ca, sa = math.cos(angle), math.sin(angle)
    pitch = -.12
    cp, sp = math.cos(pitch), math.sin(pitch)
    transformed = []
    for x, y, z in points:
        horizontal, vertical, depth = y, -x, z-.72
        a, b = ca*horizontal+sa*depth, -sa*horizontal+ca*depth
        yy, zz = cp*vertical-sp*b, sp*vertical+cp*b
        transformed.append((144+a*123, 143+yy*123, zz, z))
    for x, y, _, z in sorted(transformed, key=lambda p: p[2], reverse=True):
        draw.ellipse((x-1.5, y-1.5, x+1.5, y+1.5), fill=color(z))
    return image


def render(item, scene_index, local_frame, fonts):
    image = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    title, large, medium, small, tiny = fonts
    draw.text((26, 18), 'BEAM  /  From projected light to 3D', font=title, fill=TEXT)
    draw.text((28, 65), 'Gray-code structured light · generated camera observations', font=medium, fill=MUTED)
    for x, width in [(24, 304), (340, 304), (656, 320)]:
        draw.rounded_rectangle((x, 110, x+width, 550), radius=15, fill=CARD, outline=EDGE, width=1)
    for x, label in [(42, '01   CAPTURE'), (358, '02   DECODE + DEPTH'), (674, '03   RECONSTRUCT')]:
        draw.text((x, 127), label, font=medium, fill=ACCENT)
    depth, address, captures = item['maps']
    capture = local_frame//5
    image.paste(captures[capture], (40, 168))
    image.paste(depth, (356, 168))
    image.paste(address, (356, 454))
    image.paste(cloud(item['points'], local_frame/FRAMES_PER_SCENE), (672, 158))
    if capture == 0:
        label = 'Black reference'
    elif capture == 1:
        label = 'White reference'
    else:
        label = f'Gray bit {capture-1} of 10'
    draw.text((42, 387), label, font=large, fill=TEXT)
    draw.text((42, 420), f'Capture {capture+1:02d} / 12', font=small, fill=MUTED)
    for i in range(12):
        x = 43+i*22
        draw.rounded_rectangle((x, 451, x+16, 463), radius=3,
                               fill=ACCENT if i == capture else '#31445b')
    draw.text((42, 483), 'Same camera pixels', font=small, fill=TEXT)
    draw.text((42, 508), 'Brightness ×2 for display', font=tiny, fill=MUTED)
    draw.text((358, 382), 'Final depth', font=large, fill=TEXT)
    for x in range(268):
        draw.line((358+x, 433, 358+x, 441), fill=color(x, 0, 267))
    draw.text((358, 412), '0.35 m', font=tiny, fill=MUTED)
    draw.text((577, 412), '1.0 m', font=tiny, fill=MUTED)
    draw.text((490, 459), 'Decoded column', font=small, fill=TEXT)
    draw.text((490, 485), '0 – 1,023', font=medium, fill=ACCENT)
    draw.text((490, 514), '10 Gray bits', font=tiny, fill=MUTED)
    draw.text((674, 452), item['title'], font=large, fill=TEXT)
    stats = item['metrics']
    draw.text((674, 486), f"{len(item['points']):,} points · {stats['rmse_m']*1000:.2f} mm RMSE", font=small, fill=ACCENT)
    draw.text((674, 516), 'Final cloud · camera orbit only', font=tiny, fill=MUTED)
    draw.text((27, 572), 'SYNTHETIC  ·  supplied calibration  ·  corrected replay', font=small, fill=MUTED)
    for i, label in enumerate(['Sphere', 'Step', 'Shadow']):
        x = 698+i*92
        draw.text((x, 574), label, font=small, fill=ACCENT if i == scene_index else '#6f829b')
    draw.rectangle((0, HEIGHT-4, round(WIDTH*(scene_index*FRAMES_PER_SCENE+local_frame+1)/(len(SCENES)*FRAMES_PER_SCENE)), HEIGHT), fill=ACCENT)
    return image


def generate(scratch, output, explicit_font):
    scratch.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    chosen_font = font_path(explicit_font)
    fonts = [ImageFont.truetype(str(chosen_font), size) for size in (32, 21, 18, 17, 14)]
    items = data()
    for item in items.values():
        item['maps'] = maps(item)
    paths = []
    for scene_index, (name, _) in enumerate(SCENES):
        for local in range(FRAMES_PER_SCENE):
            frame = render(items[name], scene_index, local, fonts)
            path = scratch/f'frame-{len(paths):03d}.png'
            frame.save(path)
            paths.append(path)
    # One shared palette prevents inter-frame color shifts and avoids dithering.
    palette_sheet = Image.new('RGB', (WIDTH*3, HEIGHT*2))
    for index, number in enumerate([0, 20, 60, 80, 120, 140]):
        with Image.open(paths[number]) as frame:
            palette_sheet.paste(frame, ((index%3)*WIDTH, (index//3)*HEIGHT))
    palette = palette_sheet.quantize(colors=192, method=Image.Quantize.MEDIANCUT)
    frames = []
    expected = []
    for path in paths:
        with Image.open(path) as frame:
            indexed = frame.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE)
            expected.append(hashlib.sha256(indexed.convert('RGB').tobytes()).hexdigest())
            frames.append(indexed)
    durations = [70, 60, 70]*(len(frames)//3)
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)
    poster = output.with_name(output.stem+'-poster.png')
    Image.open(paths[0]).save(poster)
    encoded = []
    with Image.open(output) as gif:
        if gif.n_frames != len(frames) or gif.size != (WIDTH, HEIGHT) or gif.info.get('loop') != 0:
            raise ValueError('Encoded GIF dimensions/frame count/loop differ')
        for i in range(gif.n_frames):
            gif.seek(i)
            rgb = gif.convert('RGB')
            actual = hashlib.sha256(rgb.tobytes()).hexdigest()
            if actual != expected[i]:
                raise ValueError('Encoded frame differs: '+str(i))
            encoded.append({'frame': i, 'duration_ms': gif.info['duration'], 'rgb_sha256': actual,
              'cloud_sha256': hashlib.sha256(rgb.crop((672, 158, 960, 444)).tobytes()).hexdigest()})
    for s in range(len(SCENES)):
        if len({f['cloud_sha256'] for f in encoded[s*60:(s+1)*60]}) < 40:
            raise ValueError('Insufficient visible cloud motion')
    contact = Image.new('RGB', (1000, 620), BG)
    chosen = [0, 10, 20, 35, 60, 70, 80, 95, 120, 130, 140, 155]
    for j, number in enumerate(chosen):
        with Image.open(paths[number]) as frame:
            contact.paste(frame.resize((250, 155), Image.Resampling.LANCZOS), ((j%4)*250, (j//4)*206))
    contact.save(scratch/'contact-sheet.png')
    files = [ROOT/'tools/generate_demo_gif.py', ROOT/'updated/synthetic.py',
             ROOT/'updated/results/metrics.json', ROOT/'updated/android-replay/app/src/main/assets/replay.json',
             *[ROOT/'updated/results'/(name+'.ply') for name, _ in SCENES]]
    metadata = {'schema': 'beam-demo-media-v1', 'scope': 'Generated observations and corrected replay; supplied calibration, no hardware capture',
      'generator': 'tools/generate_demo_gif.py', 'python_version': platform.python_version(),
      'pillow_version': PILLOW_VERSION, 'font': {'name': chosen_font.name, 'sha256': digest(chosen_font)},
      'dimensions': [WIDTH, HEIGHT], 'frame_count': len(encoded), 'duration_ms': sum(f['duration_ms'] for f in encoded),
      'nominal_fps': FPS, 'loop': 0, 'palette_colors': 192, 'dither': False,
      'capture_display_gain': 2, 'point_cloud_source': 'Saved corrected-replay PLY; no ground-truth vertices',
      'scene_summary': {name: {'points': len(items[name]['points']), 'rmse_m': items[name]['metrics']['rmse_m'],
                       'ply_max_coordinate_rounding_m': items[name]['ply_max_coordinate_rounding_m']} for name, _ in SCENES},
      'input_sha256': {str(p.relative_to(ROOT)): digest(p) for p in files},
      'output_sha256': {str(p.relative_to(ROOT)): digest(p) for p in [output, poster]},
      'gif_bytes': output.stat().st_size, 'all_encoded_frames_match': True,
      'motion_unique_cloud_frames': [len({f['cloud_sha256'] for f in encoded[i*60:(i+1)*60]}) for i in range(3)],
      'frames': encoded}
    if metadata['gif_bytes'] > 5_000_000:
        raise ValueError('GIF exceeds 5 MB target')
    target = ROOT/'validation/demo-media.json'
    target.write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({k: metadata[k] for k in ['dimensions','frame_count','duration_ms','gif_bytes','motion_unique_cloud_frames']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'assets/beam-reconstruction.gif')
    parser.add_argument('--font', type=Path)
    args = parser.parse_args()
    generate(args.scratch, args.output.resolve(), args.font)
