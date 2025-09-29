#!/usr/bin/env python3
"""
Reads the source HTML support tables, builds the combined JSON bundle
(same structure the lookup expects), injects it into the template HTML’s
<script id="data" type="application/json">…</script> (or id="html-support-data"),
and writes a *new* HTML file (does NOT overwrite lookup/lookup.html).

Env:
- INPUT_FILES: newline-separated list of source HTML files
- LOOKUP_TEMPLATE: template HTML (e.g., lookup/lookup.html)
- OUTPUT_FILE: destination HTML (the workflow sets this)
"""
from html.parser import HTMLParser
from html import unescape
from pathlib import Path
import json, os, re, sys

def die(msg: str) -> None:
    print(f"::error::{msg}")
    sys.exit(1)

def get_env_list(name: str) -> list[Path]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        die(f"{name} is empty.")
    items = [Path(x.strip()) for x in raw.splitlines() if x.strip()]
    for p in items:
        if not p.exists():
            die(f"Missing input: {p}")
    return items

def get_env_path(name: str) -> Path:
    val = os.environ.get(name, "").strip()
    if not val:
        die(f"{name} is empty.")
    p = Path(val)
    if name == "LOOKUP_TEMPLATE" and not p.exists():
        die(f"Template not found: {p}")
    return p

def get_env_output_path(name: str) -> Path:
    val = os.environ.get(name, "").strip()
    if not val:
        die(f"{name} is empty.")
    p = Path(val)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

