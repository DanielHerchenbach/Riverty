export type DocumentEntry = {
  path: string;
  hash?: string;
  ext?: string;
  toc?: string;
  state: "hashing" | "uploading" | "analyzing" | "ready" | "error";
  error?: string;
};

export const documents = $state<DocumentEntry[]>([]);
