<script lang="ts">
  import DocumentInput from "./components/DocumentInput.svelte";
  import DocumentTreeNode from "./components/DocumentTreeNode.svelte";
  import { selection } from "./lib/documents.svelte";
  import { parseToc } from "./lib/tocTree";

  let tree = $derived(selection.document?.toc ? parseToc(selection.document.toc) : []);
</script>

<main class="panels" aria-label="Document workspace">
  <section class="panel" aria-labelledby="document-input-title">
    <DocumentInput />
  </section>
  <section class="panel" aria-labelledby="search-title">
    <h2 id="search-title">Search</h2>
  </section>
  <section class="panel" aria-labelledby="document-view-title">
    <h2 id="document-view-title">Document view</h2>
    {#if selection.document}
      <h3 class="selected-document-title" title={selection.document.path}>{selection.document.path}</h3>
      {#if selection.document.toc}
        <ul class="document-tree" aria-label="Document structure">
          {#each tree as node}
            <DocumentTreeNode {node} />
          {/each}
        </ul>
      {:else if selection.document.state === "error"}
        <p class="tree-message state-error">{selection.document.error ?? "Document analysis failed."}</p>
      {:else}
        <p class="tree-message">Analysis is still in progress.</p>
      {/if}
    {:else}
      <p class="tree-message">Select a document to view its structure.</p>
    {/if}
  </section>
</main>
