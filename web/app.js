const storeKey = "shallwe.crm.overrides.v1";

const taxonomy = {
  personas: [
    "Founder / Operator",
    "AI Builder / Engineer",
    "Researcher / Academic",
    "Product / Business",
    "Investor / Ecosystem",
    "Student / Early Career",
    "Enterprise Leader",
    "Community / Media",
    "Unclassified"
  ],
  lifecycle: ["Prospect", "Member", "Active Member", "VIP / Champion", "Speaker Prospect", "Partner Prospect"],
  engagement: ["Cold", "Warm", "Hot", "Champion"],
  readiness: ["Ready", "Needs Review", "No Email", "Missing Consent"]
};

const segmentPresets = [
  {
    name: "Speaker Prospects",
    description: "Founders, researchers, senior leaders with strong engagement.",
    rule: c => ["Founder / Operator", "Researcher / Academic", "Enterprise Leader"].includes(c.persona) && c.score >= 5
  },
  {
    name: "AI Builder Workshop Audience",
    description: "Engineers, builders, vibe-coding users, agent/product interests.",
    rule: c => c.persona === "AI Builder / Engineer" || hasAny(c.interestList, ["agents", "coding", "product", "developer tools"])
  },
  {
    name: "Mandarin Community Core",
    description: "Mandarin-speaking active members for Chinese-language campaigns.",
    rule: c => c.mandarin_speaker && c.score >= 3
  },
  {
    name: "Sponsor / Partner Leads",
    description: "Investors, enterprise leaders, operators, and ecosystem contacts.",
    rule: c => ["Investor / Ecosystem", "Enterprise Leader", "Founder / Operator"].includes(c.persona)
  },
  {
    name: "Reactivation List",
    description: "Known contacts with low attendance or no check-in signal.",
    rule: c => c.lifecycle === "Prospect" || c.engagement === "Cold"
  }
];

let selectedId = null;
let activePreset = null;
let rawData = null;
let contacts = [];
let filtered = [];

function buildContacts(data) {
  const attendanceByContact = groupBy(data.attendance || [], a => Number(a.contact_id));
  const overrides = JSON.parse(localStorage.getItem(storeKey) || "{}");
  return (data.contacts || []).map(contact => {
    const attendance = attendanceByContact.get(Number(contact.id)) || [];
    const enriched = enrichContact(contact, attendance);
    return { ...enriched, ...(overrides[contact.id] || {}), attendance };
  });
}

function enrichContact(contact, attendance) {
  const interestList = splitList(contact.interests);
  const blob = [
    contact.full_name,
    contact.email,
    contact.organization,
    contact.role_title,
    contact.professional_category,
    contact.tags,
    contact.notes,
    contact.interests,
    ...attendance.flatMap(a => [a.motivation, a.questions_for_speakers, a.experience, a.event_name])
  ].filter(Boolean).join(" ").toLowerCase();
  const checkins = attendance.filter(a => value(a.checked_in_at)).length;
  const events = attendance.length;
  const score = events * 2 + checkins * 3 + (contact.linkedin ? 1 : 0) + (contact.tags ? 1 : 0);
  const persona = inferPersona(contact, blob);
  const lifecycle = inferLifecycle(persona, score, attendance, blob);
  const engagement = score >= 10 ? "Champion" : score >= 6 ? "Hot" : score >= 2 ? "Warm" : "Cold";
  const readiness = inferReadiness(contact, attendance);
  return {
    ...contact,
    email: (contact.email || "").toLowerCase(),
    displayName: contact.full_name || [contact.first_name, contact.last_name].filter(Boolean).join(" ") || "(No name)",
    interestList,
    persona,
    lifecycle,
    engagement,
    readiness,
    eventsCount: events,
    checkins,
    score
  };
}

function inferPersona(c, blob) {
  const cat = `${c.professional_category || ""} ${c.role_title || ""}`.toLowerCase();
  if (match(cat, ["founder", "co-founder", "ceo", "operator", "startup"])) return "Founder / Operator";
  if (match(cat, ["engineer", "developer", "software", "data scientist", "ml", "ai engineer", "technical"])) return "AI Builder / Engineer";
  if (match(cat, ["phd", "research", "professor", "academic", "scientist", "student researcher"])) return "Researcher / Academic";
  if (match(cat, ["product", "growth", "marketing", "business", "strategy", "sales", "bd"])) return "Product / Business";
  if (match(cat, ["investor", "vc", "venture", "angel", "accelerator", "ecosystem"])) return "Investor / Ecosystem";
  if (match(cat, ["student", "master", "undergraduate", "graduate"])) return "Student / Early Career";
  if (match(cat, ["director", "head of", "vp", "enterprise", "manager", "lead"])) return "Enterprise Leader";
  if (match(blob, ["community", "media", "content", "newsletter", "podcast"])) return "Community / Media";
  return "Unclassified";
}

