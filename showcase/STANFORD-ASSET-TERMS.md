# Stanford Dragon source and terms

Credit: **Stanford University Computer Graphics Laboratory**, Stanford 3D
Scanning Repository. The Dragon range scans and volumetric reconstruction
are associated with Brian Curless and Marc Levoy, *A Volumetric Method for
Building Complex Models from Range Images*, SIGGRAPH 1996.

Primary source and terms: <https://graphics.stanford.edu/data/3Dscanrep/>.
Download: <https://graphics.stanford.edu/pub/3Dscanrep/dragon/dragon_recon.tar.gz>.
Terms checked on 15 November 2026. Stanford permits research use and free
mirroring/redistribution with source acknowledgement. Commercial use or use
in products for sale requires its permission. Its page also requires tasteful
use of the culturally significant dragon. **This is not an MIT/CC0 asset.**
The source page is authoritative; this paragraph is a summary, not a new grant.

The downloaded `dragon_recon/dragon_vrip.ply` has 437,645 vertices and
871,414 triangles. These measured counts differ from the repository web
page's listing. The original archive README states the reconstruction was
decimated from a higher-resolution result and that decimation introduced
small holes. No additional decimation, repair, filling or morphing was done.

The normalization is only a uniform scale and translation to a 0.35-metre
height, floor Y=0 and centered X/Z. `mesh-provenance.json` records source and
normalized hashes and the exact transformation. The synthetic experiments
use the mesh as known scene geometry to generate observations; they are not
scans of the physical Stanford statuette and are not Stanford benchmark data.

Preserve this acknowledgement and terms alongside any redistributed source
or normalized mesh. Images/reconstructions derived from it must not be
silently included in an unrestricted blanket license for new source code.
