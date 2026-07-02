from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


ADDON_NAME = "Secret Paint"
DEFAULT_GITHUB_REPO = "orencloud/Secret-Paint"
WEBSITE_ZIP_DIR = Path("VERSIONS") / "Website vers with git updater"
REQUIRED_RELEASE_FILES = (
    "__init__.py",
    "addon_updater.py",
    "addon_updater_ops.py",
    "blender_manifest.toml",
    "secret_paint_shared.py",
    "secret_paint_world_paint.py",
)
VERSION_RE = re.compile(r"(?<!\d)(\d+(?:(?:\s*,\s*|\.)\d+)+)(?!\d)")
MANIFEST_VERSION_RE = re.compile(r'(?m)^\s*version\s*=\s*"([^"]+)"')


@dataclass(frozen=True)
class VersionedZip:
    path: Path
    version: tuple[int, ...]
    version_text: str


class ReleaseError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=(
            "Publish the latest Secret Paint website-updater zip to GitHub "
            "and create a release with an empty body."
        )
    )
    parser.add_argument(
        "--versions-dir",
        type=Path,
        default=script_root / WEBSITE_ZIP_DIR,
        help="Folder containing the website-updater Secret Paint zip files.",
    )
    parser.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        help="GitHub repo in owner/name form.",
    )
    parser.add_argument(
        "--remote-url",
        default=None,
        help="Git remote URL. Defaults to https://github.com/<github-repo>.git.",
    )
    parser.add_argument(
        "--branch",
        default=None,
        help="Branch to push. Defaults to the cloned repo's current branch.",
    )
    parser.add_argument(
        "--pick",
        choices=("version", "mtime"),
        default="version",
        help="How to choose the latest zip.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Optional existing parent folder for the temporary clone.",
    )
    parser.add_argument(
        "--keep-work-dir",
        action="store_true",
        help="Keep the temporary clone after the script finishes.",
    )
    parser.add_argument(
        "--git-user-name",
        default=None,
        help="Local git author name for the release commit.",
    )
    parser.add_argument(
        "--git-user-email",
        default=None,
        help="Local git author email for the release commit.",
    )
    parser.add_argument(
        "--skip-release",
        action="store_true",
        help="Push the commit and tag but do not create the GitHub release.",
    )
    parser.add_argument(
        "--release-only",
        action="store_true",
        help="Create the GitHub release for the selected zip version without pushing files or tags.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selected archive and planned git/GitHub actions.",
    )
    return parser.parse_args()


def log(message: str) -> None:
    print(message, flush=True)


def version_tuple_from_text(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text))


def normalize_version_text(version: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def parse_version_from_name(path: Path) -> VersionedZip | None:
    match = VERSION_RE.search(path.stem)
    if match is None:
        return None
    version = version_tuple_from_text(match.group(1))
    if not version:
        return None
    return VersionedZip(path=path, version=version, version_text=normalize_version_text(version))


def find_latest_zip(versions_dir: Path, pick: str) -> VersionedZip:
    if not versions_dir.is_dir():
        raise ReleaseError(f"Versions folder does not exist: {versions_dir}")

    candidates = []
    for zip_path in versions_dir.glob("*.zip"):
        versioned = parse_version_from_name(zip_path)
        if versioned is not None:
            candidates.append(versioned)

    if not candidates:
        raise ReleaseError(f"No versioned .zip files found in {versions_dir}")

    if pick == "mtime":
        return max(candidates, key=lambda item: (item.path.stat().st_mtime, item.version))
    return max(candidates, key=lambda item: (item.version, item.path.stat().st_mtime))


def archive_top_folder(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as archive:
        top_folders = {
            PurePosixPath(info.filename).parts[0]
            for info in archive.infolist()
            if PurePosixPath(info.filename).parts
        }
    if len(top_folders) != 1:
        raise ReleaseError(
            f"Expected exactly one top-level folder in {zip_path.name}, found: "
            + ", ".join(sorted(top_folders))
        )
    return next(iter(top_folders))


def read_archive_text(zip_path: Path, top_folder: str, relative_path: str) -> str:
    archive_name = f"{top_folder}/{relative_path}"
    with zipfile.ZipFile(zip_path) as archive:
        try:
            return archive.read(archive_name).decode("utf-8")
        except KeyError as exc:
            raise ReleaseError(f"Archive is missing {archive_name}") from exc


def validate_archive(zip_info: VersionedZip) -> str:
    top_folder = archive_top_folder(zip_info.path)
    if top_folder != ADDON_NAME:
        raise ReleaseError(
            f"Expected archive top folder '{ADDON_NAME}', found '{top_folder}'"
        )

    manifest_text = read_archive_text(zip_info.path, top_folder, "blender_manifest.toml")
    manifest_match = MANIFEST_VERSION_RE.search(manifest_text)
    if manifest_match is None:
        raise ReleaseError("Archive manifest does not contain a version field")

    manifest_version = normalize_version_text(version_tuple_from_text(manifest_match.group(1)))
    if manifest_version != zip_info.version_text:
        raise ReleaseError(
            f"Zip filename version is {zip_info.version_text}, "
            f"but blender_manifest.toml says {manifest_version}"
        )

    return top_folder


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    capture: bool = False,
) -> str:
    command_text = " ".join(args)
    if dry_run:
        log(f"[dry-run] {command_text}")
        return ""

    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        output = "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part and part.strip()
        )
        raise ReleaseError(f"Command failed: {command_text}\n{output}")

    if capture:
        return completed.stdout.strip()
    if completed.stdout.strip():
        log(completed.stdout.strip())
    if completed.stderr.strip():
        log(completed.stderr.strip())
    return completed.stdout.strip()


