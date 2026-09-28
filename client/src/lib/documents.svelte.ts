import type { TreeNode } from "./documentTree";
import type { DocumentSearchResult } from "./documentApi";

export type DocumentEntry = {
  path: string;
  hash?: string;
  ext?: string;
  tree?: TreeNode[];
  state: "hashing" | "uploading" | "analyzing" | "ready" | "error";
  error?: string;
  searchResult?: DocumentSearchResult;
};

export const documents = $state<DocumentEntry[]>([]);
export const selection = $state<{ document: DocumentEntry | null }>({ document: null });

export const searchState = $state({ running: false, revision: 0 });
