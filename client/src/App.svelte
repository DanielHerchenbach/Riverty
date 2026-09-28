<script lang="ts">
  import DocumentInput from "./components/DocumentInput.svelte";
  import DocumentTreeNode from "./components/DocumentTreeNode.svelte";
  import DocumentSearch from "./components/DocumentSearch.svelte";
  import { selection, searchState } from "./lib/documents.svelte";
  import { documentRoot, matchAncestors } from "./lib/documentTree";

  let root = $derived(selection.document?.tree
    ? documentRoot(selection.document.path, selection.document.tree) : null);
  let matches = $derived(new Set(selection.document?.searchResult?.matches ?? []));
  let ancestors = $derived(root ? matchAncestors(root, matches) : new Set<string>());
  let hasResults = $derived(selection.document?.searchResult !== undefined
    && selection.document.searchResult.status !== "error");
</script>

<main class="panels" aria-label="Document workspace">
  <section class="panel" aria-labelledby="document-input-title">
    <DocumentInput />
  </section>
  <section class="panel" aria-labelledby="search-title">
    <DocumentSearch />
  </section>
  <section class="panel" aria-labelledby="document-view-title">
    <h2 id="document-view-title">Document view</h2>
    {#if selection.document}
      {#if root}
        {#if selection.document.searchResult?.status === "error"}
          <p class="tree-message state-error">{selection.document.searchResult.error}</p>
        {:else if selection.document.searchResult?.status === "no_candidates"}
          <p class="tree-message">No candidate passages were retrieved for this document.</p>
        {/if}
        {#key `${selection.document.hash}.${selection.document.ext}.${searchState.revision}`}
          <ul class="document-tree" aria-label="Document structure">
            <DocumentTreeNode node={root} {matches} {ancestors} {hasResults} />
          </ul>
        {/key}
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
