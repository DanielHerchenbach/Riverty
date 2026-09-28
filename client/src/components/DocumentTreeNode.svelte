<script lang="ts">
  import DocumentTreeNode from "./DocumentTreeNode.svelte";
  import { DOCUMENT_ROOT_ID, type TreeNode } from "../lib/documentTree";

  let { node, matches, ancestors, hasResults }: {
    node: TreeNode;
    matches: Set<string>;
    ancestors: Set<string>;
    hasResults: boolean;
  } = $props();
  let expanded = $state(true);
  $effect(() => {
    expanded = !hasResults || ancestors.has(node.id)
      || (matches.has(node.id) && node.id !== DOCUMENT_ROOT_ID);
  });
</script>

<li data-node-id={node.id}>
  <div class="tree-row" class:node-match={matches.has(node.id)}
    class:ancestor-match={!matches.has(node.id) && ancestors.has(node.id)}
    class:document-root={node.id === DOCUMENT_ROOT_ID}>
    {#if node.children.length > 0}
      <button
        class="tree-toggle"
        type="button"
        aria-expanded={expanded}
        aria-label={`${expanded ? "Collapse" : "Expand"} ${node.text}`}
        onclick={() => (expanded = !expanded)}
      >
        {expanded ? "-" : "+"}
      </button>
    {:else}
      <span class="tree-spacer"></span>
    {/if}
    <span>{node.text}</span>
    {#if matches.has(node.id)}<span class="match-label">Match</span>{/if}
  </div>
  {#if expanded && node.children.length > 0}
    <ul>
      {#each node.children as child (child.id)}
        <DocumentTreeNode node={child} {matches} {ancestors} {hasResults} />
      {/each}
    </ul>
  {/if}
</li>
