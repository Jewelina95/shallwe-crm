(async function () {
  try {
    const response = await fetch("data/contacts.private.js", { cache: "no-store" });
    if (response.ok) {
      const source = await response.text();
      Function(source)();
    }
  } catch {
    // GitHub Pages uses sample data; local private exports load when present.
  } finally {
    window.dispatchEvent(new Event("shallwe:data-ready"));
  }
})();
