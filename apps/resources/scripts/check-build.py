"""Check generated site links and assets before static deployment."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json

ROOT = Path(__file__).resolve().parents[1] / 'dist'
if not ROOT.is_dir():
    raise SystemExit('Build output missing: run npm run build first')
class Page(HTMLParser):
    def __init__(self, file):
        super().__init__(); self.file = file; self.links = []; self.ids = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        for field in (('href',) if tag in ('a','link') else ('src',) if tag in ('img','script') else ()):
            if a.get(field): self.links.append(a[field])

pages = {}
for file in ROOT.rglob('*.html'):
    p = Page(file); p.feed(file.read_text()); pages[file.resolve()] = p
if not pages:
    raise SystemExit('Build output contains no HTML pages')
errors = []
for file, page in pages.items():
    for link in page.links:
        u = urlsplit(link)
        if u.scheme or u.netloc: continue
        path = unquote(u.path)
        target = (ROOT / path.lstrip('/') if path.startswith('/') else file.parent / path).resolve() if path else file
        if not target.is_relative_to(ROOT.resolve()):
            errors.append((str(file.relative_to(ROOT)),link,'outside site')); continue
        if target.is_dir(): target = target / 'index.html'
        if not target.exists(): errors.append((str(file.relative_to(ROOT)),link,'missing target')); continue
        if u.fragment and target in pages and unquote(u.fragment) not in pages[target].ids:
            errors.append((str(file.relative_to(ROOT)),link,'missing anchor'))
print(json.dumps({'pages':len(pages),'broken_links':errors}, ensure_ascii=False))
raise SystemExit(bool(errors))
