CREATE EXTENSION IF NOT EXISTS vector;

/* Analysis returns `{hash, ext, tree}`. `tree` is an ordered array of roots, each
with `{id, text, children}`. IDs are unique within the file, assigned in preorder,
and stable for the stored tree.
*/
CREATE TABLE IF NOT EXISTS files (
    hash TEXT NOT NULL,
    ext TEXT NOT NULL,
    tree JSONB NULL,
    CONSTRAINT files_hash_ext_unique UNIQUE (hash, ext)
);

/* node_ids may be individual leaf nodes or larger subtree roots.
text is the exactly what is used for embedding, including the text of each node's ancestors to maintain context.
*/
CREATE TABLE IF NOT EXISTS chunks (
    file_hash TEXT NOT NULL,
    file_ext TEXT NOT NULL,
    node_ids TEXT[] NOT NULL CHECK (cardinality(node_ids) > 0),
    text TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    FOREIGN KEY (file_hash, file_ext) REFERENCES files(hash, ext) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS chunks_file_idx ON chunks(file_hash, file_ext);
