#!/usr/bin/env python3
"""Convert a Markdown audit report into a Word (.docx) document.

Standard-library only — no pip install. A .docx is a ZIP of OOXML parts, so we
build the minimal set of parts a reader needs and stream them out with zipfile.

This is the canonical copy. An identical copy lives in every skill's scripts/
folder so each skill stays self-contained (the installer copies skill folders
individually). tools/check_shared.py asserts the copies match this file.

Supported Markdown: ATX headings (#..######), paragraphs, unordered lists
(-, *, +), ordered lists (1.), pipe tables, blockquotes, horizontal rules
(---), fenced code blocks (```), and inline **bold**, *italic*, `code`, and
[links](url). Anything fancier degrades to plain text rather than failing.

Usage:
    python3 md_to_docx.py report.md --output report.docx
    python3 md_to_docx.py report.md --title "Meta Data Audit" -o report.docx
    cat report.md | python3 md_to_docx.py - -o report.docx
"""

import argparse
import re
import sys
import zipfile
from xml.sax.saxutils import escape

# ---------------------------------------------------------------------------
# Inline parsing: a Markdown line -> a list of (text, style) runs.
# style is a set drawn from {"bold", "italic", "code"}; links carry a url.
# ---------------------------------------------------------------------------

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_TOKEN_RE = re.compile(
    r"(\*\*.+?\*\*|__.+?__|\*[^*]+?\*|_[^_]+?_|`[^`]+?`)", re.DOTALL
)


def _split_links(text):
    """Yield (text, url_or_None) segments, pulling [label](url) out of text."""
    pos = 0
    for m in _LINK_RE.finditer(text):
        if m.start() > pos:
            yield text[pos : m.start()], None
        yield m.group(1), m.group(2)
        pos = m.end()
    if pos < len(text):
        yield text[pos:], None


def parse_inline(text):
    """Return a list of run dicts: {text, bold, italic, code, url}."""
    runs = []
    for segment, url in _split_links(text):
        for part in _TOKEN_RE.split(segment):
            if not part:
                continue
            bold = italic = code = False
            inner = part
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                bold, inner = True, part[2:-2]
            elif part.startswith("__") and part.endswith("__") and len(part) > 4:
                bold, inner = True, part[2:-2]
            elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                code, inner = True, part[1:-1]
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                italic, inner = True, part[1:-1]
            elif part.startswith("_") and part.endswith("_") and len(part) > 2:
                italic, inner = True, part[1:-1]
            runs.append(
                {"text": inner, "bold": bold, "italic": italic, "code": code, "url": url}
            )
    return runs or [{"text": "", "bold": False, "italic": False, "code": False, "url": None}]


# ---------------------------------------------------------------------------
# Block parsing: Markdown text -> a list of block dicts.
# ---------------------------------------------------------------------------


def parse_blocks(md):
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # closing fence
            blocks.append({"type": "code", "lines": code_lines})
            continue

        # Blank line
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if re.fullmatch(r"(\*\s*){3,}|(-\s*){3,}|(_\s*){3,}", stripped):
            blocks.append({"type": "hr"})
            i += 1
            continue

        # ATX heading
        m = re.match(r"(#{1,6})\s+(.*)$", stripped)
        if m:
            blocks.append(
                {"type": "heading", "level": len(m.group(1)), "text": m.group(2).strip()}
            )
            i += 1
            continue

        # Table: a header row followed by a |---|---| separator
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            header = _split_row(line)
            i += 2  # skip header + separator
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append({"type": "table", "header": header, "rows": rows})
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append({"type": "quote", "text": " ".join(quote)})
            continue

        # List (unordered or ordered) — consume consecutive item lines
        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            items = []
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            while i < n and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i]):
                indent = len(lines[i]) - len(lines[i].lstrip())
                content = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", lines[i])
                items.append({"level": indent // 2, "text": content})
                i += 1
            blocks.append({"type": "list", "ordered": ordered, "items": items})
            continue

        # Paragraph — gather until a blank line or a block starter
        para = [stripped]
        i += 1
        while i < n and lines[i].strip() and not _is_block_start(lines[i], lines, i):
            para.append(lines[i].strip())
            i += 1
        blocks.append({"type": "para", "text": " ".join(para)})

    return blocks


def _split_row(line):
    line = line.strip()
    # Protect escaped pipes (\|) so they survive the column split as literals.
    line = line.replace("\\|", "\x00")
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip().replace("\x00", "|") for c in line.split("|")]


def _is_block_start(line, lines, i):
    s = line.strip()
    if re.match(r"#{1,6}\s+", s):
        return True
    if s.startswith("```") or s.startswith(">"):
        return True
    if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
        return True
    if re.fullmatch(r"(\*\s*){3,}|(-\s*){3,}|(_\s*){3,}", s):
        return True
    if "|" in line and i + 1 < len(lines) and "-" in lines[i + 1] and re.match(
        r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]
    ):
        return True
    return False


