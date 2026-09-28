<script lang="ts">
  import DocumentTreeNode from "./DocumentTreeNode.svelte";
  import type { TocNode } from "../lib/tocTree";

  let { node }: { node: TocNode } = $props();
  let expanded = $state(true);
</script>

<li>
  <div class="tree-row">
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
  </div>
  {#if expanded && node.children.length > 0}
    <ul>
      {#each node.children as child}
        <DocumentTreeNode node={child} />
      {/each}
    </ul>
  {/if}
</li>
