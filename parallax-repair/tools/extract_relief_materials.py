# Runs on the PC (any python3): copies the brick/stone material maps (_n.jpg, _rmao.jpg) of the 0.39.0 candidate's
# zzz_hd_materials.pk3 and cqb_map_harbour.pk3 into relief_materials.zip (43 MB), the input of build_heights_039.py.
# Harbour entries go under harbour/; merge them to textures/... before the build (see parallax-repair.md).
import zipfile, re, sys
T = sys.argv[1] if len(sys.argv) > 1 else '../integ039/pkg/releases/0.39.0-sandbox37/TrueCombat Platinum/tcetest/'
rel = re.compile(r'brick|cobble|kopf|pave|pflaster|rubble|rock|stone|cliff|gravel', re.I)
exc = re.compile(r'plaster|putz|ceil|decke', re.I)
z = zipfile.ZipFile(T + 'zzz_hd_materials.pk3'); n = 0
with zipfile.ZipFile('relief_materials.zip', 'w', zipfile.ZIP_STORED) as o:
    for f in z.namelist():
        l = f.lower()
        if l.startswith('textures/') and (l.endswith('_n.jpg') or l.endswith('_rmao.jpg')) and rel.search(l) and not exc.search(l):
            o.writestr(f, z.read(f)); n += 1
    h = zipfile.ZipFile(T + 'cqb_map_harbour.pk3')
    for f in h.namelist():
        l = f.lower()
        if l.endswith('.bsp') or l.endswith('.shader') or (rel.search(l) and not exc.search(l) and l.startswith('textures/')):
            o.writestr('harbour/' + f, h.read(f)); n += 1
print(n)
