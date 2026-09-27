<script lang="ts">
  import DocumentInput from "./components/DocumentInput.svelte";
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
  </section>
</main>
