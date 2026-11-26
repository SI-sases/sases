import json
import sys

data = json.loads(sys.stdin.read() or "{}")
print(json.dumps({"echo": data, "plugin": "example-tool"}, ensure_ascii=False))
