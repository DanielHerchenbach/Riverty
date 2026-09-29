<script lang="ts">
  import { documents, searchState } from "../lib/documents.svelte";
  import { searchDocuments, type SearchDocument, type SearchResponse } from "../lib/documentApi";
  import { IconSearch, IconSortAZ, IconVector, IconFileSearch, IconChevronDown, IconLoader2 } from "@tabler/icons-svelte";

  let prompt = $state("");
  let result = $state<SearchResponse | null>(null);
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
    result = null;
    error = "";
    submittedPrompt = prompt.trim();
    searchState.revision += 1;
    searchState.running = true;
    try {
      const response = await searchDocuments(submittedPrompt, references);
      result = response;
      for (const document of targets) {
        document.searchResult = response.documents.find(
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

<form class="search-form" onsubmit={search}>
  <label class="sr-only" id="search-title" for="search-prompt">Search documents</label>
  <div class="search-field">
    <textarea id="search-prompt" bind:value={prompt} rows="2" maxlength="10000"
      placeholder="Find contracts missing a termination clause... Find provisions containing a date or time period..." disabled={searchState.running}></textarea>
    <button class="primary-button" type="submit" disabled={searchState.running || !prompt.trim() || ready.length === 0}>
      {#if searchState.running}<IconLoader2 size={18} class="spin" />{:else}<IconSearch size={18} />{/if}
      {searchState.running ? "Searching…" : "Search"}
    </button>
  </div>
  <div class="search-actions">
    <span>{ready.length} document{ready.length === 1 ? "" : "s"} ready to search</span>
    {#if ready.length === 0}<span>Add documents to get started</span>{/if}
  </div>
</form>
<div class="search-explanation" aria-live="polite" aria-busy={searchState.running}>
  {#if searchState.running}
    <p class="search-progress"><span class="status-dot"></span>Planning the search and reviewing documents…</p>
  {:else if error}
    <p class="state-error" role="alert">{error}</p>
  {:else if result}
    <details class="search-plan">
      <summary>
        <span class="plan-label">Search approach</span>
        <span class="search-methods">
          {#if result.plan.exact_phrases.length}
            <span class="method-badge text-method"><IconSortAZ size={16} />Text <span class="badge-count">{result.plan.exact_phrases.length}</span></span>
          {/if}
          {#if result.plan.semantic_queries.length}
            <span class="method-badge semantic-method"><IconVector size={16} />Semantic <span class="badge-count">{result.plan.semantic_queries.length}</span></span>
          {/if}
          {#if !result.plan.exact_phrases.length && !result.plan.semantic_queries.length}
            <span class="method-badge review-method"><IconFileSearch size={16} />Full document review</span>
          {/if}
        </span>
        <span class="review-count">{result.documents.filter((document) => document.status === "evaluated").length} / {result.documents.length} reviewed</span>
        <IconChevronDown size={16} class="plan-chevron" />
      </summary>
      <div class="plan-content">
        <p class="result-prompt"><span>Results for</span> {submittedPrompt}</p>
        {#if result.plan.exact_phrases.length}
          <div class="plan-group">
            <span class="method-badge text-method"><IconSortAZ size={16} />Text search</span>
            <div class="query-chips">{#each result.plan.exact_phrases as phrase}<span class="query-chip text-method">{phrase}</span>{/each}</div>
            <p>Matches any phrase, ignoring capitalization.</p>
          </div>
        {/if}
        {#if result.plan.semantic_queries.length}
          <div class="plan-group">
            <span class="method-badge semantic-method"><IconVector size={16} />Semantic search</span>
            <div class="query-chips">{#each result.plan.semantic_queries as query}<span class="query-chip semantic-method">{query}</span>{/each}</div>
            <p>Finds passages with a similar meaning to any query.</p>
          </div>
        {/if}
        <p class="plan-note">{result.plan.exact_phrases.length || result.plan.semantic_queries.length
          ? "Retrieved candidates are combined and reviewed against your request."
          : "Entire documents are reviewed against your request, without text or semantic filtering."}</p>
        {#if result.documents.some((document) => document.status === "error")}
          <p class="state-error">Some documents could not be reviewed. Retry the search to review them.</p>
        {/if}
      </div>
    </details>
  {/if}
</div>
