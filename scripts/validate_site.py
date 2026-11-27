#!/usr/bin/env python3
"""Check local HTML links, fragments, metadata, and sitemap coverage."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import xml.etree.ElementTree as ET
root = Path(__file__).resolve().parents[1]
base = "https://shubham235808.github.io/shubhamvashishtha/"
class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.duplicates = []
        self.links = []
        self.canonical = []
        self.description = False
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            if a["id"] in self.ids:
                self.duplicates.append(a["id"])
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if a.get(key):
                self.links.append(a[key])
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical.append(a.get("href"))
        if tag == "meta" and a.get("name") == "description":
            self.description = bool(a.get("content"))
paths = [root / "index.html", root / "resume.html", root / "404.html", *sorted((root / "projects").glob("*.html")), *sorted((root / "insights").glob("*.html"))]
pages = {p.resolve(): Page(p.read_text(encoding="utf-8")) for p in paths}
errors = []
checks = 0
for path, page in pages.items():
    rel = path.relative_to(root).as_posix()
    for duplicate in page.duplicates:
        errors.append(f"{rel}: duplicate id {duplicate}")
    if rel != "404.html":
        expected = base + ("" if rel == "index.html" else rel)
        if page.canonical != [expected] or not page.description:
            errors.append(f"{rel}: missing or incorrect canonical/description")
    for link in page.links:
        if link.startswith(base):
            parts = urlsplit(link[len(base):])
            target = root / unquote(parts.path or "index.html")
        else:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc:
                continue
            if parts.path.startswith("/"):
                errors.append(f"{rel}: unexpected site-root link {link}")
                continue
            target = path.parent / unquote(parts.path) if parts.path else path
        target = target.resolve()
        if target.is_dir():
            target = target / "index.html"
        checks += 1
        if not target.is_relative_to(root) or not target.is_file():
            errors.append(f"{rel}: missing local target {link}")
        elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
            errors.append(f"{rel}: missing fragment {link}")
ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
actual = {x.text for x in ET.parse(root / "sitemap.xml").findall("s:url/s:loc", ns)}
expected = {base + ("" if p.name == "index.html" else p.relative_to(root).as_posix()) for p in paths if p.name != "404.html"}
if actual != expected:
    errors.append("Sitemap entries differ from indexable HTML pages")
print(f"Checked {len(pages)} HTML pages and {checks} internal links")
if errors:
    print("\n".join(errors))
    raise SystemExit(1)
print("Validation passed")
