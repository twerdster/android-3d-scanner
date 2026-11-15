"""Fetch/check the official Stanford Dragon and apply translation/uniform scale.

Recipe code: MIT (HELPER-LICENSE). Data: separate STANFORD-ASSET-TERMS.md.
No repair, resampling, decimation, topology edit or axis rotation is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import urllib.request

import numpy as np

URL = "https://graphics.stanford.edu/pub/3Dscanrep/dragon/dragon_recon.tar.gz"
ARCHIVE_SHA256 = "74ac1d90989c9b1732edee82d57e9ce71452144cf4355f108d8c9c616d28d02f"
MEMBER = "dragon_recon/dragon_vrip.ply"
MEMBER_SHA256 = "fea87ff48f2aba22fb53e7b67c3ff3f7b8c2a3b3a0653af62c48bba67c6d5744"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(archive, output):
    if sha256(archive) != ARCHIVE_SHA256:
        raise ValueError("official archive checksum differs from reviewed source")
    with tarfile.open(archive, "r:gz") as tar:
        member = tar.getmember(MEMBER)
        if not member.isfile() or member.size != 33831477:
            raise ValueError("unexpected selected member")
        raw = tar.extractfile(member).read()
        original_readme = tar.extractfile("dragon_recon/README").read()
    if hashlib.sha256(raw).hexdigest() != MEMBER_SHA256:
        raise ValueError("selected mesh checksum differs")
    lines = raw.decode("ascii").splitlines()
    end = lines.index("end_header")
    header = lines[:end]
    if "format ascii 1.0" not in header:
        raise ValueError("expected reviewed ASCII PLY")
    nv = int(next(s.split()[-1] for s in header if s.startswith("element vertex ")))
    nf = int(next(s.split()[-1] for s in header if s.startswith("element face ")))
    vertices = np.array([s.split()[:3] for s in lines[end + 1:end + 1 + nv]], dtype=np.float64)
    face_lines = [s.split() for s in lines[end + 1 + nv:end + 1 + nv + nf]]
    if any(s[0] != "3" or len(s) != 4 for s in face_lines):
        raise ValueError("only the reviewed triangular mesh is supported")
    faces = np.array([s[1:] for s in face_lines], dtype=np.int32)
    if vertices.shape != (437645, 3) or faces.shape != (871414, 3):
        raise ValueError("unexpected mesh dimensions")
    lo, hi = vertices.min(0), vertices.max(0)
    offset = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    scale = .35 / (hi[1] - lo[1])
    vertices = (vertices - offset) * scale
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output / "dragon-normalized.npz", vertices=vertices, faces=faces)
    with (output / "dragon-normalized.obj").open("w") as stream:
        stream.write("# Stanford Dragon normalized uniformly to 0.35 metre height. Stanford terms apply.\n")
        np.savetxt(stream, vertices, fmt="v %.10g %.10g %.10g")
        np.savetxt(stream, faces + 1, fmt="f %d %d %d")
    ply_header = ("ply\nformat binary_little_endian 1.0\n"
                  "comment Stanford Computer Graphics Laboratory; see STANFORD-ASSET-TERMS.md\n"
                  f"element vertex {nv}\nproperty double x\nproperty double y\nproperty double z\n"
                  f"element face {nf}\nproperty list uchar int vertex_indices\nend_header\n").encode()
    packed_faces = np.empty(nf, dtype=[("n", "u1"), ("f", "<i4", (3,))])
    packed_faces["n"] = 3
    packed_faces["f"] = faces
    (output / "dragon-normalized.ply").write_bytes(
        ply_header + vertices.astype("<f8").tobytes() + packed_faces.tobytes())
    (output / "STANFORD-DRAGON-README.txt").write_bytes(original_readme)
    metadata = {
        "schema": "scanner-shared-mesh-v1", "asset": "Stanford Dragon",
        "source_page": "https://graphics.stanford.edu/data/3Dscanrep/",
        "archive_url": URL, "archive_sha256": ARCHIVE_SHA256,
        "source_member": MEMBER, "source_member_sha256": MEMBER_SHA256,
        "vertices": nv, "triangles": nf, "source_bounds": [lo.tolist(), hi.tolist()],
        "translation_before_uniform_scale": (-offset).tolist(), "uniform_scale": float(scale),
        "normalized_bounds": [vertices.min(0).tolist(), vertices.max(0).tolist()],
        "world_coordinates": "+X right; +Y up; +Z completing right handed world; floorY=0; centerX/Z=0",
        "camera_coordinates": "+X right; +Y down; +Z forward",
        "blender_coordinates": "(x,y,z)_world -> (x,-z,y)_Blender",
        "known_source_limitation": "Official source documents numerous small holes; no filling/decimation/morphing performed.",
        "files": {name: sha256(output / name) for name in
                  ["dragon-normalized.npz", "dragon-normalized.obj", "dragon-normalized.ply"]},
    }
    (output / "mesh-provenance.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="existing official .tar.gz, checked by SHA-256")
    parser.add_argument("--download", action="store_true", help="download the 11.2 MB official archive")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.archive is None and not args.download:
        parser.error("supply --archive or explicitly select --download")
    if args.archive is not None and args.download:
        parser.error("select one source")
    with tempfile.TemporaryDirectory(prefix="stanford-dragon-") as scratch:
        archive = args.archive
        if archive is None:
            archive = Path(scratch) / "dragon_recon.tar.gz"
            total = 0
            with urllib.request.urlopen(URL, timeout=60) as response, archive.open("wb") as stream:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 20 * 1024 * 1024:
                        raise ValueError("download exceeds reviewed archive bound")
                    stream.write(chunk)
        metadata = prepare(archive, args.output)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
