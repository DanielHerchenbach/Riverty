<script lang="ts">
  import { documents, selection } from "../lib/documents.svelte";
</script>

<ul class="document-list">
  {#each documents as document, index}
    <li>
      <button
        type="button"
        class="document-row"
        class:selected={selection.document === document}
        aria-pressed={selection.document === document}
        onclick={() => (selection.document = document)}
      >
        <span class="document-path" title={document.path}>{document.path}</span>
        <span class="document-state" class:state-error={document.state === "error"}>
          {document.state === "hashing" ? "Hashing…" :
            document.state === "uploading" ? "Uploading…" :
            document.state === "analyzing" ? "Analyzing…" :
            document.state === "error" ? document.error ?? "Failed" :
            document.searchResult?.status === "error" ? "Search failed" :
            document.searchResult ? `${document.searchResult.matches.length} match${document.searchResult.matches.length === 1 ? "" : "es"}` : "Ready"}
        </span>
      </button>
      <button type="button" aria-label={`Remove ${document.path}`} onclick={() => {
        if (selection.document === document) selection.document = null;
        documents.splice(index, 1);
      }}>
        Remove
      </button>
    </li>
  {/each}
</ul>
