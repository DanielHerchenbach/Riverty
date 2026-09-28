<script lang="ts">
  import { documents, searchState } from "../lib/documents.svelte";
  import { searchDocuments, type SearchDocument } from "../lib/documentApi";

  let prompt = $state("");
  let explanations = $state<string[]>([]);
  let error = $state("");
  let submittedPrompt = $state("");
  let ready = $derived(documents.filter((document) => document.state === "ready"));

  async function search(event: SubmitEvent) {
    event.preventDefault();
    if (searchState.running || !prompt.trim() || ready.length === 0) return;
    const targets = [...ready];
    const references: SearchDocument[] = targets.map((document) => ({
      hash: document.hash!, ext: document.ext!, name: document.path,
    }));
    for (const document of documents) document.searchResult = undefined;
    explanations = [];
    error = "";
    submittedPrompt = prompt.trim();
    searchState.revision += 1;
    searchState.running = true;
    try {
      const result = await searchDocuments(submittedPrompt, references);
      explanations = result.explanations;
      for (const document of targets) {
        document.searchResult = result.documents.find(
          (item) => item.hash === document.hash && item.ext === document.ext,
        );
      }
    } catch (failure) {
      error = failure instanceof Error ? failure.message : "Search failed";
    } finally {
      searchState.running = false;
      searchState.revision += 1;
    }
  }
</script>

<h2 id="search-title">Search</h2>
<form class="search-form" onsubmit={search}>
  <label for="search-prompt">What would you like to find?</label>
  <textarea id="search-prompt" bind:value={prompt} rows="2" maxlength="10000"
    placeholder="Find contracts missing a termination clause" disabled={searchState.running}></textarea>
  <div class="search-actions">
    <button type="submit" disabled={searchState.running || !prompt.trim() || ready.length === 0}>
      {searchState.running ? "Searching…" : "Search documents"}
    </button>
    <span>{ready.length} ready document{ready.length === 1 ? "" : "s"} in scope</span>
  </div>
</form>
<div class="search-explanation" aria-live="polite" aria-busy={searchState.running}>
  {#if searchState.running}
    <p>Planning the search and reviewing documents…</p>
  {:else if error}
    <p class="state-error" role="alert">{error}</p>
  {:else if explanations.length}
    <p><strong>Results for:</strong> {submittedPrompt}</p>
    {#each explanations as explanation}<p>{explanation}</p>{/each}
  {/if}
</div>
