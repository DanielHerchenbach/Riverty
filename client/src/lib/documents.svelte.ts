import type { TreeNode } from "./documentTree";

export type DocumentEntry = {
  path: string;
  hash?: string;
  ext?: string;
  tree?: TreeNode[];
  state: "hashing" | "uploading" | "analyzing" | "ready" | "error";
  error?: string;
};

export const documents = $state<DocumentEntry[]>([]);
export const selection = $state<{ document: DocumentEntry | null }>({ document: null });
