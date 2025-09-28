#!/usr/bin/env python3
"""
Parses a list of HTML "support" pages, produces the combined JSON bundle,
and replaces the JSON inside <script id="data" type="application/json">…</script>
within lookup/lookup.html (or <script id="html-support-data">…</script>).

- Keeps cell innerHTML (lists, SVG, anchors) under _html
- Keeps per-cell links as _links [{text, href}]
- Normalizes header "AURAL UI" to uppercase (for compatibility)
"""

from bs4 import BeautifulSoup
from pathlib import Path
import json
import os
import re
import sys


def die(msg: str) -> None:
    print(f"::error::{msg}")
    sys.exit(1)


def read_inputs() -> tuple[list[Path], Path]:
    raw = os.environ.get("INPUT_FILES", "").strip()
    if not raw:
        die("INPUT_FILES environment variable is empty.")
    inputs = [Path(line.strip()) for line in raw.splitlines() if line.strip()]
    for p in inputs:
        if not p.exists():
            die(f"Input file not found: {p}")
    lookup_file = Path(os.environ.get("LOOKUP_FILE", "lookup/lookup.html"))
    if not lookup_file.exists():
        die(f"Lookup file not found: {lookup_file}")
    return inputs, lookup_file


def caption_text_and_links(tag):
    if not tag:
        return "", []
    text = tag.get_text(" ", strip=True)
    links = [a.get("href") for a in tag.find_all("a", href=True)]
    return text, links


def extract_year(s: str) -> str:
    m = re.search(r"\b(19|20)\d{2}\b", s or "")
    return m.group(0) if m else ""


def pick_headers(table) -> list[str]:
    # Prefer thead, else first row with TH
    thead = table.find("thead")
    if thead:
        ths = thead.find_all(["th", "td"])
        headers = [th.get_text(" ", strip=True) for th in ths]
    else:
        first_tr = table.find("tr")
        headers = [c.get_text(" ", strip=True) for c in first_tr.find_all(["th", "td"])] if first_tr else []

    # Normalize "AURAL UI" to uppercase (matches existing client code)
    out = []
    for h in headers:
        hh = re.sub(r"\s+", " ", (h or "")).strip()
        if hh.lower() == "aural ui" or hh == "Aural UI":
            hh = "AURAL UI"
        out.append(hh)
    return out


def cell_text(cell) -> str:
    # Preserve list items separation with newlines
    return cell.get_text("\n", strip=True)


def cell_html(cell) -> str:
    # Raw inner HTML (no <td>/<th> wrappers)
    return cell.decode_contents()


def cell_links(cell) -> list[dict]:
    out = []
    for a in cell.find_all("a", href=True):
        txt = a.get_text(" ", strip=True)
        href = a.get("href")
        if href:
            out.append({"text": txt, "href": href})
    return out


def parse_table(table) -> tuple[list[str], list[dict]]:
    headers = pick_headers(table)
    body = table.find("tbody")
    trs = (body.find_all("tr") if body else table.find_all("tr")[1:]) or []

    rows = []
    for tr in trs:
        # Use row header th[scope=row] if present
        cells = []
        th_row = tr.find("th", attrs={"scope": "row"})
        if th_row:
            cells.append(th_row)
        cells.extend(tr.find_all("td"))

        # skip structural/empty rows
        if not cells or not any(c.get_text(strip=True) for c in cells):
            continue

        row_obj: dict = {}
        html_map: dict = {}
        links_map: dict = {}

        for i, cell in enumerate(cells):
            hdr = headers[i] if i < len(headers) else f"Col {i+1}"
            txt = cell_text(cell)
            html = cell_html(cell)
            lks = cell_links(cell)

            row_obj[hdr] = txt
            if html.strip():
                html_map[hdr] = html
            if lks:
                links_map[hdr] = lks

        if html_map:
            row_obj["_html"] = html_map
        if links_map:
            row_obj["_links"] = links_map

        rows.append(row_obj)

    return headers, rows


def detect_screen_reader_name(soup: BeautifulSoup, fallback: str) -> str:
    # Prefer H1, remove any trailing "HTML Support"
    h1 = soup.find("h1")
    title = (h1.get_text(" ", strip=True) if h1 else fallback).strip()
    title = re.sub(r"\s*HTML\s*Support\s*$", "", title, flags=re.I)
    # Map common label variants
    if title == "TalkBack":
        title = "TalkBack on Android"
    if title == "TalkBack HTML Support":
        title = "TalkBack on Android"
    return title


def build_bundle(files: list[Path]) -> list[dict]:
    out = []
    for fp in files:
        html = fp.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        table = soup.select_one(".table-wrapper table") or soup.find("table")
        if not table:
            out.append(
                {
                    "screen_reader": detect_screen_reader_name(soup, fp.stem),
                    "caption": "",
                    "date": "",
                    "caption_links": [],
                    "rows": [],
                }
            )
            continue

        cap_text, cap_links = caption_text_and_links(table.find("caption"))
        _, rows = parse_table(table)

        out.append(
            {
                "screen_reader": detect_screen_reader_name(soup, fp.stem),
                "caption": cap_text,
                "date": extract_year(cap_text),
                "caption_links": cap_links,
                "rows": rows,
            }
        )
    return out


def replace_json_in_lookup(lookup_path: Path, data: list[dict]) -> None:
    html = lookup_path.read_text(encoding="utf-8")
    # Prefer <script id="data" type="application/json">, but also accept id="html-support-data"
    rx = re.compile(
        r'(<script[^>]*id=["\'](?:data|html-support-data)["\'][^>]*>\s*)([\s\S]*?)(\s*</script>)',
        re.IGNORECASE,
    )

    if not rx.search(html):
        die(
            f"Could not find a <script id=\"data\" type=\"application/json\">…</script> block in {lookup_path}."
        )

    # Minified JSON, with '</' escaped to avoid prematurely closing the script tag in HTML parsers
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    updated = rx.sub(rf"\1{payload}\3", html)

    if updated == html:
        print("No change detected in embedded JSON.")
    else:
        lookup_path.write_text(updated, encoding="utf-8")
        print(f"Updated embedded JSON in {lookup_path}")


def main():
    inputs, lookup_file = read_inputs()
    bundle = build_bundle(inputs)
    replace_json_in_lookup(lookup_file, bundle)


if __name__ == "__main__":
    main()
