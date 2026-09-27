export type DocumentEntry = {
  path: string;
  hash: string;
};

export const documents = $state<DocumentEntry[]>([]);
