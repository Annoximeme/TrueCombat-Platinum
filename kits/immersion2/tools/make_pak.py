"""Zip release_src/platinum_immersion into zz_platinum_immersion.pk3 (deterministic: sorted, fixed timestamps)."""
import sys, zipfile
from pathlib import Path
S = Path(r'C:\TrueCombatWork\firefight\imm2\src\release_src\platinum_immersion'); out = Path(sys.argv[1])
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(p for p in S.rglob('*') if p.is_file()):
        i = zipfile.ZipInfo(f.relative_to(S).as_posix(), (2026, 11, 16, 0, 0, 0)); i.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(i, f.read_bytes())
print(out, out.stat().st_size)
