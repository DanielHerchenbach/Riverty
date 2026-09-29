<script lang="ts">
  import { onMount } from "svelte";
  import { documents, type DocumentEntry } from "../lib/documents.svelte";
  import { hashFile } from "../lib/hash";
  import { analyzeDocument, listDocuments, uploadIfMissing } from "../lib/documentApi";
  import DocumentList from "./DocumentList.svelte";

  let loading = $state(true);
  let loadError = $state<string | null>(null);

  onMount(() => { void loadDocuments(); });

  async function loadDocuments() {
    loading = true;
    loadError = null;
    try {
      for (const file of await listDocuments()) {
        if (documents.some((entry) => entry.hash === file.hash && entry.ext === file.ext)) continue;
        documents.push({
          path: file.filename,
          hash: file.hash,
          ext: file.ext,
          tree: file.tree ?? undefined,
          state: file.tree === null ? "analyzing" : "ready",
        });
        const entry = documents[documents.length - 1];
        if (entry && file.tree === null) void analyzeEntry(entry, file.hash, file.ext);
      }
    } catch (error) {
      loadError = error instanceof Error ? error.message : "Could not load documents";
    } finally {
      loading = false;
    }
  }

  async function analyzeEntry(entry: DocumentEntry, hash: string, ext: string) {
    try {
      entry.state = "analyzing";
      entry.tree = await analyzeDocument(hash, ext);
      entry.state = "ready";
    } catch (error) {
      entry.state = "error";
      entry.error = error instanceof Error ? error.message : "Document analysis failed";
    }
  }

  function addFiles(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = "";
    for (const file of files) {
      const entry: DocumentEntry = { path: file.name, state: "hashing" };
      documents.push(entry);
      const reactiveEntry = documents[documents.length - 1];
      if (reactiveEntry) processDocument(reactiveEntry, file);
    }
  }

  async function processDocument(entry: DocumentEntry, file: File) {
    try {
      const hash = await hashFile(file);
      const ext = getFileExtension(file.name);
      entry.hash = hash;
      entry.ext = ext;

      entry.state = "uploading";
      await uploadIfMissing(file, hash, ext);

      await analyzeEntry(entry, hash, ext);
    } catch (error) {
      entry.state = "error";
      entry.error = error instanceof Error ? error.message : "Document processing failed";
    }
  }

  function getFileExtension(filename: string): string {
    const dot = filename.lastIndexOf(".");
    const extension = dot > 0 ? filename.slice(dot + 1).toLowerCase() : "bin";
    if (!/^[a-z0-9]{1,12}$/.test(extension)) {
      throw new Error(`Unsupported file extension: ${extension}`);
    }
    return extension;
  }
</script>

<div class="panel-heading">
  <h1 id="document-input-title">Document input</h1>
  <label class="file-picker">
    <span>Add documents</span>
    <input type="file" multiple onchange={addFiles} />
  </label>
</div>

{#if loading}
  <p role="status">Loading documents…</p>
{:else if loadError}
  <p role="alert" class="state-error">Could not load documents: {loadError}</p>
  <button type="button" onclick={() => { void loadDocuments(); }}>Retry loading documents</button>
{/if}

<DocumentList />
