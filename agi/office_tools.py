"""Read-only Office document extraction for the main AGI."""
from __future__ import annotations

from .fs_tools import _safe


def read(args: dict) -> dict:
    try:
        path = _safe(args.get("path") or "")
        if not path.is_file():
            return {"ok": False, "error": "not a file"}
        suffix = path.suffix.lower()
        limit = max(1, min(int(args.get("max_chars") or 20000), 100000))
        if suffix == ".docx":
            from docx import Document
            doc = Document(str(path))
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(c.text.strip() for c in row.cells))
            return {"ok": True, "path": str(path), "text": "\n".join(parts)[:limit]}
        if suffix == ".xlsx":
            from openpyxl import load_workbook
            wb = load_workbook(str(path), read_only=True, data_only=True)
            parts = []
            for ws in wb.worksheets:
                parts.append(f"# {ws.title}")
                for row in ws.iter_rows(values_only=True):
                    vals = ["" if v is None else str(v) for v in row]
                    if any(vals):
                        parts.append(" | ".join(vals))
            wb.close()
            return {"ok": True, "path": str(path), "text": "\n".join(parts)[:limit]}
        if suffix == ".pptx":
            from pptx import Presentation
            prs = Presentation(str(path))
            parts = []
            for i, slide in enumerate(prs.slides, 1):
                parts.append(f"# Slide {i}")
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        parts.append(shape.text.strip())
            return {"ok": True, "path": str(path), "text": "\n".join(parts)[:limit]}
        return {"ok": False, "error": "unsupported office format"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def write(args: dict) -> dict:
    if not args.get("_approved"):
        from .fs_tools import _create_write_approval
        return _create_write_approval("office.write", args)
    try:
        path = _safe(args.get("path") or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        suffix = path.suffix.lower()
        if suffix == ".docx":
            from docx import Document
            doc = Document()
            for line in (args.get("lines") or str(args.get("text") or "").splitlines()):
                doc.add_paragraph(str(line))
            for table in args.get("tables") or []:
                rows = [list(r) for r in table if isinstance(r, list)]
                if not rows:
                    continue
                width = max(len(r) for r in rows)
                table_obj = doc.add_table(rows=len(rows), cols=width)
                for ri, row in enumerate(rows):
                    for ci, cell in enumerate(row):
                        table_obj.cell(ri, ci).text = str(cell)
            for image in args.get("images") or []:
                image_path = _safe(image)
                if image_path.is_file():
                    doc.add_picture(str(image_path))
            header = str(args.get("header") or "").strip()
            footer = str(args.get("footer") or "").strip()
            if header:
                section = doc.sections[0]
                section.header.paragraphs[0].text = header
            if footer:
                section = doc.sections[0]
                section.footer.paragraphs[0].text = footer
            doc.save(str(path))
        elif suffix == ".xlsx":
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            for row in args.get("rows") or []:
                ws.append(list(row))
            if args.get("bold_header") and ws.max_row >= 1:
                from openpyxl.styles import Font
                for cell in ws[1]:
                    cell.font = Font(bold=True)
            for column, width in (args.get("widths") or {}).items():
                ws.column_dimensions[str(column)].width = float(width)
            wb.save(str(path))
        elif suffix == ".pptx":
            from pptx import Presentation
            prs = Presentation()
            for line in args.get("slides") or []:
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = str(line)
            prs.save(str(path))
        else:
            return {"ok": False, "error": "unsupported office format"}
        return {"ok": True, "path": str(path)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
