#!/usr/bin/env python3
"""
Builds the combined JSON bundle from the 5 support tables and injects it
into the template's <script id="data" type="application/json">…</script>.
Writes a *new* HTML file (does NOT overwrite lookup/lookup.html) and also
drops a sibling JSON file for easy diffs.

Fixes:
- Robust header selection: choose the header row that contains "Element"
  (case-insensitive). If none, fail fast with a clear error.
- Keeps _html (raw innerHTML) and _links [{text,href}] per cell.
- Normalizes "Aural UI" header to "AURAL UI" (your page already handles it).
"""

from html.parser import HTMLParser
from html import unescape
from pathlib import Path
from datetime import datetime
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

def get_env_output_path() -> Path:
    val = os.environ.get("OUTPUT_FILE", "").strip()
    if not val:
        base = (os.environ.get("OUTPUT_BASENAME") or "lookup.auto").strip() or "lookup.auto"
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        val = f"lookup/{base}.{ts}.html"
        print(f"OUTPUT_FILE not set; defaulting to {val}")
    p = Path(val)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

class TableGrabber(HTMLParser):
    """
    Extracts the *first* table:
      - caption text + links
      - all <tr>, distinguishing 'header candidates' (rows that contain <th>)
        from 'data rows' (rows with any <td>).
      - for each cell, capture (text, innerHTML, links[]).
    We then choose the actual header row by *content* later.
    """
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.reset_state()

    def reset_state(self):
        self.in_table = False; self.table_seen = False
        self.in_caption = False; self.caption_text = []; self.caption_links = []
        self.in_tr = False; self.tr_cells = []; self.tr_has_th = False; self.tr_has_td = False
        self.in_cell = False; self.cell_text = []; self.cell_html = []
        self.in_anchor = False; self.anchor_href = ""; self.anchor_text = []
        self.header_candidates = []   # list[list[(text, html, links)]]
        self.data_rows = []           # list[list[(text, html, links)]]

    def handle_starttag(self, tag, attrs):
        if tag == "table" and not self.table_seen:
            self.table_seen = True; self.in_table = True
        elif self.in_table and tag == "caption":
            self.in_caption = True
        elif self.in_table and tag == "tr":
            self.in_tr = True; self.tr_cells = []
            self.tr_has_th = False; self.tr_has_td = False
        elif self.in_tr and tag in ("td","th"):
            self.in_cell = True; self.cell_text = []; self.cell_html = []
            if tag == "th": self.tr_has_th = True
            if tag == "td": self.tr_has_td = True

        # caption links
        if self.in_caption and tag == "a":
            for k,v in attrs:
                if (k or "").lower() == "href" and v:
                    self.caption_links.append(v); break

        # record inner HTML (not wrapping td/th themselves)
        if self.in_cell and tag not in ("td","th"):
            attrs_str = "".join([f' {k}="{v}"' for k,v in attrs if v is not None])
            if tag == "br":
                self.cell_html.append("<br>")
            else:
                self.cell_html.append(f"<{tag}{attrs_str}>")

        # link tracking in cells
        if self.in_cell and tag == "a":
            for k,v in attrs:
                if (k or "").lower() == "href" and v:
                    self.in_anchor = True; self.anchor_href = v; self.anchor_text = []; break

    def handle_endtag(self, tag):
        if tag == "caption" and self.in_caption:
            self.in_caption = False

        elif tag in ("td","th") and self.in_cell:
            text = unescape("".join(self.cell_text))
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            text_norm = "\n".join(lines)
            cell_html = "".join(self.cell_html)

            # finalize <a>
            if self.in_anchor:
                label = unescape("".join(self.anchor_text)).strip()
                # push the last link if any lingering (rare)
                # but the link list is captured in handle_data/handle_endtag('a'), so no-op here
                self.in_anchor = False; self.anchor_href = ""; self.anchor_text = []

            # NOTE: we gather links in handle_endtag('a'); but to keep code simple,
            # reuse a tiny parser: find anchors and collect href+text from the html we built
            links = []
            # very small, safe scan (we already appended real <a> start and inner text)
            for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', cell_html, flags=re.I|re.S):
                links.append({"href": m.group(1), "text": re.sub(r"\s+", " ", unescape(m.group(2))).strip()})

            self.tr_cells.append((text_norm, cell_html, links))
            self.in_cell = False; self.cell_text = []; self.cell_html = []

        elif tag == "tr" and self.in_tr:
            if self.tr_cells:
                if self.tr_has_th and not self.tr_has_td:
                    self.header_candidates.append(self.tr_cells)
                else:
                    self.data_rows.append(self.tr_cells)
            self.in_tr = False; self.tr_cells = []; self.tr_has_th = False; self.tr_has_td = False

        elif tag == "table" and self.in_table:
            self.in_table = False

        # close tags in cell_html when needed
        if self.in_cell and tag not in ("td","th","br"):
            self.cell_html.append(f"</{tag}>")

        if tag == "a" and self.in_anchor:
            label = unescape("".join(self.anchor_text)).strip()
            self.cell_html.append(label)
            self.cell_html.append("</a>")
            self.in_anchor = False; self.anchor_href = ""; self.anchor_text = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell_text.append(data); self.cell_html.append(data)
        if self.in_caption:
            self.caption_text.append(data)
        if self.in_anchor:
            self.anchor_text.append(data)

