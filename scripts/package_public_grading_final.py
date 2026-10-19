"""Package an already reviewed public-grading stage without changing that stage.

This is a standalone, standard-library-only finishing tool. It neither builds the
report nor performs live acceptance tests, visual review, Git operations, or CI.
Its source identity comes from SOURCE_MANIFEST.json, never the current Git HEAD.

Required review record: evidence/FINAL_AUDIT.json must contain status=PASS,
pdf_sha256, reviewed_at_utc, page_count, pages_reviewed,
placed_images_reviewed, raw_screenshots_verified, and visual_review with a PASS
status and a nonempty reviewer. The reviewer must create that record after
actually inspecting the PDF whose digest it records; this program cannot prove
the truth of a review declaration and never creates one.

Usage:
    python scripts/package_public_grading_final.py \
        --stage /absolute/submission/stage --output /absolute/releases \
        --name 미션18_2팀_이형기 --verify-only

Omit --verify-only to create NAME.zip, NAME_최종보고서.pdf, and SHA256SUMS.txt.
The ZIP contains 미션18/NAME/ and a MANIFEST_SHA256.json covering every file
except itself. The input stage stays read-only. Existing output names cause an
error, including partial outputs from an earlier attempt; nothing is overwritten
or retried. --verify-only also verifies these outputs if any already exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import posixpath
import re
import stat
import struct
import sys
import tempfile
import zipfile
import zlib
from collections import Counter
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

MANIFEST = "MANIFEST_SHA256.json"
PDF = "보고서.pdf"
AUDIT = "evidence/FINAL_AUDIT.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
FORBIDDEN_PARTS = {
    ".git",
    ".venv",
    "venv",
    ".local",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "cache",
    "caches",
    "node_modules",
    "models",
    "model_weights",
    "checkpoints",
    "secrets",
    ".secrets",
    ".aws",
    ".ssh",
    ".ds_store",
    "__macosx",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".db-wal",
    ".db-shm",
    ".sqlite-wal",
    ".sqlite-shm",
    ".sqlite3-wal",
    ".sqlite3-shm",
    ".dump",
    ".safetensors",
    ".onnx",
    ".pt",
    ".pth",
    ".ckpt",
    ".h5",
    ".hdf5",
    ".bin",
    ".pkl",
    ".pickle",
    ".joblib",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".bz2",
    ".xz",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".log",
}
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(rb"\b(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,})\b"),
    re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
)
RESERVED_DERIVED = {"SOURCE_MANIFEST.json", MANIFEST, PDF}
PACKAGING_HELPERS = {
    "scripts/package_public_grading_final.py",
    "tests/test_public_grading_package.py",
}


class PackageError(ValueError):
    """A validation or publication gate failed; do not retry automatically."""


def require(condition: bool, message: str) -> None:
    # Deliberately not an assert: all gates must survive python -O.
    if not condition:
        raise PackageError(message)


def mapping(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), "INVALID_OBJECT: " + label)
    return value


def sequence(value: Any, label: str, *, nonempty: bool = True) -> list[Any]:
    require(isinstance(value, list), "INVALID_LIST: " + label)
    require(not nonempty or bool(value), "EMPTY_LIST: " + label)
    return value


def positive_int(value: Any, label: str, *, minimum: int = 1) -> int:
    require(type(value) is int and value >= minimum, "INVALID_COUNT: " + label)
    return value


def digest(value: Any, label: str, *, git: bool = False) -> str:
    pattern = r"(?:[0-9a-f]{40}|[0-9a-f]{64})" if git else r"[0-9a-f]{64}"
    require(
        isinstance(value, str) and re.fullmatch(pattern, value) is not None, "INVALID_SHA: " + label
    )
    return value


def safe_relative_path(value: Any) -> str:
    require(isinstance(value, str) and bool(value), "UNSAFE_PATH: missing path")
    require(
        not any(ord(char) < 32 or ord(char) == 127 for char in value),
        "UNSAFE_PATH: control character",
    )
    require("\\" not in value and ":" not in value, "UNSAFE_PATH: " + value)
    path = PurePosixPath(value)
    require(
        bool(path.parts)
        and not path.is_absolute()
        and path.as_posix() == value
        and all(part not in {".", "..", ""} for part in path.parts),
        "UNSAFE_PATH: " + value,
    )
    return value


def permitted_path(relative: str) -> None:
    parts = PurePosixPath(safe_relative_path(relative)).parts
    for part in parts:
        lower = part.casefold()
        require(lower not in FORBIDDEN_PARTS, "FORBIDDEN_PAYLOAD: " + relative)
        require(
            not (lower == ".env" or lower.startswith(".env.")) or lower == ".env.example",
            "FORBIDDEN_ENV: " + relative,
        )
        require(not lower.startswith("._"), "FORBIDDEN_METADATA: " + relative)
    name = parts[-1].casefold()
    require(PurePosixPath(name).suffix not in FORBIDDEN_SUFFIXES, "FORBIDDEN_PAYLOAD: " + relative)
    require(
        not re.fullmatch(r"(?:secrets?|credentials?|tokens?)(?:\..+)?", name),
        "FORBIDDEN_CREDENTIAL_FILE: " + relative,
    )


def absolute_path(value: str, *, must_exist: bool) -> Path:
    path = Path(value)
    require(path.is_absolute(), "ABSOLUTE_PATH_REQUIRED: " + value)
    require(not path.is_symlink(), "SYMLINK_PATH: " + value)
    try:
        return path.resolve(strict=must_exist)
    except OSError as exc:
        raise PackageError("PATH_UNAVAILABLE: " + value) from exc


def file_bytes(path: Path) -> bytes:
    """Read a stable regular file, refusing a symlink or an in-flight write."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), "NOT_REGULAR_FILE: " + str(path))
        data = stream.read()
        after = os.fstat(stream.fileno())

    def signature(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)

    require(
        signature(before) == signature(after) and len(data) == after.st_size,
        "FILE_CHANGED_DURING_READ: " + str(path),
    )
    return data


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect_files(stage: Path) -> dict[str, dict[str, Any]]:
    require(stage.is_dir() and not stage.is_symlink(), "STAGE_DIRECTORY_REQUIRED")
    files: dict[str, dict[str, Any]] = {}
    names: set[str] = set()
    for directory, dirs, filenames in os.walk(stage, followlinks=False):
        dirs.sort()
        filenames.sort()
        for name in dirs + filenames:
            path = Path(directory) / name
            relative = path.relative_to(stage).as_posix()
            permitted_path(relative)
            mode = path.lstat().st_mode
            require(not stat.S_ISLNK(mode), "SYMLINK_PAYLOAD: " + relative)
            require(stat.S_ISREG(mode) or stat.S_ISDIR(mode), "SPECIAL_FILE_PAYLOAD: " + relative)
            require(relative.casefold() not in names, "AMBIGUOUS_PATH: " + relative)
            names.add(relative.casefold())
            if stat.S_ISREG(mode):
                payload = file_bytes(path)
                if path.suffix.casefold() not in {".png", ".pdf"}:
                    require(
                        not any(pattern.search(payload) for pattern in SECRET_PATTERNS),
                        "RECOGNIZABLE_SECRET: " + relative,
                    )
                files[relative] = {
                    "path": relative,
                    "bytes": len(payload),
                    "sha256": sha256(payload),
                }
    require(bool(files), "EMPTY_STAGE")
    return dict(sorted(files.items()))


