"""Build a clean source archive without local environments, secrets or user data."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
output = root.parent / "pocketledger-improved.zip"
excluded_dirs = {".git", ".venv", "venv", "env", "__pycache__", "staticfiles", "media", "node_modules", ".pytest_cache", ".idea", ".vscode"}
files = []
for path in root.rglob("*"):
    relative = path.relative_to(root)
    if not path.is_file() or excluded_dirs.intersection(relative.parts):
        continue
    if path.name.startswith(".env") and path.name != ".env.example":
        continue
    if path.suffix in {".pyc", ".pyo", ".sqlite3", ".db", ".zip", ".log"} or ".sqlite3-" in path.name:
        continue
    files.append(path)

with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, Path("pocketledger") / path.relative_to(root))
with ZipFile(output) as archive:
    assert archive.testzip() is None
print(f"Packaged {len(files)} files: {output} ({output.stat().st_size:,} bytes)")
