<script lang="ts">
  import { documents, type DocumentEntry } from "../lib/documents.svelte";
  import { hashFile } from "../lib/hash";
  import DocumentList from "./DocumentList.svelte";

  function addFiles(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = "";
    for (const file of files) {
      const entry: DocumentEntry = { path: file.name, state: "hashing" };
      documents.push(entry);
      calculateHash(entry, file);
    }
  }

  async function calculateHash(entry: DocumentEntry, file: File) {
    try {
      entry.hash = await hashFile(file);
      entry.state = "ready";
    } catch {
      entry.state = "error";
    }
  }
</script>

<div class="panel-heading">
  <h1 id="document-input-title">Document input</h1>
  <label class="file-picker">
    <span>Add documents</span>
    <input type="file" multiple onchange={addFiles} />
  </label>
</div>

<DocumentList />
