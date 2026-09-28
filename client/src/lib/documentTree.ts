export type TreeNode = {
  id: string;
  text: string;
  children: TreeNode[];
};

export const DOCUMENT_ROOT_ID = "document_root";

export function documentRoot(name: string, children: TreeNode[]): TreeNode {
  return { id: DOCUMENT_ROOT_ID, text: name, children };
}

export function matchAncestors(root: TreeNode, matches: Set<string>): Set<string> {
  const ancestors = new Set<string>();
  function visit(node: TreeNode): boolean {
    let descendantMatch = false;
    for (const child of node.children) {
      if (visit(child)) descendantMatch = true;
    }
    if (descendantMatch) ancestors.add(node.id);
    return descendantMatch || matches.has(node.id);
  }
  visit(root);
  return ancestors;
}
