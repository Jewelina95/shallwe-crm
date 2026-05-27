(async function () {
  window.SHALLWE_DATA_LOADER_PRESENT = true;
  try {
    const response = await fetch("data/contacts.private.js", { cache: "no-store" });
    if (response.ok) {
      const source = await response.text();
      Function(source)();
      window.dispatchEvent(new Event("shallwe:data-ready"));
      return;
    }
  } catch {
    // Local private exports load when present.
  }

  try {
    const response = await fetch("data/contacts.encrypted.json", { cache: "no-store" });
    if (response.ok) {
      showUnlock(await response.json());
      return;
    }
  } catch {
    // Public demo fallback.
  }

  window.dispatchEvent(new Event("shallwe:data-ready"));
})();

function showUnlock(encrypted) {
  const overlay = document.createElement("div");
  overlay.className = "unlock-overlay";
  overlay.innerHTML = `
    <form class="unlock-box">
      <strong>Private CRM Data</strong>
      <p>Enter the passphrase to decrypt all ShallWe Tech contacts in this browser.</p>
      <input type="password" id="unlockPassphrase" autocomplete="current-password" placeholder="Passphrase" />
      <button class="primary" type="submit">Unlock CRM</button>
      <span id="unlockStatus"></span>
    </form>
  `;
  document.body.appendChild(overlay);
  overlay.querySelector("form").addEventListener("submit", async event => {
    event.preventDefault();
    const status = overlay.querySelector("#unlockStatus");
    status.textContent = "Decrypting...";
    try {
      const passphrase = overlay.querySelector("#unlockPassphrase").value;
      window.SHALLWE_PRIVATE_DATA = await decryptPayload(encrypted, passphrase);
      overlay.remove();
      window.dispatchEvent(new Event("shallwe:data-ready"));
    } catch {
      status.textContent = "Wrong passphrase or corrupted data.";
    }
  });
}

async function decryptPayload(payload, passphrase) {
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  const key = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: fromBase64(payload.salt), iterations: payload.iterations, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"]
  );
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: fromBase64(payload.iv), tagLength: 128 },
    key,
    concatBytes(fromBase64(payload.data), fromBase64(payload.tag))
  );
  return JSON.parse(new TextDecoder().decode(plaintext));
}

function fromBase64(value) {
  return Uint8Array.from(atob(value), c => c.charCodeAt(0));
}

function concatBytes(a, b) {
  const out = new Uint8Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
}
