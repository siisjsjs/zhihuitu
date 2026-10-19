import hashlib
import pathlib

files = [
    "backend/app/main.py",
    "backend/app/api/v1/charts.py",
    "backend/app/api/v1/templates.py",
    "backend/app/api/v1/auth.py",
    "backend/app/api/v1/__init__.py",
    "backend/app/core/config.py",
    "backend/app/services/template_registry.py",
]
print("=== zhihuitu backend hashes ===")
for rel in files:
    p = pathlib.Path("/app") / rel
    if not p.exists():
        print(rel, "MISSING")
        continue
    data = p.read_bytes()
    print(f"{rel}\t{len(data)}\t{hashlib.md5(data).hexdigest()}")
