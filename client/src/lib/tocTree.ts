export type TocNode = {
  text: string;
  children: TocNode[];
};

export function parseToc(toc: string): TocNode[] {
  const roots: TocNode[] = [];
  const parents: TocNode[] = [];

  for (const line of toc.split(/\r?\n/)) {
    if (!line.trim()) continue;

    const indent = line.match(/^ */)?.[0].length ?? 0;
    const level = Math.min(Math.floor(indent / 2), parents.length);
    const node: TocNode = { text: line.slice(indent), children: [] };
    const parent = level === 0 ? undefined : parents[level - 1];

    if (parent) parent.children.push(node);
    else roots.push(node);

    parents.length = level;
    parents.push(node);
  }

  return roots;
}
