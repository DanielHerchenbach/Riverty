<script lang="ts">
  import { documents, type DocumentEntry } from "../lib/documents.svelte";
  import { hashFile } from "../lib/hash";
  import DocumentList from "./DocumentList.svelte";

  let isHashing = $state(false);

  async function addFiles(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    isHashing = true;

    try {
      for (const file of files) {
        const entry: DocumentEntry = { path: file.name, hash: await hashFile(file) };
        if (!documents.some((document) => document.hash === entry.hash)) {
          documents.push(entry);
        }
      }
    } finally {
      isHashing = false;
      input.value = "";
    }
  }
</script>

<div class="panel-heading">
  <h1 id="document-input-title">Document input</h1>
  <label class="file-picker">
    <span>{isHashing ? "Hashing…" : "Add documents"}</span>
    <input type="file" multiple onchange={addFiles} disabled={isHashing} />
  </label>
</div>

<DocumentList />
