from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath


ADDON_NAME = "Secret Paint"
VERSIONS_DIRNAME = "VERSIONS"
WEBSITE_UPDATER_DIRNAME = "Website vers with git updater"

UPDATER_FILENAMES = {
    "addon_updater.py",
    "addon_updater_ops.py",
}
REQUIRED_BASE_FILES = (
    Path("__init__.py"),
    Path("secret_paint_shared.py"),
    Path("secret_paint_world_paint.py"),
    Path("blender_manifest.toml"),
)
NO_UPDATER_INIT_FORBIDDEN_MARKERS = (
    "addon_updater",
    "auto_check_update",
    "updater_interval_",
    "auto_updater_disabled_reason",
    "auto_updater_status",
)

PACKAGE_IGNORE_DIRS = {
    "__pycache__",
    ".agents",
    ".codex",
    ".git",
    ".idea",
    "mocap type",
    "secret paint_updater",
    "versions",
}
PACKAGE_IGNORE_FILENAMES = {
    ".gitignore",
    "agents.md",
    "pbrpreset.blend",
    "secret_paint_private_impl.py",
    "secret_paint_public_init_template.py",
    "secret_paint_world_paint_perf_log.txt",
}
PACKAGE_IGNORE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".zip",
}
PACKAGE_IGNORE_NAME_PATTERNS = (
    re.compile(r"^update and zip(?: .*)?\.py$", re.IGNORECASE),
    re.compile(r" - Copy(?: \(\d+\))?(?=\.)", re.IGNORECASE),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Package Secret Paint into a no-updater zip and a website zip "
            "that keeps the GitHub updater."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview version updates and zip outputs without writing files.",
    )
    return parser.parse_args()


def log(message: str) -> None:
    print(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str, *, dry_run: bool) -> None:
    if dry_run:
        log(f"[dry-run] write {path}")
        return
    path.write_text(text, encoding="utf-8")


def parse_version_tuple(version_name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version_name.split("."))


def version_from_script_filename(script_path: Path) -> tuple[int, ...]:
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)+)$", script_path.stem)
    if match is None:
        raise RuntimeError(
            "Packaging script filename must end with a version, "
            "for example 'update and zip 1.9.9.py'"
        )
    return parse_version_tuple(match.group(1))


