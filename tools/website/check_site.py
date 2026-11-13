#!/usr/bin/env python3
"""Site check for docs/: broken internal links and anchors, duplicate ids, images without alt,
links without a name, invalid JSON-LD, hreflang and sitemap targets, and the per-page script
policy (every inline script must match a hash in the page's own policy).

  python tools/website/check_site.py            # exit code 1 when an error is found

Long titles and descriptions and pages not yet translated are listed as notes only.
"""
import base64, hashlib, os, re, sys, json, collections
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs')
LANGS = ['nl','de','fr','pl']
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.links=[]; s.ids=collections.Counter(); s.meta={}; s.links_rel=[]; s.title=None; s._t=False; s.h1=0; s.imgs_noalt=[]; s.lang=None; s.hreflang={}; s.scripts=[]; s.ld=[]; s._ld=False; s.buttons_noname=0; s._a=None; s.empty_a=[]; s.ext_blank_noopener=[]; s.inputs_nolabel=0; s.labels_for=set(); s.inputs=[]
    def handle_starttag(s,t,a):
        a=dict(a)
        if 'id' in a: s.ids[a['id']]+=1
        if t=='html': s.lang=a.get('lang')
        if t=='title': s._t=True; s.title=''
        if t=='h1': s.h1+=1
        if t=='meta':
            k=a.get('name') or a.get('property')
            if k: s.meta[k]=a.get('content')
        if t=='link':
            s.links_rel.append(a)
            if a.get('rel')=='alternate' and a.get('hreflang'): s.hreflang[a['hreflang']]=a.get('href')
            if a.get('href'): s.links.append(('link',a['href']))
            for c in (a.get('imagesrcset') or '').split(','):
                c=c.strip().split(' ')[0]
                if c: s.links.append(('srcset',c))
        for k in ('href','src','poster','data-src','data-full'):
            if t!='link' and a.get(k): s.links.append((t+'.'+k,a[k]))
        for k in ('srcset','data-srcset'):
            for c in (a.get(k) or '').split(','):
                c=c.strip().split(' ')[0]
                if c: s.links.append((t+'.'+k,c))
        st=a.get('style') or ''
        for m in re.findall(r'url\(([^)]+)\)',st): s.links.append(('style',m.strip('\'" ')))
        if t=='img' and a.get('alt') is None: s.imgs_noalt.append(a.get('src'))
        if t=='script' and a.get('type')=='application/ld+json': s._ld=True; s.ld.append('')
        if t=='a':
            s._a={'hidden':a.get('aria-hidden')=='true','href':a.get('href'),'txt':'','aria':a.get('aria-label') or a.get('title'),'img':False}
            if a.get('target')=='_blank' and 'noopener' not in (a.get('rel') or '') and (a.get('href') or '').startswith('http'): s.ext_blank_noopener.append(a.get('href'))
        if t=='img' and s._a is not None and a.get('alt'): s._a['img']=True
        if t=='svg' and s._a is not None and a.get('aria-label'): s._a['img']=True
        if t=='label': s._lab=getattr(s,'_lab',0)+1
        if t=='label' and a.get('for'): s.labels_for.add(a['for'])
        if t in ('input','select','textarea') and a.get('type') not in ('hidden','submit','button'):
            s.inputs.append((a.get('id'), a.get('aria-label') or a.get('aria-labelledby') or a.get('title') or ('wrapped' if getattr(s,'_lab',0) else None)))
    def handle_endtag(s,t):
        if t=='title': s._t=False
        if t=='label' and getattr(s,'_lab',0): s._lab-=1
        if t=='script': s._ld=False
        if t=='a' and s._a is not None:
            x=s._a
            if not x['txt'].strip() and not x['aria'] and not x['img'] and not x.get('hidden'): s.empty_a.append(x['href'])
            s._a=None
    def handle_data(s,d):
        if s._t: s.title+=d
        if s._ld: s.ld[-1]+=d
        if s._a is not None: s._a['txt']+=d
pages={}
for dp,dn,fn in os.walk(ROOT):
    for f in fn:
        if f.endswith('.html'):
            p=os.path.join(dp,f); rel=os.path.relpath(p,ROOT)
            x=P(); 
            try: x.feed(open(p,encoding='utf-8').read())
            except Exception as e: print('PARSE',rel,e); continue
            pages[rel]=x
def resolve(rel, url):
    u=urlparse(url)
    if u.scheme in ('mailto','tel','javascript','data'): return None
    if u.netloc and u.netloc not in ('truecombat.eu','www.truecombat.eu'): return 'EXT'
    path=unquote(u.path)
    if path.startswith('/api/'): return None   # served by the VPS (Caddy), not a file in docs/
    if not path and not u.netloc: return 'SELF'
    if path.startswith('/'): t=path.lstrip('/')
    else: t=os.path.normpath(os.path.join(os.path.dirname(rel),path))
    t=t.replace('\\','/')
    t=t.strip('/')
    if t in ('.',''): t=''
    cands=[t, t+'.html', (t+'/' if t else '')+'index.html']
    if path.endswith('/') or t=='': cands=[(t+'/' if t else '')+'index.html']
    for c in cands:
        if os.path.isfile(os.path.join(ROOT,c)): return 'OK'
    return 'MISSING:'+t
