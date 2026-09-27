import { sha256 } from "@noble/hashes/sha2.js";

/** Hashes the file's bytes with SHA-256 without loading the entire file into memory. */
export async function hashFile(file: File): Promise<string> {
  const hash = sha256.create();
  const reader = file.stream().getReader();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      hash.update(value);
    }
  } finally {
    reader.releaseLock();
  }

  const digest = hash.digest();
  const hex = Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `sha256:${hex}`;
}
