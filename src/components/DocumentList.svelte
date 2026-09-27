<script lang="ts">
  import { documents } from "../lib/documents.svelte";

  function removeDocument(hash: string) {
    const index = documents.findIndex((document) => document.hash === hash);
    if (index !== -1) documents.splice(index, 1);
  }
</script>

<ul class="document-list">
  {#each documents as document (document.hash)}
    <li>
      <span class="document-path" title={document.path}>{document.path}</span>
      <code>{document.hash}</code>
      <button type="button" aria-label={`Remove ${document.path}`} onclick={() => removeDocument(document.hash)}>
        Remove
      </button>
    </li>
  {/each}
</ul>