function inferLifecycle(persona, score, attendance, blob) {
  if (score >= 10) return "VIP / Champion";
  if (match(blob, ["speaker", "panel", "talk", "keynote"])) return "Speaker Prospect";
  if (["Investor / Ecosystem", "Enterprise Leader"].includes(persona) && score >= 3) return "Partner Prospect";
  if (score >= 6) return "Active Member";
  if (attendance.length > 0) return "Member";
  return "Prospect";
}

function inferReadiness(c, attendance) {
  if (!value(c.email)) return "No Email";
  const declined = attendance.some(a => String(a.approval_status || "").toLowerCase().includes("declined"));
  if (declined) return "Needs Review";
  return "Ready";
}

function render() {
  applyFilters();
  renderKpis();
  renderCharts();
  renderContacts();
  renderSegments();
  renderProfile();
  document.getElementById("dataMode").textContent = window.SHALLWE_PRIVATE_DATA
    ? `Private dataset loaded: ${contacts.length} contacts`
    : "Sample data only. Run scripts/export_static_data.py for real data.";
}

function setupControls() {
  fillSelect("persona", ["All", ...taxonomy.personas]);
  fillSelect("lifecycle", ["All", ...taxonomy.lifecycle]);
  fillSelect("interest", ["All", ...topValues(contacts.flatMap(c => c.interestList), 80)]);
  fillSelect("engagement", ["All", ...taxonomy.engagement]);
  fillSelect("readiness", ["All", ...taxonomy.readiness]);
  ["search", "persona", "lifecycle", "interest", "engagement", "readiness"].forEach(id => {
    document.getElementById(id).addEventListener("input", () => {
      activePreset = null;
      render();
    });
  });
  document.querySelectorAll(".nav").forEach(btn => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });
  document.getElementById("exportCsv").addEventListener("click", exportCsv);
  document.getElementById("exportEmails").addEventListener("click", copyEmails);
}

function applyFilters() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const persona = val("persona");
  const lifecycle = val("lifecycle");
  const interest = val("interest");
  const engagement = val("engagement");
  const readiness = val("readiness");
  filtered = contacts.filter(c => {
    const haystack = [c.displayName, c.email, c.organization, c.role_title, c.professional_category, c.interests, c.tags, c.notes].filter(Boolean).join(" ").toLowerCase();
    return (!q || haystack.includes(q))
      && (persona === "All" || c.persona === persona)
      && (lifecycle === "All" || c.lifecycle === lifecycle)
      && (interest === "All" || c.interestList.includes(interest))
      && (engagement === "All" || c.engagement === engagement)
      && (readiness === "All" || c.readiness === readiness)
      && (!activePreset || activePreset.rule(c));
  });
}

function renderKpis() {
  const ready = filtered.filter(c => c.readiness === "Ready").length;
  const active = filtered.filter(c => ["Hot", "Champion"].includes(c.engagement)).length;
  const mandarin = filtered.filter(c => c.mandarin_speaker).length;
  const orgs = new Set(filtered.map(c => c.organization).filter(Boolean)).size;
  document.getElementById("kpis").innerHTML = [
    metric("Contacts", filtered.length),
    metric("Ready to email", ready),
    metric("Hot / Champion", active),
    metric("Mandarin", mandarin),
    metric("Organizations", orgs)
  ].join("");
}

function renderCharts() {
  renderBars("personaChart", countBy(filtered, c => c.persona), 9);
  renderBars("orgChart", countBy(filtered.filter(c => c.organization), c => c.organization), 12);
  const interests = countBy(filtered.flatMap(c => c.interestList), x => x);
  document.getElementById("interestChart").innerHTML = topEntries(interests, 30)
    .map(([name, count]) => `<button class="chip" data-interest="${escapeAttr(name)}">${escapeHtml(name)} <span>${count}</span></button>`)
    .join("");
  document.querySelectorAll("[data-interest]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById("interest").value = btn.dataset.interest;
      switchView("contacts");
      render();
    });
  });
  document.getElementById("segmentCards").innerHTML = segmentPresets.map(p => {
    const n = contacts.filter(p.rule).length;
    return `<button class="segment-card" data-segment="${escapeAttr(p.name)}"><strong>${escapeHtml(p.name)}</strong><span>${n} contacts</span><small>${escapeHtml(p.description)}</small></button>`;
  }).join("");
  document.querySelectorAll("[data-segment]").forEach(btn => {
    btn.addEventListener("click", () => {
      activePreset = segmentPresets.find(s => s.name === btn.dataset.segment);
      switchView("contacts");
      render();
    });
  });
}

