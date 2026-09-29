import type { TreeNode } from "./documentTree";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type TreeResponse = {
  tree: TreeNode[];
};

export type StoredDocument = {
  hash: string;
  ext: string;
  filename: string;
  tree: TreeNode[] | null;
};

export async function listDocuments(): Promise<StoredDocument[]> {
  const response = await fetch(`${API_BASE_URL}/api/files`);
  await ensureSuccess(response);
  return response.json();
}

export type SearchDocument = { hash: string; ext: string; name: string };
export type DocumentSearchResult = {
  hash: string;
  ext: string;
  matches: string[];
  status: "evaluated" | "no_candidates" | "error";
  error: string | null;
};
export type SearchResponse = {
  plan: { exact_phrases: string[]; semantic_queries: string[] };
  explanations: string[];
  documents: DocumentSearchResult[];
};

export async function searchDocuments(prompt: string, documents: SearchDocument[]): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, documents }),
  });
  await ensureSuccess(response);
  return response.json();
}

async function ensureSuccess(response: Response): Promise<void> {
  if (response.ok) return;

  let detail = `${response.status} ${response.statusText}`;
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) detail = body.detail;
  } catch {
    // Keep the status text when the server does not return a JSON error body.
  }

  throw new Error(detail);
}

export async function uploadIfMissing(file: File, hash: string, ext: string): Promise<void> {
  const url = `${API_BASE_URL}/api/upload/${hash}/${ext}`;
  const check = await fetch(url, { method: "HEAD" });

  if (check.status === 200) return;
  if (check.status !== 404) await ensureSuccess(check);

  const form = new FormData();
  form.append("file", file, file.name);
  const upload = await fetch(url, { method: "PUT", body: form });
  await ensureSuccess(upload);
}

export async function analyzeDocument(hash: string, ext: string): Promise<TreeNode[]> {
  const response = await fetch(`${API_BASE_URL}/api/analyze/${hash}/${ext}`, {
    method: "PUT",
  });
  await ensureSuccess(response);

  const result = (await response.json()) as TreeResponse;
  return result.tree;
}