def default_remote_url(github_repo: str) -> str:
    return f"https://github.com/{github_repo}.git"


def clone_or_init(remote_url: str, clone_path: Path, dry_run: bool) -> None:
    try:
        run(["git", "clone", remote_url, str(clone_path)], dry_run=dry_run)
    except ReleaseError:
        if dry_run:
            return
        clone_path.mkdir(parents=True, exist_ok=True)
        run(["git", "init"], cwd=clone_path)
        run(["git", "remote", "add", "origin", remote_url], cwd=clone_path)


def current_branch(repo_path: Path, requested_branch: str | None, dry_run: bool) -> str:
    if requested_branch:
        return requested_branch
    branch = run(["git", "branch", "--show-current"], cwd=repo_path, dry_run=dry_run, capture=True)
    if branch:
        return branch
    return "master"


def configured_value(repo_path: Path, key: str, dry_run: bool) -> str:
    if dry_run:
        return ""
    completed = subprocess.run(
        ["git", "config", "--get", key],
        cwd=str(repo_path),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def configure_git_identity(
    repo_path: Path,
    github_repo: str,
    user_name: str | None,
    user_email: str | None,
    dry_run: bool,
) -> None:
    owner = github_repo.split("/", 1)[0]
    resolved_name = user_name or os.environ.get("GIT_AUTHOR_NAME") or owner
    resolved_email = (
        user_email
        or os.environ.get("GIT_AUTHOR_EMAIL")
        or f"{owner}@users.noreply.github.com"
    )

    if not configured_value(repo_path, "user.name", dry_run):
        run(["git", "config", "user.name", resolved_name], cwd=repo_path, dry_run=dry_run)
    if not configured_value(repo_path, "user.email", dry_run):
        run(["git", "config", "user.email", resolved_email], cwd=repo_path, dry_run=dry_run)


def clear_checkout(repo_path: Path) -> None:
    resolved_repo = repo_path.resolve()
    if not (repo_path / ".git").is_dir():
        raise ReleaseError(f"Refusing to clear non-git folder: {repo_path}")

    for child in repo_path.iterdir():
        if child.name == ".git":
            continue
        resolved_child = child.resolve()
        if resolved_repo not in resolved_child.parents:
            raise ReleaseError(f"Refusing to remove path outside repo: {child}")
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def extract_archive_contents(zip_path: Path, top_folder: str, repo_path: Path) -> None:
    resolved_repo = repo_path.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            archive_path = PurePosixPath(info.filename)
            if len(archive_path.parts) < 2 or archive_path.parts[0] != top_folder:
                continue
            relative_parts = archive_path.parts[1:]
            if not relative_parts:
                continue

            destination = repo_path.joinpath(*relative_parts)
            resolved_destination = destination.resolve()
            if resolved_repo != resolved_destination and resolved_repo not in resolved_destination.parents:
                raise ReleaseError(f"Archive path escapes repo: {info.filename}")

            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)


def validate_extracted_repo(repo_path: Path) -> None:
    missing = [name for name in REQUIRED_RELEASE_FILES if not (repo_path / name).is_file()]
    if missing:
        raise ReleaseError("Extracted release is missing: " + ", ".join(missing))


def has_changes(repo_path: Path, dry_run: bool) -> bool:
    if dry_run:
        return True
    status = run(["git", "status", "--porcelain"], cwd=repo_path, capture=True)
    return bool(status)


