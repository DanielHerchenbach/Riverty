<script lang="ts">
  import { documents, type DocumentEntry } from "../lib/documents.svelte";
</script>

<ul class="document-list">
  {#each documents as document, index}
    <li>
      <span class="document-path" title={document.path}>{document.path}</span>
      <span class="document-state" class:state-error={document.state === "error"}>
        {document.state}
      </span>
      <button type="button" aria-label={`Remove ${document.path}`} onclick={() => documents.splice(index, 1)}>
        Remove
      </button>
    </li>
  {/each}
</ul>