issues=collections.defaultdict(list)
for rel,x in sorted(pages.items()):
    if rel.startswith('go/') : continue
    for kind,l in x.links:
        r=resolve(rel,l)
        if r and r.startswith('MISSING'): issues['broken-link'].append(f'{rel}: {kind} {l}')
    # anchors
    for kind,l in x.links:
        u=urlparse(l)
        if u.fragment and kind=='a.href' and not u.netloc:
            tgt=rel if not u.path else None
            if tgt and u.fragment not in x.ids and u.fragment not in ('top','',): issues['missing-anchor'].append(f'{rel}: #{u.fragment}')
    for i,c in x.ids.items():
        if c>1: issues['dup-id'].append(f'{rel}: {i} x{c}')
    noindex='noindex' in (x.meta.get('robots') or '')
    if not x.title: issues['no-title'].append(rel)
    elif len(x.title)>70 and not noindex: issues['long-title'].append(f'{rel}: {len(x.title)} {x.title}')
    d=x.meta.get('description')
    if not noindex:
        if not d: issues['no-desc'].append(rel)
        elif len(d)>170 or len(d)<50: issues['desc-length'].append(f'{rel}: {len(d)}')
        if x.h1!=1: issues['h1-count'].append(f'{rel}: {x.h1}')
        if not any(l.get('rel')=='canonical' for l in x.links_rel): issues['no-canonical'].append(rel)
        if not x.meta.get('og:image'): issues['no-og-image'].append(rel)
        else:
            r=resolve(rel,x.meta['og:image'])
            if r!='OK' and r!='EXT': issues['og-image-missing'].append(f"{rel}: {x.meta['og:image']} {r}")
    if not x.lang: issues['no-lang'].append(rel)
    else:
        top=rel.split('/')[0]
        exp=top if top in LANGS else 'en'
        if not x.lang.startswith(exp): issues['wrong-lang'].append(f'{rel}: {x.lang}')
    if x.imgs_noalt: issues['img-no-alt'].append(f'{rel}: {x.imgs_noalt[:5]}')
    if x.empty_a: issues['link-no-name'].append(f'{rel}: {x.empty_a[:5]}')
    if x.ext_blank_noopener: issues['blank-no-noopener'].append(f'{rel}: {x.ext_blank_noopener[:3]}')
    for b in x.ld:
        try: json.loads(b)
        except Exception as e: issues['bad-jsonld'].append(f'{rel}: {e}')
    for i,lab in x.inputs:
        if not lab and i not in x.labels_for: issues['input-no-label'].append(f'{rel}: {i}')
    # hreflang reciprocity
    for hl,href in x.hreflang.items():
        r=resolve(rel,href)
        if r not in ('OK',): issues['hreflang-target-missing'].append(f'{rel}: {hl} {href} {r}')
    # the page's own script policy must allow each inline script it carries
    raw=open(os.path.join(ROOT,rel),encoding='utf-8').read()
    pol=re.search(r'<meta http-equiv="Content-Security-Policy" content="script-src ([^"]*)">',raw)
    if pol:
        for m in re.finditer(r'<script(?: type="speculationrules")?>(.*?)</script>',raw,re.S):
            h="'sha256-%s'"%base64.b64encode(hashlib.sha256(m.group(1).encode('utf-8')).digest()).decode()
            if h not in pol.group(1).split(): issues['csp-hash-mismatch'].append(rel)
# sitemap targets
sm=open(os.path.join(ROOT,'sitemap.xml'),encoding='utf-8').read()
for u in re.findall(r'<loc>([^<]+)</loc>',sm)+re.findall(r'<image:loc>([^<]+)</image:loc>',sm)+re.findall(r'hreflang="[^"]+" href="([^"]+)"',sm):
    if resolve('index.html',u)!='OK': issues['sitemap-target-missing'].append(u)
NOTES=('long-title','desc-length')
en=[p for p in pages if '/' not in p]
for L in LANGS:
    have={p.split('/',1)[1] for p in pages if p.startswith(L+'/')}
    miss=[p for p in en if p not in have]
    issues['note-untranslated-'+L].append('%d English pages have no %s version'%(len(miss),L))
errors=0
for k,v in sorted(issues.items()):
    note=k in NOTES or k.startswith('note-')
    if not note: errors+=len(v)
    print('%s %s (%d)'%('note ' if note else 'ERROR',k,len(v)))
    for i in v[:(5 if note else 40)]: print('   ',i)
print('%d pages checked, %d errors'%(len(pages),errors))
sys.exit(1 if errors else 0)
