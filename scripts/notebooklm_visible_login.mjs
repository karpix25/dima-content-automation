import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { homedir } from "node:os";
import { chromium } from "playwright";

const storagePath = process.env.NOTEBOOKLM_STORAGE_PATH || join(homedir(), ".notebooklm", "storage-state.json");
const profileDir = process.env.NOTEBOOKLM_LOGIN_PROFILE || join(homedir(), ".notebooklm", "playwright-profile");

await mkdir(dirname(storagePath), { recursive: true });
await mkdir(profileDir, { recursive: true });

const context = await chromium.launchPersistentContext(profileDir, {
  headless: false,
  args: ["--disable-blink-features=AutomationControlled"],
  userAgent:
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
});

const page = context.pages()[0] || (await context.newPage());
await page.goto("https://notebooklm.google.com", { waitUntil: "domcontentloaded" });

console.log("Opened visible browser for NotebookLM login.");
console.log("Log in there, wait until NotebookLM home page is visible, then press Enter here.");

process.stdin.resume();
process.stdin.setEncoding("utf8");
process.stdin.once("data", async () => {
  const url = page.url();
  if (!url.includes("notebooklm.google.com") || url.includes("accounts.google.com")) {
    console.error(`Login does not look complete. Current URL: ${url}`);
    await context.close();
    process.exit(1);
  }
  await context.storageState({ path: storagePath });
  console.log(`Saved NotebookLM auth state to ${storagePath}`);
  await context.close();
  process.exit(0);
});
