def test_office_read_docx(tmp_path, monkeypatch):
    from docx import Document
    from agi.tools import build_default_registry

    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    doc = Document()
    doc.add_paragraph("SASES office test")
    doc.save(str(tmp_path / "a.docx"))
    out = build_default_registry().invoke("main", "office.read", {"path": "a.docx"})
    assert out["ok"] is True
    assert "SASES office test" in out["text"]
