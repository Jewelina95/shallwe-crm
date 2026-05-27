import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const privateDataPath = path.join(root, "web", "data", "contacts.private.js");
const encryptedPath = path.join(root, "web", "data", "contacts.encrypted.json");
const passphrasePath = path.join(root, "web", "data", "private.passphrase.txt");

function b64(buf) {
  return Buffer.from(buf).toString("base64");
}

async function getPassphrase() {
  try {
    return (await fs.readFile(passphrasePath, "utf8")).trim();
  } catch {
    const passphrase = crypto.randomBytes(24).toString("base64url");
    await fs.writeFile(passphrasePath, passphrase + "\n", "utf8");
    return passphrase;
  }
}

const source = await fs.readFile(privateDataPath, "utf8");
const jsonText = source
  .replace(/^window\.SHALLWE_PRIVATE_DATA\s*=\s*/, "")
  .replace(/;\s*$/, "");
JSON.parse(jsonText);

const passphrase = await getPassphrase();
const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(passphrase, salt, 250000, 32, "sha256");
const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
const encrypted = Buffer.concat([cipher.update(jsonText, "utf8"), cipher.final()]);
const tag = cipher.getAuthTag();

await fs.writeFile(
  encryptedPath,
  JSON.stringify(
    {
      version: 1,
      kdf: "PBKDF2-SHA256",
      iterations: 250000,
      cipher: "AES-256-GCM",
      salt: b64(salt),
      iv: b64(iv),
      tag: b64(tag),
      data: b64(encrypted),
    },
    null,
    2
  ) + "\n",
  "utf8"
);

console.log(`Encrypted private CRM data: ${encryptedPath}`);
console.log(`Passphrase saved locally: ${passphrasePath}`);
