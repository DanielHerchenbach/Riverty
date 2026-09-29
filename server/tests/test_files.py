import io
import os
import tempfile
import unittest
from contextlib import ExitStack, nullcontext
from pathlib import Path
from unittest.mock import patch

import psycopg
from dotenv import load_dotenv
from fastapi import UploadFile
from psycopg.types.json import Jsonb


class FilesDatabaseTests(unittest.TestCase):
    def setUp(self):
        load_dotenv("server/.env")
        database_url = os.environ.get("RIVERTY_DATABASE_URL")
        if not database_url:
            self.skipTest("RIVERTY_DATABASE_URL is not configured")
        from server import api

        self.api = api
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.connection = stack.enter_context(psycopg.connect(database_url))
        stack.enter_context(self.connection.transaction(force_rollback=True))
        self.connection.execute(
            "CREATE TEMP TABLE files (hash text, ext text, filename text NOT NULL, "
            "tree jsonb, UNIQUE (hash, ext)) ON COMMIT DROP"
        )
        directory = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(patch.object(api, "FILES_DIR", Path(directory)))
        stack.enter_context(patch.object(api.psycopg, "connect", side_effect=lambda _: nullcontext(self.connection)))

    def test_list_restores_names_and_trees_including_unanalyzed_files(self):
        tree = [{"id": "n1", "text": "Contract", "children": []}]
        self.connection.execute(
            "INSERT INTO files VALUES (%s, 'pdf', 'Original contract.pdf', %s), "
            "(%s, 'pdf', 'Pending contract.pdf', NULL)",
            ("a" * 64, Jsonb(tree), "b" * 64),
        )
        self.assertEqual(self.api.list_files(), [
            {"hash": "a" * 64, "ext": "pdf", "filename": "Original contract.pdf", "tree": tree},
            {"hash": "b" * 64, "ext": "pdf", "filename": "Pending contract.pdf", "tree": None},
        ])

    def test_upload_keeps_full_original_filename_across_duplicate_uploads(self):
        file_hash = "a" * 64
        upload = UploadFile(file=io.BytesIO(b"document"), filename="Original contract ü.pdf")
        self.assertFalse(self.api.upload_file(file_hash, "pdf", upload)["already_present"])
        self.assertEqual(self.api.stored_file_path(file_hash, "pdf").read_bytes(), b"document")
        duplicate = UploadFile(file=io.BytesIO(b"document"), filename="Renamed.pdf")
        self.assertTrue(self.api.upload_file(file_hash, "pdf", duplicate)["already_present"])
        self.assertEqual(self.api.list_files(), [
            {"hash": file_hash, "ext": "pdf", "filename": "Original contract ü.pdf", "tree": None},
        ])

    def test_migration_backfills_legacy_names_and_can_be_reapplied(self):
        self.connection.execute("ALTER TABLE files DROP COLUMN filename")
        first = "7837df24989af83a369b3f1e8cf7aaf8b2cb38d85faef493496dac19830debde"
        second = "4f7f73fad7d3f00c1f17c11894ac56867d049a7de006b38f172120e5c7bf458e"
        self.connection.execute("INSERT INTO files VALUES (%s, 'pdf', NULL), (%s, 'pdf', NULL)", (first, second))
        migration = Path("server/migrations/001_original_filename.sql").read_text()
        # Keep the migration inside the test's rollback transaction.
        migration = migration.replace("BEGIN;", "").replace("COMMIT;", "")
        self.connection.execute(migration)
        self.connection.execute("UPDATE files SET filename = 'User renamed.pdf' WHERE hash = %s", (second,))
        self.connection.execute(migration)
        self.assertEqual(self.connection.execute("SELECT hash, filename FROM files ORDER BY hash DESC").fetchall(),
                         [(first, "test1"), (second, "User renamed.pdf")])