def read_verified(stage: Path, files: dict[str, dict[str, Any]], relative: str) -> bytes:
    relative = safe_relative_path(relative)
    require(relative in files, "MISSING_FILE: " + relative)
    data = file_bytes(stage / relative)
    entry = files[relative]
    require(
        len(data) == entry["bytes"] and sha256(data) == entry["sha256"],
        "HASH_MISMATCH_OR_CHANGED_FILE: " + relative,
    )
    return data


def unique_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY: " + key)
        result[key] = value
    return result


def parse_json(data: bytes, label: str) -> Any:
    try:
        return json.loads(
            data,
            object_pairs_hook=unique_json_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                PackageError("NONFINITE_JSON_VALUE: " + value)
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PackageError("INVALID_JSON: " + label) from exc


def json_file(stage: Path, files: dict[str, dict[str, Any]], relative: str) -> Any:
    return parse_json(read_verified(stage, files, relative), relative)


def verify_sources(source: dict[str, Any], files: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Validate original bytes; documentation changes must be declared derived."""
    digest(source.get("source_sha"), "SOURCE_MANIFEST.source_sha", git=True)
    derived = sequence(source.get("derived_files"), "derived_files", nonempty=False)
    exact: set[str] = set(RESERVED_DERIVED)
    prefixes: list[str] = []
    for item in derived:
        require(isinstance(item, str), "INVALID_DERIVED_PATH")
        if item.endswith("/"):
            safe_relative_path(item[:-1])
            require(item in {"report/", "evidence/"}, "RUNTIME_DERIVATION_FORBIDDEN: " + item)
            prefixes.append(item)
        else:
            safe_relative_path(item)
            require(
                item in {".env.example", "README.md", "INDEX.md", PDF} | PACKAGING_HELPERS
                or (item.startswith("docs/") and item.endswith(".md"))
                or item.startswith(("report/", "evidence/")),
                "RUNTIME_DERIVATION_FORBIDDEN: " + item,
            )
            exact.add(item)
        exists = (
            any(path.startswith(item) for path in files) if item.endswith("/") else item in files
        )
        require(exists, "MISSING_DERIVED_FILE: " + item)

    def is_derived(path: str) -> bool:
        return path in exact or any(path.startswith(prefix) for prefix in prefixes)

    sources: set[str] = set()
    for value in sequence(source.get("source_files"), "source_files"):
        row = mapping(value, "source_files entry")
        path = safe_relative_path(row.get("path"))
        require(path not in sources, "DUPLICATE_SOURCE_PATH: " + path)
        sources.add(path)
        require(path in files, "MISSING_SOURCE_FILE: " + path)
        original_sha = digest(row.get("source_sha256"), path)
        original_size = positive_int(row.get("bytes"), path, minimum=0)
        if not is_derived(path):
            require(
                files[path]["sha256"] == original_sha and files[path]["bytes"] == original_size,
                "SOURCE_HASH_MISMATCH: " + path,
            )
    kinds = {}
    for path in files:
        require(path in sources or is_derived(path), "UNDECLARED_PAYLOAD: " + path)
        kinds[path] = (
            "packaging_helper"
            if path in PACKAGING_HELPERS and is_derived(path)
            else ("derived" if is_derived(path) else "source_preserved")
        )
    return kinds


def verify_acceptance(
    acceptance: dict[str, Any],
    validation: dict[str, Any],
    deployment: dict[str, Any],
    source_sha: str,
) -> None:
    require(acceptance.get("status") == "PASS_SINGLE_SESSION_VERIFIED", "ACCEPTANCE_NOT_PASS")
    require(acceptance.get("errors") == [], "ACCEPTANCE_ERRORS")
    require(acceptance.get("browser_js_errors", []) == [], "BROWSER_JS_ERRORS")
    require(acceptance.get("source_main") == source_sha, "ACCEPTANCE_SOURCE_MISMATCH")
    checks = mapping(acceptance.get("checks"), "acceptance.checks")
    require(
        bool(checks) and all(value is True for value in checks.values()),
        "ACCEPTANCE_CHECKS_NOT_ALL_TRUE",
    )
    for key in (
        "baseline_original_rows_byte_equivalent",
        "created_movie_persisted",
        "new_review_saved_with_real_inference",
        "review_deletion_persisted",
        "owned_movie_deleted",
        "anonymous_public_demo_enabled",
    ):
        require(checks.get(key) is True, "REQUIRED_ACCEPTANCE_CHECK_MISSING: " + key)
    require(validation.get("status") == "PASS", "VALIDATION_NOT_PASS")
    require(validation.get("runtime_source_sha") == source_sha, "VALIDATION_SOURCE_MISMATCH")
    require(
        validation.get("cloud_e2e_checks") == len(checks)
        and validation.get("cloud_e2e_passed") == len(checks),
        "VALIDATION_ACCEPTANCE_COUNT_MISMATCH",
    )
    require(validation.get("contract_check") == "G1_CONTRACT_PASS", "CONTRACT_CHECK_NOT_PASS")
    for key in ("original_source_tests", "portable_submission_tests"):
        result = mapping(validation.get(key), key)
        positive_int(result.get("passed"), key + ".passed")
        require(
            result.get("failed", 0) == 0 and result.get("errors", 0) == 0, "TEST_FAILURES: " + key
        )
        if result.get("skipped", 0):
            require(
                isinstance(result.get("skip_reason"), str) and result["skip_reason"].strip(),
                "UNDOCUMENTED_TEST_SKIP: " + key,
            )
    require(deployment.get("runtime_source_sha") == source_sha, "DEPLOYMENT_SOURCE_MISMATCH")
    require(deployment.get("public_write_policy") == "public_demo", "PUBLIC_POLICY_MISMATCH")
    live = mapping(acceptance.get("deployment"), "acceptance.deployment")
    require(live.get("write_policy") == "public_demo", "LIVE_PUBLIC_POLICY_MISMATCH")
    render_sha = digest(deployment.get("render_deployed_sha"), "render_deployed_sha", git=True)
    require(live.get("revision") == render_sha, "RENDER_REVISION_MISMATCH")
    readiness = mapping(live.get("readiness"), "readiness")
    require(
        all(readiness.get(key) == "ready" for key in ("status", "database", "model")),
        "READINESS_NOT_VERIFIED",
    )
    baseline = mapping(acceptance.get("baseline"), "baseline")
    after = mapping(acceptance.get("after"), "after")
    recorded = mapping(deployment.get("baseline_and_final"), "baseline_and_final")
    for entity, plural in (("movie", "movies"), ("review", "reviews")):
        count = positive_int(baseline.get(entity + "_count"), entity + " count")
        original = digest(baseline.get(entity + "_sha256"), entity + " baseline SHA")
        require(
            after.get(entity + "_count") == count == recorded.get(plural),
            "ORIGINAL_DATA_COUNT_MISMATCH: " + entity,
        )
        require(
            after.get(entity + "_sha256")
            == original
            == recorded.get("original_" + entity + "_sha256")
            == recorded.get("final_" + entity + "_sha256"),
            "ORIGINAL_DATA_HASH_MISMATCH: " + entity,
        )
    films = sequence(acceptance.get("required_three_films"), "required_three_films")
    require(len(films) >= 3, "THREE_FILMS_REQUIRED")
    identities = set()
    for value in films:
        film = mapping(value, "required film")
        identities.add(positive_int(film.get("movie_id"), "required film ID"))
        positive_int(film.get("review_count"), "required film reviews", minimum=10)
        require(isinstance(film.get("title"), str) and film["title"].strip(), "MISSING_FILM_TITLE")
    require(len(identities) == len(films), "DUPLICATE_REQUIRED_FILM")


def verify_png(data: bytes, path: str) -> tuple[int, int]:
    """Validate PNG framing and every chunk CRC; visual QA remains the reviewer's job."""
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), "INVALID_PNG_SIGNATURE: " + path)
    offset, dimensions, saw_data, saw_end = 8, None, False, False
    while offset < len(data):
        require(offset + 12 <= len(data), "TRUNCATED_PNG: " + path)
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        end = offset + length + 12
        require(end <= len(data), "TRUNCATED_PNG_CHUNK: " + path)
        kind = data[offset + 4 : offset + 8]
        content = data[offset + 8 : end - 4]
        crc = struct.unpack(">I", data[end - 4 : end])[0]
        require(zlib.crc32(kind + content) & 0xFFFFFFFF == crc, "PNG_CRC_MISMATCH: " + path)
        if dimensions is None:
            require(kind == b"IHDR" and length == 13, "INVALID_PNG_IHDR: " + path)
            dimensions = struct.unpack(">II", content[:8])
            require(all(value > 0 for value in dimensions), "INVALID_PNG_DIMENSIONS: " + path)
        elif kind == b"IHDR":
            raise PackageError("DUPLICATE_PNG_IHDR: " + path)
        saw_data = saw_data or kind == b"IDAT"
        offset = end
        if kind == b"IEND":
            require(length == 0 and offset == len(data), "INVALID_PNG_END: " + path)
            saw_end = True
            break
    require(saw_data and saw_end and dimensions is not None, "INCOMPLETE_PNG: " + path)
    return dimensions


