#!/usr/bin/env python3
"""
Builds the combined JSON bundle from the 5 support tables and injects it
into the template's <script id="data" type="application/json">…</script>
(or id="html-support-data"). Writes a *new* HTML file (does NOT overwrite
lookup/lookup.html) and also writes a sibling .json for diffing.

Key points
- Robust header selection: pick the header row that contains "Element".
  If none is found, fail fast with a clear error (prevents broken JSON).
- Preserves per-cell raw inner HTML under _html (lists, SVG, etc.)
- Preserves per-cell links under _links as [{ "text", "href" }]
- Normalizes header "Aural UI" to "AURAL UI" (your page already handles it)
"""

from html.parser import HTMLParser
from html import unescape
from pathlib import Path
from datetime import datetime
import json
import os
import re
import sys


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
    Extract the first table's:
      - caption text + links
      - header candidates (rows that contain <th>)
      - data rows (rows with any <td>)
    For each cell we capture: (text, innerHTML, links[]).
    """
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.reset_state()

    def reset_state(self):
        self.in_table = False
        self.table_seen = False

        self.in_caption = False
        self.caption_text = []
        self.caption_links = []

        self.in_thead = False
        self.thead_rows = []  # list[list[(text, html, links)]]

        self.in_tr = False
        self.tr_cells = []
        self.tr_has_th = False
        self.tr_has_td = False

        self.in_cell = False
        self.cell_text = []
        self.cell_html = []

        self.header_candidates = []  # list[list[(text, html, links)]]
        self.data_rows = []          # list[list[(text, html, links)]]

    def handle_starttag(self, tag, attrs):
        if tag == "table" and not self.table_seen:
            self.table_seen = True
            self.in_table = True

        elif self.in_table and tag == "caption":
            self.in_caption = True

        elif self.in_table and tag == "thead":
            self.in_thead = True

        elif self.in_table and tag == "tr":
            self.in_tr = True
            self.tr_cells = []
            self.tr_has_th = False
            self.tr_has_td = False

        elif self.in_tr and tag in ("td", "th"):
            self.in_cell = True
            self.cell_text = []
            self.cell_html = []
            if tag == "th":
                self.tr_has_th = True
            if tag == "td":
                self.tr_has_td = True

        # caption links
        if self.in_caption and tag == "a":
            for k, v in attrs:
                if (k or "").lower() == "href" and v:
                    self.caption_links.append(v)
                    break

        # record inner HTML (not wrapping td/th)
        if self.in_cell and tag not in ("td", "th"):
            attrs_str = "".join([f' {k}="{v}"' for k, v in attrs if v is not None])
            if tag == "br":
                self.cell_html.append("<br>")
            else:
                self.cell_html.append(f"<{tag}{attrs_str}>")

    def handle_endtag(self, tag):
        if tag == "caption" and self.in_caption:
            self.in_caption = False

        elif tag == "thead" and self.in_thead:
            self.in_thead = False

        elif tag in ("td", "th") and self.in_cell:
            text = unescape("".join(self.cell_text))
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            text_norm = "\n".join(lines)
            cell_html = "".join(self.cell_html)

            # collect links from the html we built
            links = []
            for m in re.finditer(
                r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                cell_html,
                flags=re.I | re.S,
            ):
                links.append({
                    "href": m.group(1),
                    "text": re.sub(r"\s+", " ", unescape(m.group(2))).strip()
                })

            self.tr_cells.append((text_norm, cell_html, links))
            self.in_cell = False
            self.cell_text = []
            self.cell_html = []

        elif tag == "tr" and self.in_tr:
            if self.tr_cells:
                if self.tr_has_th and not self.tr_has_td:
                    # header-ish row
                    (self.thead_rows if self.in_thead else self.header_candidates).append(self.tr_cells)
                else:
                    self.data_rows.append(self.tr_cells)
            self.in_tr = False
            self.tr_cells = []
            self.tr_has_th = False
            self.tr_has_td = False

        elif tag == "table" and self.in_table:
            self.in_table = False

        # generic closing for inner HTML (we already added open tag in start)
        if self.in_cell and tag not in ("td", "th", "br"):
            self.cell_html.append(f"</{tag}>")

    def handle_data(self, data):
        if self.in_cell:
            self.cell_text.append(data)
            self.cell_html.append(data)
        if self.in_caption:
            self.caption_text.append(data)


def normalize_headers(headers: list[str]) -> list[str]:
    out = []
    for h in headers:
        hh = re.sub(r"\s+", " ", (h or "")).strip()
        if hh.lower() == "aural ui" or hh == "Aural UI":
            hh = "AURAL UI"
        out.append(hh)
    return out


def extract_year(s: str) -> str:
    m = re.search(r"\b(?:19|20)\d{2}\b", s or "")
    return m.group(0) if m else ""


def choose_header(thead_rows, header_candidates) -> list[str]:
    """
    Prefer a row whose headers include 'Element' (case-insensitive).
    Search order: <thead> rows first, then other header-candidate rows.
    If none match exactly, accept any row that contains 'element' as a substring.
    """
    def rows_to_text(rows):
        # Each row is a list of tuples: (text, html, links). We want the text.
        return [[cell[0] for cell in row] for row in rows]

    # 1) Look in <thead> rows for an exact 'Element'
    for row in rows_to_text(thead_rows):
        norm = normalize_headers(row)
        if any(h.lower() == "element" for h in norm):
            return norm

    # 2) Look in header-candidate rows (those with only <th>)
    for row in rows_to_text(header_candidates):
        norm = normalize_headers(row)
        if any(h.lower() == "element" for h in norm):
            return norm

    # 3) Softer fallback: a header containing 'element' anywhere
    for row in rows_to_text(thead_rows + header_candidates):
        norm = normalize_headers(row)
        if any("element" in h.lower() for h in norm):
            return norm

    # Nothing suitable found
    return []


def convert(path: Path, sr_name: str) -> dict:
    grab = TableGrabber()
    grab.feed(path.read_text(encoding="utf-8", errors="ignore"))

    caption = re.sub(r"\s+", " ", unescape("".join(grab.caption_text)).strip())
    caption_links = grab.caption_links

    headers = choose_header(grab.thead_rows, grab.header_candidates)
    if not headers:
        die(f"{sr_name}: could not find a header row containing 'Element' in {path.name}.")

    # Log chosen headers for diagnostic visibility in Actions
    print(f"{sr_name}: headers = {headers}")

    rows_out = []
    for row in grab.data_rows:
        # align to headers (pad/truncate)
        cells = row[:len(headers)] + [("", "", [])] * max(0, len(headers) - len(row))

        obj = {}
        html_map = {}
        links_map = {}
        for i, h in enumerate(headers):
            txt, html, lks = cells[i]
            obj[h] = txt
            if html.strip():
                html_map[h] = html
            if lks:
                links_map[h] = lks

        if html_map:
            obj["_html"] = html_map
        if links_map:
            obj["_links"] = links_map

        # Skip rows with empty Element (these won't show in the lookup)
        if not obj.get("Element", "").strip():
            continue

        rows_out.append(obj)

    return {
        "screen_reader": sr_name,
        "caption": caption,
        "date": extract_year(caption),
        "caption_links": caption_links,
        "rows": rows_out
    }


def build_bundle(paths: list[Path]) -> list[dict]:
    # Stable display names for the first column
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
    # Replace JSON inside <script id="data" ...>…</script> (or id="html-support-data")
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
    problems = []
    for sec in data:
        rows = sec.get("rows", [])
        if not rows:
            problems.append(f"{sec.get('screen_reader')}: no rows parsed.")
            continue
        miss = sum(1 for r in rows if "Element" not in r or not r["Element"].strip())
        if miss:
            problems.append(f"{sec.get('screen_reader')}: {miss} row(s) missing non-empty 'Element'.")
    if problems:
        for p in problems:
            print(f"::error::{p}")
        die("Validation failed for lookup JSON.")
    print(f"Validation OK: {len(data)} sections, all rows have 'Element'.")


def main():
    inputs = get_env_list("INPUT_FILES")
    template = get_env_path("LOOKUP_TEMPLATE")
    out_html = get_env_output_path()

    bundle = build_bundle(inputs)
    validate_for_lookup(bundle)

    merged = inject_json(template.read_text(encoding="utf-8"), bundle)
    out_html.write_text(merged, encoding="utf-8")
    print(f"Wrote HTML: {out_html}")

    # Also emit a sibling JSON file for diffing in PRs/Actions artifacts
    out_json = out_html.with_suffix(".json")
    out_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote JSON: {out_json}")


if __name__ == "__main__":
    main()
