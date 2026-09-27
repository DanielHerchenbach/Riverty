export type DocumentEntry = {
  path: string;
  hash?: string;
  state: "hashing" | "ready" | "error";
};

export const documents = $state<DocumentEntry[]>([]);
