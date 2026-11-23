import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fd, path = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.environ["SASES_DB_PATH"] = path
os.environ["ENABLE_HIVE"] = "false"

from core.db import init_db  # noqa: E402
init_db()

from fastapi.testclient import TestClient  # noqa: E402
from core.bootstrap import create_app  # noqa: E402
from core import node_identity as ni  # noqa: E402

app = create_app()
client = TestClient(app)

r = client.get("/version")
print("version", r.status_code, r.json().get("node_id"))

r = client.get("/node/whoami")
print("whoami-no-header", r.status_code)

_priv, pub = ni.generate_node_keypair()
node = ni.create_node(1, "edge", ed25519_pubkey=pub)
manifest = ni.issue_manifest(node["node_id"])
r = client.get("/node/whoami", headers={"X-SASES-Node-Manifest": manifest})
print("whoami", r.status_code, r.json().get("profile") if r.status_code == 200 else r.text[:120])

r = client.post("/node/creator/check?capability=publish_tool", headers={"X-SASES-Node-Manifest": manifest})
print("creator-check-edge", r.status_code)

os.remove(path)
raise SystemExit(0)
