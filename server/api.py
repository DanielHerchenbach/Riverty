import asyncio
import logging
import os
import re
import uuid
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from openai import APITimeoutError

from server.storage import save_analysis

SERVER_DIR = Path(__file__).resolve().parent
load_dotenv(SERVER_DIR / ".env")

DATABASE_URL = os.environ.get("RIVERTY_DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set RIVERTY_DATABASE_URL in server/.env")
FILES_DIR = Path(os.environ.get("RIVERTY_FILES_DIR", SERVER_DIR / "files"))

app = FastAPI()
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_methods=["GET", "HEAD", "PUT", "OPTIONS"],
    allow_headers=["*"],
)


def validate_file_key(file_hash: str, ext: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", file_hash) is None:
        raise HTTPException(status_code=422, detail="hash must be a lowercase SHA-256 hex digest")
    if re.fullmatch(r"[a-z0-9]{1,12}", ext) is None:
        raise HTTPException(status_code=422, detail="ext must be a lowercase file extension")


def stored_file_path(file_hash: str, ext: str) -> Path:
    return FILES_DIR / f"{file_hash}.{ext}"


@app.head("/api/upload/{file_hash}/{ext}")
def file_exists(file_hash: str, ext: str) -> Response:
    validate_file_key(file_hash, ext)
    with psycopg.connect(DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT 1 FROM files WHERE hash = %s AND ext = %s",
            (file_hash, ext),
        ).fetchone()

    if row is None or not stored_file_path(file_hash, ext).is_file():
        return Response(status_code=404)
    return Response(status_code=200)


@app.put("/api/upload/{file_hash}/{ext}")
def upload_file(file_hash: str, ext: str, file: UploadFile = File(...)) -> dict[str, str | bool]:
    validate_file_key(file_hash, ext)
    final_path = stored_file_path(file_hash, ext)

    with psycopg.connect(DATABASE_URL) as connection:
        existing = connection.execute(
            "SELECT 1 FROM files WHERE hash = %s AND ext = %s",
            (file_hash, ext),
        ).fetchone()
    if existing is not None and final_path.is_file():
        return {"hash": file_hash, "ext": ext, "already_present": True}

    FILES_DIR.mkdir(parents=True, exist_ok=True)
    temporary_path = FILES_DIR / f"{uuid.uuid4()}.tmp"
    try:
        with temporary_path.open("wb") as destination:
            while chunk := file.file.read(1024 * 1024):
                destination.write(chunk)
        temporary_path.replace(final_path)

        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "INSERT INTO files (hash, ext, tree) VALUES (%s, %s, NULL) "
                "ON CONFLICT (hash, ext) DO NOTHING",
                (file_hash, ext),
            )
    except Exception as error:
        temporary_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not store the uploaded file") from error
    finally:
        file.file.close()

    return {"hash": file_hash, "ext": ext, "already_present": False}


@app.put("/api/analyze/{file_hash}/{ext}")
def analyze_file(file_hash: str, ext: str) -> dict:
    validate_file_key(file_hash, ext)

    with psycopg.connect(DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT tree FROM files WHERE hash = %s AND ext = %s",
            (file_hash, ext),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="File has not been uploaded")
    if row[0] is not None:
        return {"hash": file_hash, "ext": ext, "tree": row[0]}

    pdf_path = stored_file_path(file_hash, ext)
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="Stored file is missing")

    try:
        from server.services.analysis import analyze_document

        result = asyncio.run(analyze_document(pdf_path))
        with psycopg.connect(DATABASE_URL) as connection:
            tree = save_analysis(connection, file_hash, ext, result.tree, result.chunks)
    except Exception as error:
        logger.exception("Document analysis failed for %s.%s", file_hash, ext)
        if isinstance(error, APITimeoutError):
            raise HTTPException(status_code=504, detail="Document analysis timed out; retry analysis") from error
        raise HTTPException(status_code=502, detail="Document analysis failed") from error

    return {"hash": file_hash, "ext": ext, "tree": tree}
