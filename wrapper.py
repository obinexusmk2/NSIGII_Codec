# nsigii_wrapper.py

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final

MAGIC: Final[bytes] = b"NSIGII\x00\x00"
VERSION_MAJOR: Final[int] = 1
VERSION_MINOR: Final[int] = 0
VERSION_PATCH: Final[int] = 0

HEADER_STRUCT: Final[struct.Struct] = struct.Struct("<8sBBBx16sQQ")
CHUNK_HEADER_STRUCT: Final[struct.Struct] = struct.Struct("<QQI32s")
DEFAULT_CHUNK_SIZE: Final[int] = 64 * 1024


@dataclass(frozen=True)
class Manifest:
    original_name: str
    original_type: str
    original_size: int
    chunk_size: int
    chunk_count: int
    sha256_total: str
    created_at_unix_nano: int
    session_id: str
    wrapper: str
    mirror_model: str

    def to_bytes(self) -> bytes:
        payload = {
            "original_name": self.original_name,
            "original_type": self.original_type,
            "original_size": self.original_size,
            "chunk_size": self.chunk_size,
            "chunk_count": self.chunk_count,
            "sha256_total": self.sha256_total,
            "created_at_unix_nano": self.created_at_unix_nano,
            "session_id": self.session_id,
            "wrapper": self.wrapper,
            "mirror_model": self.mirror_model,
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wrap a .zip file into a .nsigii container with chunk hashes."
    )
    parser.add_argument("input_zip", type=Path, help="Path to the input .zip file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to the output .nsigii file (default: <input>.nsigii)",
    )
    parser.add_argument(
        "-c",
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Chunk size in bytes (default: {DEFAULT_CHUNK_SIZE})",
    )
    return parser.parse_args()


def validate_args(input_zip: Path, output_path: Path, chunk_size: int) -> None:
    if not input_zip.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_zip}")
    if not input_zip.is_file():
        raise ValueError(f"Input path is not a file: {input_zip}")
    if input_zip.suffix.lower() != ".zip":
        raise ValueError(f"Input must be a .zip file: {input_zip}")
    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero")
    if output_path.resolve() == input_zip.resolve():
        raise ValueError("Output path must be different from input path")


def derive_output_path(input_zip: Path, output: Path | None) -> Path:
    if output is not None:
        return output
    return input_zip.with_suffix(".nsigii")


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def build_manifest(input_zip: Path, chunk_size: int, session_id: uuid.UUID) -> Manifest:
    file_size = input_zip.stat().st_size
    chunk_count = math.ceil(file_size / chunk_size) if file_size > 0 else 0
    created_at_unix_nano = time.time_ns()
    total_hash = sha256_file(input_zip)

    return Manifest(
        original_name=input_zip.name,
        original_type="zip",
        original_size=file_size,
        chunk_size=chunk_size,
        chunk_count=chunk_count,
        sha256_total=total_hash,
        created_at_unix_nano=created_at_unix_nano,
        session_id=str(session_id),
        wrapper="zip->nsigii",
        mirror_model="send-receive-reflect",
    )


def write_header(
    handle: BinaryIO,
    session_id: uuid.UUID,
    created_at_unix_nano: int,
    manifest_length: int,
) -> None:
    header = HEADER_STRUCT.pack(
        MAGIC,
        VERSION_MAJOR,
        VERSION_MINOR,
        VERSION_PATCH,
        session_id.bytes,
        created_at_unix_nano,
        manifest_length,
    )
    handle.write(header)


def iter_chunks(path: Path, chunk_size: int):
    with path.open("rb") as handle:
        offset = 0
        sequence = 0
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            yield sequence, offset, chunk
            sequence += 1
            offset += len(chunk)


def write_chunk_record(handle: BinaryIO, sequence: int, offset: int, payload: bytes) -> None:
    chunk_hash = hashlib.sha256(payload).digest()
    record_header = CHUNK_HEADER_STRUCT.pack(sequence, offset, len(payload), chunk_hash)
    handle.write(record_header)
    handle.write(payload)


def wrap_zip_to_nsigii(input_zip: Path, output_path: Path, chunk_size: int) -> Manifest:
    session_id = uuid.uuid4()
    manifest = build_manifest(input_zip, chunk_size, session_id)
    manifest_bytes = manifest.to_bytes()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("wb") as out:
        write_header(
            handle=out,
            session_id=session_id,
            created_at_unix_nano=manifest.created_at_unix_nano,
            manifest_length=len(manifest_bytes),
        )
        out.write(manifest_bytes)

        for sequence, offset, chunk in iter_chunks(input_zip, chunk_size):
            write_chunk_record(out, sequence, offset, chunk)

    return manifest


def format_size(num_bytes: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{num_bytes} B"


def main() -> int:
    try:
        args = parse_args()
        input_zip = args.input_zip
        output_path = derive_output_path(input_zip, args.output)
        validate_args(input_zip, output_path, args.chunk_size)

        manifest = wrap_zip_to_nsigii(
            input_zip=input_zip,
            output_path=output_path,
            chunk_size=args.chunk_size,
        )

        print("NSIGII wrapper complete")
        print(f"Input:        {input_zip}")
        print(f"Output:       {output_path}")
        print(f"Session ID:   {manifest.session_id}")
        print(f"ZIP size:     {format_size(manifest.original_size)}")
        print(f"Chunk size:   {format_size(manifest.chunk_size)}")
        print(f"Chunk count:  {manifest.chunk_count}")
        print(f"Total SHA256: {manifest.sha256_total}")
        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())