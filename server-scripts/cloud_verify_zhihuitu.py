import hashlib
import pathlib

files = [
    "/app/backend/app/main.py",
    "/app/backend/app/api/v1/charts.py",
    "/app/backend/app/api/v1/templates.py",
    "/app/backend/app/api/v1/auth.py",
    "/app/backend/app/api/v1/__init__.py",
    "/app/app/main.py",
    "/app/app/api/v1/charts.py",
    "/app/app/api/v1/templates.py",
    "/app/app/api/v1/auth.py",
]
print("=== possible backend files ===")
for path in files:
    p = pathlib.Path(path)
    print(path, "EXISTS" if p.exists() else "no")

print("\n=== walk likely app roots ===")
for root in [pathlib.Path("/app"), pathlib.Path("/app/backend")]:
    if not root.exists():
        continue
    print("root", root)
    for child in sorted(root.iterdir())[:30]:
        print(" ", child.name)

# find main.py
print("\n=== find main.py ===")
for p in pathlib.Path("/app").rglob("main.py"):
    if "site-packages" in str(p):
        continue
    print(p)
