import { createClient } from "/Users/nadaraya/.npm-global/lib/node_modules/notebooklm/dist/index.js";

const client = await createClient();
const notebooks = await client.notebooks.list();
for (const nb of notebooks) {
  console.log(JSON.stringify({
    id: nb.id,
    title: nb.title,
    sourceCount: nb.sourceCount ?? null,
    updatedAt: nb.updatedAt ?? null,
  }));
}
