"""Create an allowlisted source handoff without local data or environments."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL = (
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "pyproject.toml",
    "MANIFEST.in",
    "requirements-dev.lock",
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    "Dockerfile",
    "compose.yaml",
)
DIRECTORIES = ("src/adresplan", "tests", "examples", "docs", ".github", "scripts")
EXTENSIONS = {
    ".py",
    ".md",
    ".json",
    ".html",
    ".css",
    ".js",
    ".txt",
    ".typed",
    ".yml",
    ".yaml",
    ".png",
    ".jpg",
    ".csv",
    ".xlsx",
    ".docx",
    ".svg",
}


def package_source() -> Path:
    paths = [ROOT / name for name in TOP_LEVEL if (ROOT / name).is_file()]
    for folder in DIRECTORIES:
        paths.extend(
            path
            for path in (ROOT / folder).rglob("*")
            if path.is_file() and path.suffix in EXTENSIONS and "__pycache__" not in path.parts
        )
    target = ROOT / "dist/address-plan-1.1.0-source.zip"
    target.parent.mkdir(exist_ok=True)
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    return target


if __name__ == "__main__":
    print(package_source())
