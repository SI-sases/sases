import http.server
import json
import os
import socketserver
import threading
from functools import partial

from scripts.client_release import build
from scripts.client_updater import check_and_apply


def _serve(directory):
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_client_update_replaces_code_and_preserves_data(tmp_path):
    root = tmp_path / "client"
    (root / "core").mkdir(parents=True)
    (root / "static").mkdir()
    (root / "scripts").mkdir()
    (root / "core" / "old.txt").write_text("old", encoding="utf-8")
    (root / "users.db").write_text("keep-db", encoding="utf-8")
    (root / ".env").write_text("KEEP=1", encoding="utf-8")
    (root / "client_version.json").write_text(
        json.dumps({"version": "1.0.0", "build": "old"}), encoding="utf-8"
    )

    src = tmp_path / "src"
    (src / "core").mkdir(parents=True)
    (src / "static").mkdir()
    (src / "scripts").mkdir()
    (src / "core" / "new.txt").write_text("new", encoding="utf-8")
    (src / "static" / "app.js").write_text("// v2", encoding="utf-8")
    (src / "scripts" / "run_forever.py").write_text("# v2", encoding="utf-8")

    dist = tmp_path / "dist"
    (dist / "core").mkdir(parents=True)
    (dist / "core" / "new.txt").write_text("new", encoding="utf-8")
    (dist / "static").mkdir()
    (dist / "static" / "app.js").write_text("// v2", encoding="utf-8")
    (dist / "scripts").mkdir()
    (dist / "scripts" / "run_forever.py").write_text("# v2", encoding="utf-8")

    zip_path = dist / "client_update.zip"
    build(str(dist), str(zip_path), "1.1.0", "newbuild")
    from scripts.client_release import _sha256
    manifest = {
        "version": "1.1.0",
        "build": "newbuild",
        "package_url": "client_update.zip",
        "sha256": _sha256(str(zip_path)),
        "size": os.path.getsize(zip_path),
    }
    (dist / "client_version.json").write_text(json.dumps(manifest), encoding="utf-8")

    server, base = _serve(str(dist))
    try:
        result = check_and_apply(str(root), [base + "/client_version.json"], apply=True)
    finally:
        server.shutdown()
        server.server_close()

    assert result["updated"] is True
    assert (root / "core" / "new.txt").exists()
    assert not (root / "core" / "old.txt").exists()
    assert (root / "users.db").read_text(encoding="utf-8") == "keep-db"
    assert (root / ".env").read_text(encoding="utf-8") == "KEEP=1"
    assert json.loads((root / "client_version.json").read_text(encoding="utf-8"))["version"] == "1.1.0"