def normalize_headers(headers):
    out = []
    for h in headers:
        hh = re.sub(r"\s+"," ", h or "").strip()
        if hh.lower() == "aural ui" or hh == "Aural UI":
            hh = "AURAL UI"
        out.append(hh)
    return out

def extract_year(s):
    m = re.search(r"\b(?:19|20)\d{2}\b", s or "")
    return m.group(0) if m else ""

def choose_header(candidates: list[list[tuple]]) -> list[str]:
    """
    Pick the header row by content. Prefer a row whose headers include 'Element'
    (case-insensitive). Else, if exactly one candidate exists, use it.
    Else, fail—better to stop than emit broken JSON.
    """
    if not candidates:
        return []
    # Convert candidates to text lists
    text_rows = [[c[0] for c in row] for row in candidates]  # c[0] = text
    # Normalize and look for 'Element'
    normalized = [normalize_headers(r) for r in text_rows]
    for r in normalized:
        if any(h.strip().lower() == "element" for h in r):
            return r
    if len(normalized) == 1:
        return normalized[0]
    # Try a softer match ('Element' appears as part of header like 'Element ')
    for r in normalized:
        if any("element" in h.lower() for h in r):
            return r
    # No suitable header row found
    return []

def convert(path: Path, sr_name: str) -> dict:
    grab = TableGrabber()
    grab.feed(path.read_text(encoding="utf-8", errors="ignore"))

    caption = re.sub(r"\s+"," ", unescape("".join(grab.caption_text)).strip())
    caption_links = grab.caption_links
    headers = choose_header(grab.header_candidates)
    if not headers:
        die(f"{sr_name}: could not find a valid header row containing 'Element' in {path.name}.")

    rows_out = []
    for row in grab.data_rows:
        # pad/truncate to header count
        cells = row[:len(headers)] + [("", "", [])] * max(0, len(headers) - len(row))
        obj = {}; html_map = {}; links_map = {}
        for i, h in enumerate(headers):
            txt, html, lks = cells[i]
            obj[h] = txt
            if html.strip(): html_map[h] = html
            if lks: links_map[h] = lks
        if html_map: obj["_html"] = html_map
        if links_map: obj["_links"] = links_map
        rows_out.append(obj)

    return {
        "screen_reader": sr_name,
        "caption": caption,
        "date": extract_year(caption),
        "caption_links": caption_links,
        "rows": rows_out
    }

def build_bundle(paths: list[Path]) -> list[dict]:
    # Keep the display names stable for the first column in your table
    mapping = {
        "jaws.html": "JAWS",
        "nvda.html": "NVDA",
        "talkback-android.html": "TalkBack on Android",
        "vo-mac.html": "VoiceOver on Mac",
        "vo-ios.html": "VoiceOver on iOS",
    }
    out = []
    for p in paths:
        name = mapping.get(p.name.lower(), p.stem)
        out.append(convert(p, name))
    return out

def inject_json(template_html: str, data: list[dict]) -> str:
    rx = re.compile(
        r'(<script[^>]*id=["\'](?:data|html-support-data)["\'][^>]*>\s*)([\s\S]*?)(\s*</script>)',
        re.IGNORECASE,
    )
    m = rx.search(template_html)
    if not m:
        die('Could not find a <script id="data" type="application/json">…</script> block in the template.')
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return rx.sub(rf"\1{payload}\3", template_html)

def validate_for_lookup(data: list[dict]) -> None:
    # Ensure every section has rows and that 'Element' exists on rows
    problems = []
    for sec in data:
        rows = sec.get("rows", [])
        if not rows:
            problems.append(f"{sec.get('screen_reader')}: no rows parsed.")
            continue
        miss = sum(1 for r in rows if "Element" not in r)
        if miss:
            problems.append(f"{sec.get('screen_reader')}: {miss} row(s) missing 'Element'.")
    if problems:
        for p in problems: print(f"::error::{p}")
        die("Validation failed for lookup JSON.")
    print(f"Validation OK: {len(data)} sections.")

def main():
    inputs = get_env_list("INPUT_FILES")
    template = get_env_path("LOOKUP_TEMPLATE")
    out_html = get_env_output_path()

    bundle = build_bundle(inputs)
    validate_for_lookup(bundle)

    merged = inject_json(template.read_text(encoding="utf-8"), bundle)
    out_html.write_text(merged, encoding="utf-8")
    print(f"Wrote HTML: {out_html}")

    # Also emit a sibling JSON file for diffing in PRs
    out_json = out_html.with_suffix(".json")
    out_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote JSON: {out_json}")

if __name__ == "__main__":
    main()
