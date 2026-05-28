import { createClient } from "/Users/nadaraya/.npm-global/lib/node_modules/notebooklm/dist/index.js";

const notebookId = process.argv[2];
if (!notebookId) {
  console.error("Usage: node scripts/test_notebooklm_notebook.mjs <notebookId>");
  process.exit(1);
}

const client = await createClient();
console.log("Notebook info:");
console.log(await client.notebooks.get(notebookId));

console.log("Sources:");
console.log(await client.sources.list(notebookId));

console.log("Ask:");
console.log(await client.chat.ask(notebookId, "Кратко: о чем эта база знаний? Ответь в 3 пунктах."));