# ---------------------------------------------------------------------------
# OOXML generation
# ---------------------------------------------------------------------------

_HEADING_SIZE = {1: 36, 2: 30, 3: 26, 4: 22, 5: 20, 6: 18}  # half-points


def _run_xml(run, rels, force_style=None):
    props = []
    if run.get("bold"):
        props.append("<w:b/>")
    if run.get("italic"):
        props.append("<w:i/>")
    if run.get("code") or force_style == "code":
        props.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
        props.append('<w:shd w:val="clear" w:fill="F2F2F2"/>')
    if run.get("url"):
        props.append('<w:color w:val="0563C1"/><w:u w:val="single"/>')
    rpr = "<w:rPr>%s</w:rPr>" % "".join(props) if props else ""
    text = escape(run.get("text", ""))
    r = '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, text)
    if run.get("url"):
        rid = rels.add(run["url"])
        return '<w:hyperlink r:id="%s">%s</w:hyperlink>' % (rid, r)
    return r


def _para(runs_xml, style=None, before=120, after=120):
    ppr = "<w:pPr>"
    if style:
        ppr += '<w:pStyle w:val="%s"/>' % style
    ppr += '<w:spacing w:before="%d" w:after="%d"/>' % (before, after)
    ppr += "</w:pPr>"
    return "<w:p>%s%s</w:p>" % (ppr, runs_xml)


class Rels:
    """Accumulates hyperlink relationships for document.xml.rels."""

    def __init__(self):
        self.items = []  # (rId, target)

    def add(self, target):
        rid = "rId%d" % (len(self.items) + 100)
        self.items.append((rid, target))
        return rid

    def xml(self):
        rels = "".join(
            '<Relationship Id="%s" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            'Target="%s" TargetMode="External"/>' % (rid, escape(t))
            for rid, t in self.items
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + rels
            + "</Relationships>"
        )