class ReportImages(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pages: list[int] = []
        self.images: list[tuple[int, str]] = []
        self.current_page: int | None = None
        self.sections: list[int | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "section":
            self.sections.append(self.current_page)
            if "page" in (attributes.get("class") or "").split():
                match = re.fullmatch(r"p([1-9][0-9]*)", attributes.get("id") or "")
                require(match is not None, "REPORT_PAGE_ID_INVALID")
                self.current_page = int(match.group(1))
                self.pages.append(self.current_page)
        if tag == "img":
            require(self.current_page is not None, "REPORT_IMAGE_OUTSIDE_PAGE")
            url = urlsplit(attributes.get("src") or "")
            require(
                not (url.scheme or url.netloc or url.query or url.fragment)
                and bool(url.path)
                and not url.path.startswith("/"),
                "REPORT_IMAGE_NOT_LOCAL",
            )
            path = safe_relative_path(
                posixpath.normpath(posixpath.join("report", unquote(url.path)))
            )
            self.images.append((self.current_page, path))

    def handle_endtag(self, tag: str) -> None:
        if tag == "section":
            require(bool(self.sections), "UNBALANCED_REPORT_SECTIONS")
            self.current_page = self.sections.pop()


def verify_images(
    stage: Path,
    files: dict[str, dict[str, Any]],
    acceptance: dict[str, Any],
    report: dict[str, Any],
    image_use: list[Any],
    openapi: dict[str, Any],
    contract: dict[str, Any],
) -> int:
    dimensions = {
        path: verify_png(read_verified(stage, files, path), path)
        for path in files
        if path.casefold().endswith(".png")
    }
    screenshots: dict[str, dict[str, Any]] = {}
    for value in sequence(acceptance.get("screenshots"), "screenshots"):
        row = mapping(value, "screenshot")
        name = safe_relative_path(row.get("file"))
        require("/" not in name and name.endswith(".png"), "SCREENSHOT_BASENAME_REQUIRED")
        require(name not in screenshots, "DUPLICATE_SCREENSHOT: " + name)
        path = "evidence/screenshots/" + name
        require(path in dimensions, "MISSING_SCREENSHOT: " + name)
        require(
            files[path]["sha256"] == digest(row.get("sha256"), name)
            and files[path]["bytes"] == positive_int(row.get("bytes"), name),
            "SCREENSHOT_HASH_MISMATCH: " + name,
        )
        screenshots[name] = row
    raw_files = {
        path.removeprefix("evidence/screenshots/")
        for path in files
        if path.startswith("evidence/screenshots/")
    }
    require(raw_files == set(screenshots), "UNLISTED_OR_MISSING_RAW_SCREENSHOT")

    pages = positive_int(report.get("page_count"), "report.page_count")
    require(
        positive_int(report.get("image_count"), "report.image_count") == len(image_use),
        "REPORT_IMAGE_COUNT_MISMATCH",
    )
    placements: list[tuple[int, str]] = []
    displayed_sources: set[str] = set()
    for value in image_use:
        row = mapping(value, "image placement")
        name = safe_relative_path(row.get("source_file"))
        require(name in screenshots, "IMAGE_SOURCE_NOT_IN_ACCEPTANCE: " + name)
        original = screenshots[name]
        path = safe_relative_path(row.get("display_file"))
        require(
            path.startswith("report/assets/") or path == "evidence/screenshots/" + name,
            "IMAGE_DISPLAY_PATH_INVALID: " + path,
        )
        require(path in dimensions, "MISSING_PLACED_IMAGE: " + path)
        require(
            row.get("source_sha256") == original["sha256"], "IMAGE_SOURCE_HASH_MISMATCH: " + name
        )
        require(
            files[path]["sha256"] == digest(row.get("display_sha256"), path),
            "DISPLAY_IMAGE_HASH_MISMATCH: " + path,
        )
        for key in ("role", "api_match", "resource_ids"):
            require(
                key in row and key in original and row[key] == original[key],
                "IMAGE_IDENTITY_MISMATCH: " + name + ":" + key,
            )
        require(
            isinstance(row.get("caption"), str) and row["caption"].strip(), "MISSING_IMAGE_CAPTION"
        )
        page = positive_int(row.get("page"), "image.page")
        require(page <= pages, "IMAGE_PAGE_OUT_OF_RANGE")
        if row.get("crop") is not None:
            crop = mapping(row["crop"], "crop")
            values = [crop.get(key) for key in ("x", "y", "width", "height")]
            require(
                all(type(value) in (int, float) and math.isfinite(value) for value in values),
                "INVALID_CROP: " + name,
            )
            x, y, width, height = values
            raw_width, raw_height = dimensions["evidence/screenshots/" + name]
            require(
                x >= 0
                and y >= 0
                and width > 0
                and height > 0
                and x + width <= raw_width
                and y + height <= raw_height,
                "CROP_OUT_OF_BOUNDS: " + name,
            )
        placements.append((page, path))
        displayed_sources.add(name)
    assets = {path for path in files if path.startswith("report/assets/")}
    require(
        assets == {path for _, path in placements if path.startswith("report/assets/")},
        "UNLISTED_OR_MISSING_REPORT_ASSET",
    )
    parser = ReportImages()
    parser.feed(read_verified(stage, files, "report/report.html").decode("utf-8"))
    parser.close()
    require(
        not parser.sections and parser.pages == list(range(1, pages + 1)),
        "REPORT_PAGE_SEQUENCE_MISMATCH",
    )
    require(parser.images == placements, "HTML_IMAGE_MANIFEST_MISMATCH")

    live_operations = {}
    for path, methods in mapping(openapi.get("paths"), "openapi.paths").items():
        for method, operation in mapping(methods, "openapi path").items():
            if method in HTTP_METHODS:
                operation_id = mapping(operation, "openapi operation").get("operationId")
                require(isinstance(operation_id, str) and operation_id, "MISSING_OPERATION_ID")
                live_operations[(method.upper(), path)] = operation_id
    expected_operations = {
        (row["method"], row["path"])
        for row in sequence(contract.get("endpoints"), "contract.endpoints")
    }
    require(
        bool(live_operations) and set(live_operations) == expected_operations,
        "LIVE_OPENAPI_CONTRACT_MISMATCH",
    )
    captured = {}
    captured_files = set()
    for value in sequence(acceptance.get("swagger_operations"), "swagger_operations"):
        row = mapping(value, "swagger operation")
        key = (row.get("method"), row.get("path"))
        require(all(isinstance(part, str) for part in key), "INVALID_SWAGGER_OPERATION")
        require(key not in captured and key in live_operations, "SWAGGER_OPERATION_MISMATCH")
        require(row.get("operation_id") == live_operations[key], "SWAGGER_OPERATION_ID_MISMATCH")
        name = safe_relative_path(row.get("file"))
        require(
            name in screenshots and name in displayed_sources and name not in captured_files,
            "SWAGGER_IMAGE_MISSING_OR_DUPLICATE: " + name,
        )
        require(
            screenshots[name].get("role") == "api_documentation"
            and screenshots[name].get("api_match") == " ".join(key),
            "SWAGGER_IMAGE_IDENTITY_MISMATCH",
        )
        captured[key] = name
        captured_files.add(name)
    require(set(captured) == set(live_operations), "SWAGGER_COVERAGE_INCOMPLETE")
    return len(screenshots)


def verify_review(
    audit: dict[str, Any],
    report: dict[str, Any],
    layout: dict[str, Any],
    pdf: bytes,
    raw_count: int,
) -> None:
    require(audit.get("status") == "PASS", "FINAL_AUDIT_NOT_PASS")
    require(pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-1024:], "INVALID_PDF_FRAMING")
    actual_sha = sha256(pdf)
    require(
        audit.get("pdf_sha256") == actual_sha == report.get("pdf_sha256"),
        "AUDITED_PDF_HASH_MISMATCH",
    )
    pages = positive_int(report.get("page_count"), "page_count")
    require(
        audit.get("page_count") == pages == audit.get("pages_reviewed"), "ALL_PAGES_NOT_REVIEWED"
    )
    require(
        audit.get("placed_images_reviewed") == report.get("image_count"),
        "ALL_PLACED_IMAGES_NOT_REVIEWED",
    )
    require(audit.get("raw_screenshots_verified") == raw_count, "ALL_RAW_IMAGES_NOT_REVIEWED")
    review = mapping(audit.get("visual_review"), "visual_review")
    require(
        review.get("status") == "PASS"
        and isinstance(review.get("reviewer"), str)
        and bool(review["reviewer"].strip()),
        "VISUAL_REVIEW_NOT_PASS",
    )
    require(audit.get("errors", []) == [], "FINAL_AUDIT_HAS_ERRORS")
    try:
        reviewed_at = datetime.fromisoformat(
            audit.get("reviewed_at_utc", "").replace("Z", "+00:00")
        )
        require(reviewed_at.utcoffset() == timedelta(0), "AUDIT_UTC_TIMESTAMP_REQUIRED")
    except (TypeError, ValueError, AttributeError) as exc:
        raise PackageError("INVALID_AUDIT_TIMESTAMP") from exc
    require(
        layout.get("pages") == pages
        and layout.get("images_loaded") == report.get("image_count")
        and layout.get("overflows") == [],
        "REPORT_LAYOUT_NOT_PASS",
    )
    layouts = sequence(layout.get("layouts"), "layouts")
    require(len(layouts) == pages, "REPORT_LAYOUT_PAGE_COUNT_MISMATCH")
    for index, value in enumerate(layouts, 1):
        row = mapping(value, "layout")
        require(row.get("page") == index, "REPORT_LAYOUT_PAGE_SEQUENCE_MISMATCH")
        bottom, footer = row.get("contentBottom"), row.get("footerTop")
        require(
            all(
                type(number) in (int, float) and math.isfinite(number)
                for number in (bottom, footer)
            )
            and 0 <= bottom < footer,
            "REPORT_CONTENT_OVERLAPS_FOOTER",
        )


def verify_stage(stage: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any], bytes]:
    files = collect_files(stage)
    audit = mapping(json_file(stage, files, AUDIT), AUDIT)
    require(audit.get("status") == "PASS", "FINAL_AUDIT_NOT_PASS")
    source = mapping(json_file(stage, files, "SOURCE_MANIFEST.json"), "SOURCE_MANIFEST")
    kinds = verify_sources(source, files)
    source_sha = source["source_sha"]
    acceptance = mapping(
        json_file(stage, files, "evidence/public_grading_acceptance.json"), "acceptance"
    )
    deployment = mapping(json_file(stage, files, "evidence/DEPLOYMENT_AND_DATA.json"), "deployment")
    validation = mapping(json_file(stage, files, "evidence/VALIDATION.json"), "validation")
    report = mapping(json_file(stage, files, "report/REPORT_MANIFEST.json"), "report manifest")
    require(report.get("source_sha") == source_sha, "REPORT_SOURCE_MISMATCH")
    require(
        report.get("render_deploy_sha") == deployment.get("render_deployed_sha"),
        "REPORT_RENDER_SHA_MISMATCH",
    )
    verify_acceptance(acceptance, validation, deployment, source_sha)
    image_use = sequence(json_file(stage, files, "report/IMAGE_MATCHING.json"), "IMAGE_MATCHING")
    openapi = mapping(json_file(stage, files, "evidence/live_openapi.json"), "live openapi")
    contract = mapping(json_file(stage, files, "contracts/api_contract.json"), "API contract")
    raw_count = verify_images(stage, files, acceptance, report, image_use, openapi, contract)
    layout = mapping(json_file(stage, files, "evidence/REPORT_LAYOUT.json"), "report layout")
    verify_review(audit, report, layout, read_verified(stage, files, PDF), raw_count)
    manifest = {
        "schema": "mission18/public-grading-package/v1",
        "status": "FINAL_PUBLIC_GRADING_AUDITED",
        "source_sha": source_sha,
        "render_sha": deployment["render_deployed_sha"],
        "pdf_sha256": report["pdf_sha256"],
        "manifest_scope": "Every packaged file except MANIFEST_SHA256.json itself",
        "files": [
            dict(entry, kind=kinds[path]) for path, entry in files.items() if path != MANIFEST
        ],
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if MANIFEST in files:
        existing_bytes = read_verified(stage, files, MANIFEST)
        existing = mapping(parse_json(existing_bytes, MANIFEST), MANIFEST)
        require(
            existing.get("source_sha") == source_sha
            and existing.get("render_sha") == deployment["render_deployed_sha"]
            and existing.get("status") == "FINAL_PUBLIC_GRADING_AUDITED",
            "EXISTING_MANIFEST_PROVENANCE_MISMATCH",
        )
        entries = sequence(existing.get("files"), "existing manifest files")
        normalized = []
        for value in entries:
            row = mapping(value, "existing manifest entry")
            normalized.append(
                {
                    "path": safe_relative_path(row.get("path")),
                    "bytes": positive_int(row.get("bytes"), "manifest size", minimum=0),
                    "sha256": digest(row.get("sha256"), "manifest SHA"),
                }
            )
        require(
            sorted(normalized, key=lambda row: row["path"])
            == [entry for path, entry in files.items() if path != MANIFEST],
            "EXISTING_MANIFEST_FILE_MISMATCH",
        )
        manifest_bytes = existing_bytes
    summary = {
        "source_sha": source_sha,
        "render_sha": deployment["render_deployed_sha"],
        "pdf_sha256": report["pdf_sha256"],
        "page_count": report["page_count"],
        "placed_images": len(image_use),
        "raw_screenshots": raw_count,
        "swagger_operations": len(acceptance["swagger_operations"]),
        "acceptance_checks": len(acceptance["checks"]),
        "source_preserved_files": Counter(kinds.values())["source_preserved"],
        "file_count": len(manifest["files"]) + 1,
    }
    return files, summary, manifest_bytes


def validate_name(value: str) -> str:
    safe_relative_path(value)
    require(
        "/" not in value
        and len(value) <= 160
        and re.fullmatch(r"[A-Za-z0-9가-힣_-]+", value) is not None,
        "INVALID_SUBMISSION_NAME",
    )
    return value


def output_paths(output: Path, name: str) -> tuple[Path, Path, Path]:
    return output / (name + ".zip"), output / (name + "_최종보고서.pdf"), output / "SHA256SUMS.txt"


def verify_archive(
    archive: Path, name: str, files: dict[str, dict[str, Any]], manifest_bytes: bytes
) -> None:
    prefix = "미션18/" + validate_name(name) + "/"
    expected = {prefix + path for path in files if path != MANIFEST} | {prefix + MANIFEST}
    with zipfile.ZipFile(archive, "r") as zipped:
        entries = zipped.infolist()
        require(
            len(entries) == len(expected) and {entry.filename for entry in entries} == expected,
            "ARCHIVE_MEMBER_SET_MISMATCH",
        )
        require(zipped.testzip() is None, "ARCHIVE_CRC_FAILURE")
        for entry in entries:
            safe_relative_path(entry.filename)
            mode = entry.external_attr >> 16
            require(
                not entry.is_dir() and not stat.S_ISLNK(mode) and not (entry.flag_bits & 1),
                "UNSAFE_ARCHIVE_MEMBER",
            )
            data = zipped.read(entry)
            relative = entry.filename.removeprefix(prefix)
            if relative == MANIFEST:
                require(data == manifest_bytes, "ARCHIVED_MANIFEST_MISMATCH")
            else:
                require(
                    len(data) == files[relative]["bytes"]
                    and sha256(data) == files[relative]["sha256"],
                    "ARCHIVED_FILE_HASH_MISMATCH: " + relative,
                )


def verify_outputs(
    output: Path, name: str, files: dict[str, dict[str, Any]], manifest_bytes: bytes
) -> dict[str, Any]:
    archive, report, sums = output_paths(output, name)
    for path in (archive, report, sums):
        require(
            path.is_file() and not path.is_symlink(), "INCOMPLETE_OR_UNSAFE_OUTPUT: " + str(path)
        )
    verify_archive(archive, name, files, manifest_bytes)
    zip_sha = sha256(file_bytes(archive))
    pdf_data = file_bytes(report)
    pdf_sha = sha256(pdf_data)
    require(
        pdf_sha == files[PDF]["sha256"] and len(pdf_data) == files[PDF]["bytes"],
        "STANDALONE_PDF_MISMATCH",
    )
    expected_sums = f"{zip_sha}  {archive.name}\n{pdf_sha}  {report.name}\n".encode("utf-8")
    require(file_bytes(sums) == expected_sums, "SHA256SUMS_MISMATCH")
    return {
        "zip": str(archive),
        "zip_sha256": zip_sha,
        "zip_bytes": archive.stat().st_size,
        "pdf": str(report),
        "pdf_sha256": pdf_sha,
        "sha256sums": str(sums),
    }


def package_stage(
    stage: Path, output: Path, name: str, *, verify_only: bool = False
) -> dict[str, Any]:
    name = validate_name(name)
    require(output != stage and not output.is_relative_to(stage), "OUTPUT_MUST_BE_OUTSIDE_STAGE")
    files, summary, manifest_bytes = verify_stage(stage)
    targets = output_paths(output, name)
    occupied = [path for path in targets if os.path.lexists(path)]
    if verify_only:
        result = {"status": "STAGE_VERIFIED", **summary, "stage": str(stage), "writes": 0}
        if occupied:
            result.update(verify_outputs(output, name, files, manifest_bytes))
            result["status"] = "FINAL_PACKAGE_VERIFIED"
        return result
    require(
        not occupied,
        "OUTPUT_EXISTS_USE_NEW_DESTINATION: " + ", ".join(str(path) for path in occupied),
    )
    output.mkdir(parents=True, exist_ok=True)
    # Build and fully verify private temporary outputs before publishing names.
    # Exclusive hard links below never replace existing paths, even in a race.
    with tempfile.TemporaryDirectory(prefix=".m18-package-", dir=output) as temporary:
        pending = Path(temporary)
        archive, report, sums = output_paths(pending, name)
        prefix = "미션18/" + name + "/"
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED, compresslevel=8) as zipped:
            for relative in sorted(set(files) | {MANIFEST}):
                data = (
                    manifest_bytes
                    if relative == MANIFEST
                    else read_verified(stage, files, relative)
                )
                info = zipfile.ZipInfo(prefix + relative, (2020, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                zipped.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=8)
        with report.open("xb") as stream:
            stream.write(read_verified(stage, files, PDF))
        with sums.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(
                f"{sha256(file_bytes(archive))}  {archive.name}\n"
                f"{sha256(file_bytes(report))}  {report.name}\n"
            )
        verify_outputs(pending, name, files, manifest_bytes)
        require(collect_files(stage) == files, "STAGE_CHANGED_DURING_PACKAGING")
        for source, target in zip((archive, report, sums), targets):
            os.link(source, target, follow_symlinks=False)
    result = verify_outputs(output, name, files, manifest_bytes)
    return {"status": "FINAL_PACKAGE_VERIFIED", **summary, **result, "stage": str(stage)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--stage", required=True, help="Absolute path of the already reviewed stage"
    )
    parser.add_argument("--output", required=True, help="Absolute directory for new final outputs")
    parser.add_argument(
        "--name", default="미션18_2팀_이형기", help="Submission name without path separators"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the stage and any existing outputs without writing",
    )
    args = parser.parse_args(argv)
    try:
        result = package_stage(
            absolute_path(args.stage, must_exist=True),
            absolute_path(args.output, must_exist=False),
            args.name,
            verify_only=args.verify_only,
        )
    except (PackageError, OSError, UnicodeError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(
            json.dumps(
                {"status": "BLOCKED", "error": str(exc), "retried": False}, ensure_ascii=False
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
