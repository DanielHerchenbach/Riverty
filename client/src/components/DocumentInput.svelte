<script lang="ts">
  import { documents, type DocumentEntry } from "../lib/documents.svelte";
  import { hashFile } from "../lib/hash";
  import { analyzeDocument, uploadIfMissing } from "../lib/documentApi";
  import DocumentList from "./DocumentList.svelte";

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

      entry.state = "analyzing";
      entry.toc = await analyzeDocument(hash, ext);
      entry.state = "ready";
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

<DocumentList />