function renderContacts() {
  document.getElementById("resultCount").textContent = `${filtered.length} contacts`;
  document.getElementById("activeRule").textContent = activePreset ? activePreset.name : "";
  document.getElementById("contactRows").innerHTML = filtered.slice(0, 500).map(c => `
    <tr data-id="${c.id}">
      <td><strong>${escapeHtml(c.displayName)}</strong><small>${escapeHtml(c.email)}</small></td>
      <td>${badge(c.persona)}</td>
      <td>${badge(c.lifecycle)}</td>
      <td>${escapeHtml(c.organization || "")}<small>${escapeHtml(c.role_title || "")}</small></td>
      <td>${c.interestList.slice(0, 4).map(t => `<span class="mini-chip">${escapeHtml(t)}</span>`).join("")}</td>
      <td><strong>${c.score}</strong><small>${c.eventsCount} events / ${c.checkins} check-ins</small></td>
      <td>${badge(c.readiness)}</td>
    </tr>
  `).join("");
  document.querySelectorAll("#contactRows tr").forEach(row => {
    row.addEventListener("click", () => {
      selectedId = Number(row.dataset.id);
      switchView("profile");
      renderProfile();
    });
  });
}

function renderSegments() {
  document.getElementById("savedSegments").innerHTML = segmentPresets.map(p => {
    const rows = contacts.filter(p.rule);
    const personas = topEntries(countBy(rows, c => c.persona), 4).map(([k, v]) => `${k}: ${v}`).join(" · ");
    return `<article class="panel segment-wide">
      <div><h2>${escapeHtml(p.name)}</h2><p>${escapeHtml(p.description)}</p><small>${escapeHtml(personas)}</small></div>
      <div><strong>${rows.length}</strong><button data-segment="${escapeAttr(p.name)}">Open</button></div>
    </article>`;
  }).join("");
  document.querySelectorAll("#savedSegments [data-segment]").forEach(btn => {
    btn.addEventListener("click", () => {
      activePreset = segmentPresets.find(s => s.name === btn.dataset.segment);
      switchView("contacts");
      render();
    });
  });
}

function renderProfile() {
  const pane = document.getElementById("profilePane");
  const c = contacts.find(x => x.id === selectedId);
  if (!c) {
    pane.className = "profile-empty";
    pane.textContent = "Select a contact from Contacts.";
    return;
  }
  pane.className = "profile";
  pane.innerHTML = `
    <section class="profile-main">
      <h2>${escapeHtml(c.displayName)}</h2>
      <p>${escapeHtml(c.email)} ${c.phone ? " · " + escapeHtml(c.phone) : ""}</p>
      <div class="badges">${badge(c.persona)}${badge(c.lifecycle)}${badge(c.engagement)}${badge(c.readiness)}</div>
      <dl>
        <dt>Organization</dt><dd>${escapeHtml(c.organization || "-")}</dd>
        <dt>Role</dt><dd>${escapeHtml(c.role_title || "-")}</dd>
        <dt>LinkedIn</dt><dd>${c.linkedin ? `<a href="${escapeAttr(c.linkedin)}" target="_blank" rel="noreferrer">${escapeHtml(c.linkedin)}</a>` : "-"}</dd>
        <dt>Interests</dt><dd>${c.interestList.map(t => `<span class="mini-chip">${escapeHtml(t)}</span>`).join("") || "-"}</dd>
      </dl>
      <label>Lifecycle
        <select id="editLifecycle">${taxonomy.lifecycle.map(x => `<option ${x === c.lifecycle ? "selected" : ""}>${x}</option>`).join("")}</select>
      </label>
      <label>Audience type
        <select id="editPersona">${taxonomy.personas.map(x => `<option ${x === c.persona ? "selected" : ""}>${x}</option>`).join("")}</select>
      </label>
      <label>Manual tags
        <input id="editTags" value="${escapeAttr(c.tags || "")}" />
      </label>
      <label>Notes
        <textarea id="editNotes">${escapeHtml(c.notes || "")}</textarea>
      </label>
      <button id="saveProfile" class="primary">Save local edits</button>
    </section>
    <section class="timeline">
      <h2>Timeline</h2>
      ${c.attendance.map(a => `<article>
        <strong>${escapeHtml(a.event_name || "Event")}</strong>
        <span>${escapeHtml(a.approval_status || "status n/a")} · ${escapeHtml(a.registered_at || "")}</span>
        <p>${escapeHtml(a.motivation || a.experience || "")}</p>
      </article>`).join("") || "<p>No attendance records.</p>"}
    </section>
  `;
  document.getElementById("saveProfile").addEventListener("click", () => saveProfile(c.id));
}

