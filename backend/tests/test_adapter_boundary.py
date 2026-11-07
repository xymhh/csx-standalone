from pathlib import Path


def test_vendor_imports_are_limited_to_drive_adapters():
    package = Path(__file__).parents[1] / "csx"
    offenders = []
    for source in package.rglob("*.py"):
        relative = source.relative_to(package).as_posix()
        if relative.startswith(("adapters/drive/", "adapters/search/", "vendor/")):
            continue
        for number, line in enumerate(source.read_text().splitlines(), 1):
            if "csx.vendor" in line and line.lstrip().startswith(("from ", "import ")):
                offenders.append(f"{relative}:{number}:{line.strip()}")
    assert offenders == []