def blocks_to_body(blocks, rels):
    out = []
    for b in blocks:
        t = b["type"]
        if t == "heading":
            size = _HEADING_SIZE.get(b["level"], 18)
            runs = parse_inline(b["text"])
            runs_xml = ""
            for r in runs:
                r = dict(r, bold=True)
                runs_xml += _run_xml_sized(r, rels, size)
            out.append(_para(runs_xml, before=240, after=120))
        elif t == "para":
            runs_xml = "".join(_run_xml(r, rels) for r in parse_inline(b["text"]))
            out.append(_para(runs_xml))
        elif t == "quote":
            runs_xml = "".join(_run_xml(r, rels) for r in parse_inline(b["text"]))
            ppr = (
                "<w:pPr><w:ind w:left=\"480\"/>"
                '<w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="CCCCCC"/></w:pBdr>'
                '<w:spacing w:before="120" w:after="120"/></w:pPr>'
            )
            out.append("<w:p>%s%s</w:p>" % (ppr, runs_xml))
        elif t == "code":
            for ln in (b["lines"] or [""]):
                run = {"text": ln, "code": True}
                ppr = (
                    '<w:pPr><w:shd w:val="clear" w:fill="F2F2F2"/>'
                    '<w:spacing w:before="0" w:after="0"/></w:pPr>'
                )
                out.append("<w:p>%s%s</w:p>" % (ppr, _run_xml(run, rels, force_style="code")))
        elif t == "list":
            for idx, item in enumerate(b["items"], 1):
                bullet = "%d." % idx if b["ordered"] else "•"
                indent = 360 + item["level"] * 360
                lead = {"text": bullet + "  ", "bold": False}
                runs_xml = _run_xml(lead, rels) + "".join(
                    _run_xml(r, rels) for r in parse_inline(item["text"])
                )
                ppr = '<w:pPr><w:ind w:left="%d" w:hanging="360"/><w:spacing w:before="40" w:after="40"/></w:pPr>' % indent
                out.append("<w:p>%s%s</w:p>" % (ppr, runs_xml))
        elif t == "table":
            out.append(_table_xml(b, rels))
        elif t == "hr":
            out.append(
                '<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" '
                'w:space="1" w:color="CCCCCC"/></w:pBdr></w:pPr></w:p>'
            )
    return "".join(out)


def _run_xml_sized(run, rels, size):
    props = ["<w:b/>"] if run.get("bold") else []
    props.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size))
    rpr = "<w:rPr>%s</w:rPr>" % "".join(props)
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, escape(run.get("text", "")))


def _cell(text, rels, header=False):
    runs = parse_inline(text)
    if header:
        runs = [dict(r, bold=True) for r in runs]
    runs_xml = "".join(_run_xml(r, rels) for r in runs)
    shd = '<w:shd w:val="clear" w:fill="F2F2F2"/>' if header else ""
    tcpr = "<w:tcPr>%s</w:tcPr>" % shd if shd else ""
    return (
        "<w:tc>%s<w:p><w:pPr><w:spacing w:before=\"20\" w:after=\"20\"/></w:pPr>%s</w:p></w:tc>"
        % (tcpr, runs_xml)
    )


def _table_xml(b, rels):
    borders = "".join(
        '<w:%s w:val="single" w:sz="4" w:space="0" w:color="BBBBBB"/>' % edge
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    tblpr = (
        '<w:tblPr><w:tblW w:w="0" w:type="auto"/>'
        "<w:tblBorders>%s</w:tblBorders></w:tblPr>" % borders
    )
    rows = ["<w:tr>%s</w:tr>" % "".join(_cell(c, rels, header=True) for c in b["header"])]
    width = len(b["header"])
    for row in b["rows"]:
        cells = (row + [""] * width)[:width]
        rows.append("<w:tr>%s</w:tr>" % "".join(_cell(c, rels) for c in cells))
    return "<w:tbl>%s%s</w:tbl><w:p/>" % (tblpr, "".join(rows))


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>'
)


def build_docx(md, title=None):
    rels = Rels()
    blocks = parse_blocks(md)
    if title:
        blocks = [{"type": "heading", "level": 1, "text": title}] + blocks
    body = blocks_to_body(blocks, rels)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body>" + body + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>'
    )
    return document, rels.xml()


def write_docx(md, path, title=None):
    document, doc_rels = build_docx(md, title)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", doc_rels)


def main():
    ap = argparse.ArgumentParser(description="Convert a Markdown report to .docx")
    ap.add_argument("input", help="Markdown file, or '-' to read stdin")
    ap.add_argument("-o", "--output", required=True, help="output .docx path")
    ap.add_argument("--title", help="optional H1 title to prepend")
    args = ap.parse_args()

    if args.input == "-":
        md = sys.stdin.read()
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            md = f.read()

    write_docx(md, args.output, title=args.title)
    print("Wrote %s" % args.output, file=sys.stderr)


if __name__ == "__main__":
    main()