function saveProfile(id) {
  const overrides = JSON.parse(localStorage.getItem(storeKey) || "{}");
  overrides[id] = {
    lifecycle: document.getElementById("editLifecycle").value,
    persona: document.getElementById("editPersona").value,
    tags: document.getElementById("editTags").value,
    notes: document.getElementById("editNotes").value
  };
  localStorage.setItem(storeKey, JSON.stringify(overrides));
  rawData = window.SHALLWE_PRIVATE_DATA || window.SHALLWE_SAMPLE_DATA;
  contacts = buildContacts(rawData);
  selectedId = id;
  render();
}

function exportCsv() {
  const rows = filtered.map(c => ({
    Name: c.displayName,
    Email: c.email,
    "Audience Type": c.persona,
    Lifecycle: c.lifecycle,
    Engagement: c.engagement,
    Readiness: c.readiness,
    Organization: c.organization || "",
    Role: c.role_title || "",
    Interests: c.interestList.join("; "),
    Tags: c.tags || "",
    Notes: c.notes || ""
  }));
  const csv = toCsv(rows);
  download(`shallwe_segment_${rows.length}.csv`, csv, "text/csv;charset=utf-8");
}

async function copyEmails() {
  const emails = filtered.filter(c => c.readiness === "Ready").map(c => c.email).filter(Boolean).join("\n");
  await navigator.clipboard.writeText(emails);
  document.getElementById("exportEmails").textContent = `Copied ${emails ? emails.split("\n").length : 0}`;
  setTimeout(() => document.getElementById("exportEmails").textContent = "Copy Emails", 1200);
}

function switchView(id) {
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === id));
  document.querySelectorAll(".nav").forEach(n => n.classList.toggle("active", n.dataset.view === id));
}

function renderBars(id, counts, limit) {
  const entries = topEntries(counts, limit);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  document.getElementById(id).innerHTML = entries.map(([name, count]) => `
    <div class="bar-row"><span>${escapeHtml(name)}</span><div><i style="width:${Math.max(4, count / max * 100)}%"></i></div><b>${count}</b></div>
  `).join("");
}

function metric(label, value) {
  return `<article class="metric"><span>${label}</span><strong>${Number(value).toLocaleString()}</strong></article>`;
}

function badge(text) {
  return `<span class="badge">${escapeHtml(text || "")}</span>`;
}

function fillSelect(id, options) {
  document.getElementById(id).innerHTML = options.map(o => `<option>${escapeHtml(o)}</option>`).join("");
}

function val(id) {
  return document.getElementById(id).value;
}

function splitList(s) {
  return String(s || "").split(/[,;|]/).map(x => x.trim()).filter(Boolean);
}

function groupBy(arr, fn) {
  const map = new Map();
  arr.forEach(item => {
    const key = fn(item);
    map.set(key, [...(map.get(key) || []), item]);
  });
  return map;
}

function countBy(arr, fn) {
  const out = {};
  arr.forEach(item => {
    const key = fn(item);
    if (key) out[key] = (out[key] || 0) + 1;
  });
  return out;
}

function topEntries(obj, n) {
  return Object.entries(obj).sort((a, b) => b[1] - a[1]).slice(0, n);
}

function topValues(values, n) {
  return topEntries(countBy(values, x => x), n).map(([k]) => k);
}

function match(text, words) {
  return words.some(w => text.includes(w));
}

function hasAny(values, wanted) {
  const lower = values.map(v => v.toLowerCase());
  return wanted.some(w => lower.some(v => v.includes(w)));
}

function value(v) {
  return v !== undefined && v !== null && String(v).trim() !== "";
}

function toCsv(rows) {
  const headers = Object.keys(rows[0] || { Name: "", Email: "" });
  return [headers.join(","), ...rows.map(r => headers.map(h => csvCell(r[h])).join(","))].join("\n");
}

function csvCell(v) {
  return `"${String(v ?? "").replaceAll('"', '""')}"`;
}

function download(filename, content, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([content], { type }));
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function escapeAttr(s) {
  return escapeHtml(s);
}

function initApp() {
  rawData = window.SHALLWE_PRIVATE_DATA || window.SHALLWE_SAMPLE_DATA;
  contacts = buildContacts(rawData);
  filtered = contacts;
  setupControls();
  render();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    if (window.SHALLWE_DATA_LOADER_PRESENT) {
      window.addEventListener("shallwe:data-ready", initApp, { once: true });
    } else {
      initApp();
    }
  });
} else if (window.SHALLWE_DATA_LOADER_PRESENT) {
  window.addEventListener("shallwe:data-ready", initApp, { once: true });
} else {
  initApp();
}