class RobustTableParser(HTMLParser):
    """Extract first table: caption, header row (first <tr> with <th>), and body rows."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.reset_state()
    def reset_state(self):
        self.in_table=False; self.seen_table=False
        self.in_caption=False; self.caption_text_parts=[]; self.caption_links=[]
        self.in_tr=False; self.current_row=[]; self.rows=[]; self.headers=[]
        self.header_locked=False
        self.in_cell=False; self.cell_text_parts=[]; self.cell_html_parts=[]
        self.current_cell_links=[]; self.in_anchor=False; self.anchor_href=""; self.anchor_text_parts=[]
        self.current_tr_has_th=False
    def handle_starttag(self, tag, attrs):
        if tag=="table" and not self.seen_table:
            self.seen_table=True; self.in_table=True
        elif self.in_table and tag=="caption":
            self.in_caption=True
        elif self.in_table and tag=="tr":
            self.in_tr=True; self.current_row=[]; self.current_tr_has_th=False
        elif self.in_tr and tag in ("td","th"):
            self.in_cell=True; self.cell_text_parts=[]; self.cell_html_parts=[]; self.current_cell_links=[]
            if tag=="th": self.current_tr_has_th=True
        if self.in_caption and tag=="a":
            for k,v in attrs:
                if k and k.lower()=="href" and v:
                    self.caption_links.append(v); break
        if self.in_cell and tag not in ("td","th"):
            attrs_str="".join([f' {k}="{v}"' for k,v in attrs if v is not None])
            if tag=="br": self.cell_html_parts.append("<br>")
            else: self.cell_html_parts.append(f"<{tag}{attrs_str}>")
        if self.in_cell and tag=="a":
            for k,v in attrs:
                if k and k.lower()=="href" and v:
                    self.in_anchor=True; self.anchor_href=v; self.anchor_text_parts=[]; break
    def handle_endtag(self, tag):
        if tag=="caption" and self.in_caption:
            self.in_caption=False
        elif tag in ("td","th") and self.in_cell:
            text=unescape("".join(self.cell_text_parts))
            lines=[ln.strip() for ln in text.splitlines() if ln.strip()!=""]
            text_norm="\n".join(lines)
            cell_html="".join(self.cell_html_parts)
            seen=set(); dedup=[]
            for L in self.current_cell_links:
                key=(L.get("href",""), L.get("text",""))
                if key not in seen: seen.add(key); dedup.append(L)
            self.current_row.append((text_norm, cell_html, dedup))
            self.in_cell=False; self.cell_text_parts=[]; self.cell_html_parts=[]; self.current_cell_links=[]
        elif tag=="tr" and self.in_tr:
            if not self.header_locked and self.current_tr_has_th:
                self.headers=[t for (t,_h,_l) in self.current_row]
                self.header_locked=True
            elif self.current_row:
                self.rows.append(self.current_row)
            self.in_tr=False; self.current_row=[]; self.current_tr_has_th=False
        elif tag=="table" and self.in_table:
            self.in_table=False
        if self.in_cell and tag not in ("td","th","br"):
            self.cell_html_parts.append(f"</{tag}>")
        if tag=="a" and self.in_anchor:
            label=unescape("".join(self.anchor_text_parts)).strip()
            self.current_cell_links.append({"href": self.anchor_href, "text": label or self.anchor_href})
            self.in_anchor=False; self.anchor_href=""; self.anchor_text_parts=[]
    def handle_data(self, data):
        if self.in_cell: self.cell_text_parts.append(data); self.cell_html_parts.append(data)
        if self.in_caption: self.caption_text_parts.append(data)
        if self.in_anchor: self.anchor_text_parts.append(data)
    def handle_entityref(self, name):
        ent=f"&{name};"
        if self.in_cell: self.cell_text_parts.append(ent); self.cell_html_parts.append(ent)
        if self.in_caption: self.caption_text_parts.append(ent)
        if self.in_anchor: self.anchor_text_parts.append(ent)
    def handle_charref(self, name):
        ent=f"&#{name};"
        if self.in_cell: self.cell_text_parts.append(ent); self.cell_html_parts.append(ent)
        if self.in_caption: self.caption_text_parts.append(ent)
        if self.in_anchor: self.anchor_text_parts.append(ent)

def normalize_headers(headers):
    out=[]
    for h in headers:
        hh=re.sub(r"\s+"," ",h).strip()
        if hh.lower()=="aural ui" or hh=="Aural UI": hh="AURAL UI"
        out.append(hh)
    return out

def extract_year(s):
    m=re.search(r"\b(?:19|20)\d{2}\b", s or "")
    return m.group(0) if m else ""

def convert(path: Path, sr_name: str):
    parser=RobustTableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    headers=normalize_headers(parser.headers)
    rows_out=[]
    for row in parser.rows:
        cc=row[:len(headers)] + [("", "", [])] * max(0, len(headers)-len(row))
        obj={}; html_map={}; links_map={}
        for i,h in enumerate(headers):
            text_val, html_val, links = cc[i]
            obj[h]=text_val
            if html_val.strip(): html_map[h]=html_val
            if links: links_map[h]=links
        if html_map: obj["_html"]=html_map
        if links_map: obj["_links"]=links_map
        rows_out.append(obj)
    caption = unescape("".join(parser.caption_text_parts)).strip()
    caption = re.sub(r"\s+"," ", caption)
    return {
        "screen_reader": sr_name,
        "caption": caption,
        "date": extract_year(caption),
        "caption_links": parser.caption_links,
        "rows": rows_out
    }

def build_bundle(paths: list[Path]) -> list[dict]:
    mapping = {
        "jaws.html": "JAWS",
        "nvda.html": "NVDA",
        "talkback-android.html": "TalkBack-Android",
        "vo-mac.html": "VO-mac",
        "vo-ios.html": "VO-iOS",
    }
    out=[]
    for p in paths:
        name = mapping.get(p.name.lower(), p.stem)
        out.append(convert(p, name))
    return out

def inject_json(template_html: str, data: list[dict]) -> str:
    rx = re.compile(
        r'(<script[^>]*id=["\'](?:data|html-support-data)["\'][^>]*>\s*)([\s\S]*?)(\s*</script>)',
        re.IGNORECASE,
    )
    if not rx.search(template_html):
        die('Could not find a <script id="data" type="application/json">…</script> block in the template.')
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return rx.sub(rf"\1{payload}\3", template_html)

def main():
    inputs = get_env_list("INPUT_FILES")
    template = get_env_path("LOOKUP_TEMPLATE")
    output = get_env_output_path("OUTPUT_FILE")

    bundle = build_bundle(inputs)
    for sec in bundle:
        if not sec["rows"]:
            die(f"{sec['screen_reader']}: no rows parsed.")

    merged = inject_json(template.read_text(encoding="utf-8"), bundle)
    output.write_text(merged, encoding="utf-8")
    print(f"Wrote: {output}")

if __name__ == "__main__":
    main()