def replace_once(text: str, pattern: str, replacement: str, *, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match while updating {label}")
    return updated


def update_init_version(init_path: Path, version_tuple: tuple[int, ...], *, dry_run: bool) -> str:
    version_csv = ", ".join(str(part) for part in version_tuple)
    updated = replace_once(
        read_text(init_path),
        r'("version"\s*:\s*)\([^)]*\)',
        rf"\g<1>({version_csv})",
        label="bl_info version",
    )
    compile(updated, str(init_path), "exec")
    write_text(init_path, updated, dry_run=dry_run)
    return updated


def update_manifest_version(manifest_path: Path, version_tuple: tuple[int, ...], *, dry_run: bool) -> str:
    version_text = ".".join(str(part) for part in version_tuple)
    updated = replace_once(
        read_text(manifest_path),
        r'(^version\s*=\s*")[^"]+(")',
        rf"\g<1>{version_text}\2",
        label="manifest version",
    )
    write_text(manifest_path, updated, dry_run=dry_run)
    return updated


def remove_line_range_once(text: str, start_marker: str, end_marker: str, *, label: str) -> str:
    lines = text.splitlines(keepends=True)
    start_index = next(
        (index for index, line in enumerate(lines) if line.strip() == start_marker),
        None,
    )
    if start_index is None:
        raise RuntimeError(f"Could not find start of {label}")

    end_index = next(
        (
            index
            for index in range(start_index, len(lines))
            if lines[index].strip() == end_marker
        ),
        None,
    )
    if end_index is None:
        raise RuntimeError(f"Could not find end of {label}")

    del lines[start_index : end_index + 1]
    return "".join(lines)


def remove_line_containing_once(text: str, snippet: str, *, label: str) -> str:
    lines = text.splitlines(keepends=True)
    matching_indexes = [
        index for index, line in enumerate(lines) if snippet in line
    ]
    if len(matching_indexes) != 1:
        raise RuntimeError(
            f"Expected exactly one line while removing {label}, found {len(matching_indexes)}"
        )

    del lines[matching_indexes[0]]
    return "".join(lines)


def build_no_updater_init(init_text: str) -> str:
    stripped = remove_line_range_once(
        init_text,
        "addon_path = Path(__file__).resolve().parent",
        "addon_updater_ops = _addon_updater_ops",
        label="updater bootstrap block",
    )
    stripped = remove_line_range_once(
        stripped,
        "if addon_updater_ops is not None:",
        "box.label(text=auto_updater_disabled_reason, icon='INFO')",
        label="updater preferences UI",
    )
    for snippet, label in (
        ("auto_check_update : bpy.props.BoolProperty", "updater auto-check preference"),
        ("updater_interval_months : bpy.props.IntProperty", "updater month preference"),
        ("updater_interval_days : bpy.props.IntProperty", "updater day preference"),
        ("updater_interval_hours : bpy.props.IntProperty", "updater hour preference"),
        ("updater_interval_minutes : bpy.props.IntProperty", "updater minute preference"),
        ("addon_updater_ops.register(bl_info)", "updater registration"),
        ("addon_updater_ops.unregister()", "updater unregistration"),
    ):
        stripped = remove_line_containing_once(stripped, snippet, label=label)

    forbidden_markers = [
        marker for marker in NO_UPDATER_INIT_FORBIDDEN_MARKERS if marker in stripped
    ]
    if forbidden_markers:
        markers_text = ", ".join(repr(marker) for marker in forbidden_markers)
        raise RuntimeError(f"No-updater __init__.py still contains: {markers_text}")

    compile(stripped, "generated no-updater __init__.py", "exec")
    return stripped


def build_no_updater_manifest(manifest_text: str) -> str:
    lines = manifest_text.splitlines(keepends=True)
    updated_lines = [
        line for line in lines if re.match(r"\s*network\s*=", line) is None
    ]
    updated = "".join(updated_lines)
    if re.search(r"(?m)^\s*network\s*=", updated):
        raise RuntimeError("No-updater manifest still declares network permission")
    return updated


def build_no_updater_shared(shared_text: str) -> str:
    stripped = "".join(
        line
        for line in shared_text.splitlines(keepends=True)
        if "addon_updater" not in line and "auto_updater_status" not in line
    )
    compile(stripped, "generated no-updater secret_paint_shared.py", "exec")
    return stripped


def should_ignore_package_path(path: Path, package_root: Path) -> bool:
    relative = path.relative_to(package_root)
    lower_parts = tuple(part.lower() for part in relative.parts)
    if any(part in PACKAGE_IGNORE_DIRS for part in lower_parts[:-1]):
        return True
    if path.name.lower() in PACKAGE_IGNORE_FILENAMES:
        return True
    if path.suffix.lower() in PACKAGE_IGNORE_SUFFIXES:
        return True
    if any(pattern.search(path.name) for pattern in PACKAGE_IGNORE_NAME_PATTERNS):
        return True
    return False


def iter_package_files(package_root: Path, *, include_updater: bool) -> list[Path]:
    files = {
        path.relative_to(package_root)
        for path in package_root.rglob("*")
        if path.is_file() and not should_ignore_package_path(path, package_root)
    }

    required_files = list(REQUIRED_BASE_FILES)
    if include_updater:
        required_files.extend(Path(filename) for filename in sorted(UPDATER_FILENAMES))

    missing = [
        str(package_root / relative_path)
        for relative_path in required_files
        if not (package_root / relative_path).is_file()
    ]
    if missing:
        raise RuntimeError("Missing required package files:\n" + "\n".join(missing))

    files.update(required_files)
    if not include_updater:
        files = {
            relative_path
            for relative_path in files
            if relative_path.name.lower() not in UPDATER_FILENAMES
        }

    return sorted(files, key=lambda path: path.as_posix().lower())


def build_zip(
    zip_path: Path,
    package_root: Path,
    relative_files: list[Path],
    *,
    text_overrides: dict[Path, str] | None = None,
    dry_run: bool,
) -> None:
    text_overrides = text_overrides or {}
    archive_files = sorted(
        set(relative_files) | set(text_overrides),
        key=lambda path: path.as_posix().lower(),
    )

    if dry_run:
        log(f"[dry-run] create zip {zip_path} ({len(archive_files)} files)")
        return

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path in archive_files:
            archive_path = f"{ADDON_NAME}/{relative_path.as_posix()}"
            if relative_path in text_overrides:
                archive.writestr(archive_path, text_overrides[relative_path])
                continue

            source_path = package_root / relative_path
            archive.write(source_path, arcname=archive_path)


def read_archive_text(archive: zipfile.ZipFile, relative_path: Path) -> str:
    archive_path = f"{ADDON_NAME}/{relative_path.as_posix()}"
    return archive.read(archive_path).decode("utf-8")


def verify_no_updater_zip(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        forbidden_files = [
            name
            for name in names
            if PurePosixPath(name).name.lower() in UPDATER_FILENAMES
            or "secret paint_updater/" in name.lower()
        ]
        if forbidden_files:
            raise RuntimeError(
                "No-updater zip still contains updater files:\n"
                + "\n".join(sorted(forbidden_files))
            )

        marker_hits = []
        for name in names:
            if not (name.endswith(".py") or name.endswith("blender_manifest.toml")):
                continue
            text = archive.read(name).decode("utf-8")
            forbidden_markers = [
                marker for marker in NO_UPDATER_INIT_FORBIDDEN_MARKERS if marker in text
            ]
            if forbidden_markers:
                markers_text = ", ".join(repr(marker) for marker in forbidden_markers)
                marker_hits.append(f"{name}: {markers_text}")
        if marker_hits:
            raise RuntimeError(
                "No-updater zip still contains updater markers:\n"
                + "\n".join(sorted(marker_hits))
            )

        manifest_text = read_archive_text(archive, Path("blender_manifest.toml"))
        if re.search(r"(?m)^\s*network\s*=", manifest_text):
            raise RuntimeError("No-updater zip manifest still declares network permission")


def verify_website_updater_zip(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        required_names = {
            f"{ADDON_NAME}/{filename}" for filename in sorted(UPDATER_FILENAMES)
        }
        missing = sorted(required_names - names)
        if missing:
            raise RuntimeError(
                "Website updater zip is missing updater files:\n" + "\n".join(missing)
            )

        init_text = read_archive_text(archive, Path("__init__.py"))
        required_markers = (
            "addon_updater_ops.update_settings_ui",
            "addon_updater_ops.register(bl_info)",
            "addon_updater_ops.unregister()",
        )
        missing_markers = [marker for marker in required_markers if marker not in init_text]
        if missing_markers:
            markers_text = ", ".join(repr(marker) for marker in missing_markers)
            raise RuntimeError(f"Website updater zip init is missing: {markers_text}")


def main() -> int:
    args = parse_args()

    script_path = Path(__file__).resolve()
    addon_root = script_path.parent
    init_path = addon_root / "__init__.py"
    shared_path = addon_root / "secret_paint_shared.py"
    manifest_path = addon_root / "blender_manifest.toml"

    version_tuple = version_from_script_filename(script_path)
    version_text = ".".join(str(part) for part in version_tuple)
    log(f"Package version from script filename: {version_text}")

    updated_init = update_init_version(init_path, version_tuple, dry_run=args.dry_run)
    updated_manifest = update_manifest_version(manifest_path, version_tuple, dry_run=args.dry_run)

    no_updater_init = build_no_updater_init(updated_init)
    no_updater_manifest = build_no_updater_manifest(updated_manifest)
    no_updater_shared = build_no_updater_shared(read_text(shared_path))

    no_updater_files = iter_package_files(addon_root, include_updater=False)
    website_updater_files = iter_package_files(addon_root, include_updater=True)
    if not no_updater_files or not website_updater_files:
        raise RuntimeError(f"No package files found in {addon_root}")

    versions_root = addon_root / VERSIONS_DIRNAME
    website_versions_root = versions_root / WEBSITE_UPDATER_DIRNAME
    no_updater_zip_path = versions_root / f"{ADDON_NAME} {version_text}.zip"
    website_updater_zip_path = website_versions_root / f"{ADDON_NAME} {version_text}.zip"

    build_zip(
        no_updater_zip_path,
        addon_root,
        no_updater_files,
        text_overrides={
            Path("__init__.py"): no_updater_init,
            Path("blender_manifest.toml"): no_updater_manifest,
            Path("secret_paint_shared.py"): no_updater_shared,
        },
        dry_run=args.dry_run,
    )
    build_zip(
        website_updater_zip_path,
        addon_root,
        website_updater_files,
        text_overrides={
            Path("__init__.py"): updated_init,
            Path("blender_manifest.toml"): updated_manifest,
        },
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        verify_no_updater_zip(no_updater_zip_path)
        verify_website_updater_zip(website_updater_zip_path)

    log(f"Prepared Secret Paint {version_text}")
    log(f"No-updater package file count: {len(no_updater_files)}")
    log(f"Website updater package file count: {len(website_updater_files)}")
    log(f"No-updater zip output: {no_updater_zip_path}")
    log(f"Website updater zip output: {website_updater_zip_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
