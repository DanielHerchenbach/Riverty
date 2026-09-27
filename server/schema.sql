CREATE TABLE IF NOT EXISTS files (
    hash TEXT NOT NULL,
    ext TEXT NOT NULL,
    toc TEXT NULL,
    CONSTRAINT files_hash_ext_unique UNIQUE (hash, ext)
);