def tag_exists(repo_path: Path, tag: str, dry_run: bool) -> bool:
    if dry_run:
        return False
    completed = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=str(repo_path),
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def commit_tag_and_push(repo_path: Path, branch: str, tag: str, dry_run: bool) -> None:
    if tag_exists(repo_path, tag, dry_run):
        raise ReleaseError(f"Local tag already exists: {tag}")

    run(["git", "add", "-A"], cwd=repo_path, dry_run=dry_run)
    if has_changes(repo_path, dry_run):
        run(["git", "commit", "-m", f"Release {tag}"], cwd=repo_path, dry_run=dry_run)
    else:
        log("No file changes in release repo; tagging current HEAD.")

    run(["git", "tag", tag], cwd=repo_path, dry_run=dry_run)
    run(["git", "push", "origin", f"HEAD:{branch}"], cwd=repo_path, dry_run=dry_run)
    run(["git", "push", "origin", tag], cwd=repo_path, dry_run=dry_run)


def gh_available() -> bool:
    return shutil.which("gh") is not None


def create_release_with_gh(github_repo: str, tag: str, dry_run: bool) -> bool:
    if not gh_available():
        return False
    run(
        [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            github_repo,
            "--title",
            tag,
            "--notes",
            "",
            "--verify-tag",
        ],
        dry_run=dry_run,
    )
    return True


def github_token_from_env() -> str | None:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def github_token_from_git_credential() -> str | None:
    credential_input = "protocol=https\nhost=github.com\n\n"
    completed = subprocess.run(
        ["git", "credential", "fill"],
        input=credential_input,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None

    values = {}
    for line in completed.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values.get("password")


def github_token() -> str | None:
    return github_token_from_env() or github_token_from_git_credential()


def create_release_with_api(github_repo: str, tag: str, dry_run: bool) -> None:
    if dry_run:
        log(f"[dry-run] POST https://api.github.com/repos/{github_repo}/releases")
        log(f"[dry-run] Release title/body: {tag!r} / ''")
        return

    token = github_token()
    if not token:
        raise ReleaseError(
            "Could not create the GitHub release: install/authenticate GitHub CLI "
            "or set GH_TOKEN/GITHUB_TOKEN. Git credentials were not available to the API fallback."
        )

    payload = json.dumps(
        {
            "tag_name": tag,
            "name": tag,
            "body": "",
            "draft": False,
            "prerelease": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{github_repo}/releases",
        data=payload,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Secret-Paint-release-script",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            if response.status not in (200, 201):
                raise ReleaseError(f"GitHub release API returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ReleaseError(f"GitHub release API failed: HTTP {exc.code}\n{detail}") from exc


def create_release(github_repo: str, tag: str, dry_run: bool) -> None:
    if create_release_with_gh(github_repo, tag, dry_run):
        return
    create_release_with_api(github_repo, tag, dry_run)


def make_temp_parent(args: argparse.Namespace) -> tuple[Path, bool]:
    if args.work_dir is not None:
        args.work_dir.mkdir(parents=True, exist_ok=True)
        return args.work_dir.resolve(), False
    temp_parent = Path(tempfile.mkdtemp(prefix="secret-paint-release-")).resolve()
    return temp_parent, True


def main() -> int:
    args = parse_args()
    selected_zip = find_latest_zip(args.versions_dir.resolve(), args.pick)
    top_folder = validate_archive(selected_zip)
    remote_url = args.remote_url or default_remote_url(args.github_repo)
    tag = selected_zip.version_text

    log(f"Selected archive: {selected_zip.path}")
    log(f"Release tag: {tag}")
    log(f"GitHub repo: {args.github_repo}")

    if args.dry_run:
        log(f"[dry-run] Remote URL: {remote_url}")

    if args.release_only:
        if args.skip_release:
            raise ReleaseError("--release-only cannot be combined with --skip-release")
        create_release(args.github_repo, tag, args.dry_run)
        log(f"Created GitHub release {tag}")
        return 0

    temp_parent, remove_temp_parent = make_temp_parent(args)
    clone_path = temp_parent / "Secret-Paint-release"

    try:
        if clone_path.exists() and any(clone_path.iterdir()):
            raise ReleaseError(f"Release work folder is not empty: {clone_path}")

        clone_or_init(remote_url, clone_path, args.dry_run)
        branch = current_branch(clone_path, args.branch, args.dry_run)
        log(f"Publishing branch: {branch}")
        configure_git_identity(
            clone_path,
            args.github_repo,
            args.git_user_name,
            args.git_user_email,
            args.dry_run,
        )

        if not args.dry_run:
            clear_checkout(clone_path)
            extract_archive_contents(selected_zip.path, top_folder, clone_path)
            validate_extracted_repo(clone_path)

        commit_tag_and_push(clone_path, branch, tag, args.dry_run)

        if args.skip_release:
            log("Skipped GitHub release creation.")
        else:
            create_release(args.github_repo, tag, args.dry_run)

        log(f"Published Secret Paint {tag}")
        return 0
    finally:
        if remove_temp_parent and not args.keep_work_dir and temp_parent.exists():
            shutil.rmtree(temp_parent)
        elif args.keep_work_dir:
            log(f"Kept release work folder: {clone_path}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
