window.addEventListener("shallwe:data-ready", function () {
  const rawData = window.SHALLWE_PRIVATE_DATA || window.SHALLWE_SAMPLE_DATA;
  const dataMode = window.SHALLWE_PRIVATE_DATA ? "Using local private CRM export" : "Using sample data";
  const editsKey = "shallwe-crm-contact-edits-v1";
  const selectedKey = "shallwe-crm-selected-contact-v1";

  const state = {
    filters: {
      search: "",
      persona: "All",
      lifecycle: "All",
      interest: "All",
      engagement: "All",
      readiness: "All"
    },
    selectedId: Number(localStorage.getItem(selectedKey)) || null,
    contacts: [],
    filtered: []
  };

  const savedSegments = [
    {
      name: "Hot founder / operator leads",
      description: "Founders, operators, and product leaders who attended or checked in.",
      filters: { persona: "Founder / Operator", engagement: "Warm+" }
    },
    {
      name: "Research-heavy audience",
      description: "Researchers and technical builders for deep AI content.",
      filters: { persona: "Research / Technical", interest: "research" }
    },
    {
      name: "Mandarin-ready community",
      description: "Mandarin speakers with enough data to invite to Chinese-language events.",
      filters: { readiness: "Email-ready" },
      custom: c => c.mandarin_speaker === 1
    },
    {
      name: "Needs enrichment before email",
      description: "Contacts missing consent, names, or useful targeting fields.",
      filters: { readiness: "Needs enrichment" }
    }
  ];

  const els = {
    dataMode: document.getElementById("dataMode"),
    kpis: document.getElementById("kpis"),
    personaChart: document.getElementById("personaChart"),
    orgChart: document.getElementById("orgChart"),
    interestChart: document.getElementById("interestChart"),
    segmentCards: document.getElementById("segmentCards"),
    contactRows: document.getElementById("contactRows"),
    resultCount: document.getElementById("resultCount"),
    activeRule: document.getElementById("activeRule"),
    profilePane: document.getElementById("profilePane"),
    savedSegments: document.getElementById("savedSegments")
  };

  function savedEdits() {
    try {
      return JSON.parse(localStorage.getItem(editsKey) || "{}");
    } catch {
      return {};
    }
  }

  function saveEdit(id, patch) {
    const edits = savedEdits();
    edits[id] = { ...(edits[id] || {}), ...patch };
    localStorage.setItem(editsKey, JSON.stringify(edits));
  }

  function clean(value) {
    return String(value || "").trim();
  }

  function words(value) {
    return clean(value).toLowerCase();
  }

  function splitTags(value) {
    return clean(value)
      .split(",")
      .map(t => t.trim())
      .filter(Boolean);
  }

  function byContactAttendance() {
    const map = new Map();
    for (const row of rawData.attendance || []) {
      const id = Number(row.contact_id);
      if (!map.has(id)) map.set(id, []);
      map.get(id).push(row);
    }
    return map;
  }

  function inferPersona(c, attendanceText) {
    const blob = words([c.professional_category, c.role_title, c.organization, c.tags, c.interests, attendanceText].join(" "));
    if (/(founder|co-founder|ceo|cto|chief|startup|venture|investor|partner|vc|entrepreneur)/.test(blob)) return "Founder / Operator";
    if (/(phd|professor|research|scientist|university|academic|student|engineer|developer|machine learning|ai engineer|data scientist)/.test(blob)) return "Research / Technical";
    if (/(product|pm|manager|strategy|business|growth|marketing|community|operations|consultant)/.test(blob)) return "Product / Business";
    if (/(student|graduate|master|undergraduate)/.test(blob)) return "Student / Early Career";
    return "General Community";
  }

  function inferSeniority(c) {
    const blob = words([c.role_title, c.professional_category].join(" "));
    if (/(chief|founder|ceo|cto|cpo|vp|partner|director|head of|principal)/.test(blob)) return "Decision maker";
    if (/(manager|lead|senior|staff|consultant|product)/.test(blob)) return "Mid-senior";
    if (/(student|intern|graduate|junior|assistant)/.test(blob)) return "Early";
    return "Unknown";
  }

  function inferInterests(c, attendanceRows) {
    const seeded = splitTags(c.interests);
    const blob = words([
      c.role_title,
      c.organization,
      c.professional_category,
      c.tags,
      ...attendanceRows.flatMap(a => [a.motivation, a.questions_for_speakers, a.experience])
    ].join(" "));
    const rules = [
      ["agents", /(agent|workflow|automation|copilot|assistant)/],
      ["vibe coding", /(vibe|coding|developer|prototype|cursor|code)/],
      ["world models", /(world model|simulation|robot|spatial|embodied)/],
      ["research", /(research|paper|phd|academic|university|scientist|multimodal)/],
      ["product", /(product|startup|ship|market|user|growth|commercial)/],
      ["venture", /(invest|vc|fund|capital|venture|founder)/],
      ["community", /(community|network|meet|connect|event)/],
      ["career", /(career|job|student|learn|skill|mentor)/]
    ];
    const inferred = rules.filter(([, re]) => re.test(blob)).map(([tag]) => tag);
    return [...new Set([...seeded, ...inferred])];
  }

  function buildContacts() {
    const attendanceMap = byContactAttendance();
    const edits = savedEdits();
    state.contacts = (rawData.contacts || []).map(contact => {
      const c = { ...contact, ...(edits[contact.id] || {}) };
      const attendance = attendanceMap.get(Number(c.id)) || [];
      const attendanceText = attendance.map(a => [a.motivation, a.questions_for_speakers, a.experience].join(" ")).join(" ");
      const eventCount = attendance.length;
      const checkins = attendance.filter(a => clean(a.checked_in_at)).length;
      const hasLinkedIn = Boolean(clean(c.linkedin));
      const hasName = Boolean(clean(c.full_name || `${c.first_name || ""} ${c.last_name || ""}`));
      const interests = inferInterests(c, attendance);
      const persona = c.persona || inferPersona(c, attendanceText);
      const seniority = c.seniority || inferSeniority(c);
      const score = Math.min(100, eventCount * 18 + checkins * 22 + interests.length * 5 + (hasLinkedIn ? 8 : 0) + (seniority === "Decision maker" ? 12 : 0));
      const engagement = score >= 70 ? "Hot" : score >= 38 ? "Warm" : eventCount > 0 ? "Light" : "Cold";
      const lifecycle = c.lifecycle || (checkins > 0 ? "Attendee" : eventCount > 0 ? "Registered" : "Lead");
      const consent = c.consent || (eventCount > 0 ? "consented" : "unknown");
      const readiness = consent !== "unknown" && hasName && interests.length ? "Email-ready" : "Needs enrichment";
      return {
        ...c,
        attendance,
        eventCount,
        checkins,
        interestsList: interests,
        persona,
        seniority,
        score,
        engagement,
        lifecycle,
        consent,
        readiness,
        displayName: clean(c.full_name) || clean(`${c.first_name || ""} ${c.last_name || ""}`) || "(No name)"
      };
    });
  }

  function countBy(items, keyFn, limit = 10) {
    const counts = new Map();
    for (const item of items) {
      const key = keyFn(item);
      if (!key) continue;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit);
  }

  function filterContacts() {
    const f = state.filters;
    state.filtered = state.contacts.filter(c => {
      const haystack = words([c.displayName, c.email, c.organization, c.role_title, c.professional_category, c.interestsList.join(" "), c.tags].join(" "));
      if (f.search && !haystack.includes(f.search.toLowerCase())) return false;
      if (f.persona !== "All" && c.persona !== f.persona) return false;
      if (f.lifecycle !== "All" && c.lifecycle !== f.lifecycle) return false;
      if (f.interest !== "All" && !c.interestsList.includes(f.interest)) return false;
      if (f.engagement === "Warm+" && !["Warm", "Hot"].includes(c.engagement)) return false;
      if (!["All", "Warm+"].includes(f.engagement) && c.engagement !== f.engagement) return false;
      if (f.readiness !== "All" && c.readiness !== f.readiness) return false;
      return true;
    });
  }

  function fillSelect(id, options) {
    const el = document.getElementById(id);
    el.innerHTML = "";
    for (const option of options) {
      const node = document.createElement("option");
      node.value = option;
      node.textContent = option;
      el.appendChild(node);
    }
    el.addEventListener("change", () => {
      state.filters[id] = el.value;
      render();
    });
  }

  function setupControls() {
    document.getElementById("search").addEventListener("input", e => {
      state.filters.search = e.target.value;
      render();
    });
    fillSelect("persona", ["All", ...countBy(state.contacts, c => c.persona, 20).map(([k]) => k)]);
    fillSelect("lifecycle", ["All", "Lead", "Registered", "Attendee", "Partner", "Speaker prospect"]);
    const interests = [...new Set(state.contacts.flatMap(c => c.interestsList))].sort();
    fillSelect("interest", ["All", ...interests]);
    fillSelect("engagement", ["All", "Hot", "Warm+", "Warm", "Light", "Cold"]);
    fillSelect("readiness", ["All", "Email-ready", "Needs enrichment"]);
    document.querySelectorAll(".nav").forEach(button => {
      button.addEventListener("click", () => {
        document.querySelectorAll(".nav").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
        button.classList.add("active");
        document.getElementById(button.dataset.view).classList.add("active");
      });
    });
    document.getElementById("exportCsv").addEventListener("click", downloadCsv);
    document.getElementById("exportEmails").addEventListener("click", copyEmails);
  }

  function renderKpis() {
    const total = state.contacts.length;
    const emailReady = state.contacts.filter(c => c.readiness === "Email-ready").length;
    const hot = state.contacts.filter(c => c.engagement === "Hot").length;
    const attendees = state.contacts.filter(c => c.lifecycle === "Attendee").length;
    const mandarin = state.contacts.filter(c => c.mandarin_speaker === 1).length;
    els.kpis.innerHTML = [
      ["Contacts", total],
      ["Email-ready", emailReady],
      ["Hot leads", hot],
      ["Attendees", attendees],
      ["Mandarin", mandarin]
    ].map(([label, value]) => `<div class="kpi"><span>${label}</span><strong>${value.toLocaleString()}</strong></div>`).join("");
  }

  function renderBars(el, rows) {
    const max = Math.max(1, ...rows.map(([, n]) => n));
    el.innerHTML = rows.map(([label, n]) => `
      <div class="bar-row">
        <div class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.round((n / max) * 100)}%"></div></div>
        <strong>${n}</strong>
      </div>
    `).join("");
  }

  function renderDashboard() {
    renderKpis();
    renderBars(els.personaChart, countBy(state.contacts, c => c.persona, 8));
    renderBars(els.orgChart, countBy(state.contacts, c => clean(c.organization), 10));
    const interestRows = countBy(state.contacts.flatMap(c => c.interestsList), x => x, 30);
    els.interestChart.innerHTML = interestRows.map(([tag, n]) => `<span class="chip">${escapeHtml(tag)} <strong>${n}</strong></span>`).join("");
    els.segmentCards.innerHTML = savedSegments.map(segmentCardHtml).join("");
    wireSegmentButtons(els.segmentCards);
  }

  function segmentCardHtml(seg, index) {
    const count = state.contacts.filter(c => segmentMatches(c, seg)).length;
    return `
      <div class="segment-card">
        <div class="row"><strong>${escapeHtml(seg.name)}</strong><span class="score">${count}</span></div>
        <small>${escapeHtml(seg.description)}</small>
        <button data-segment="${index}">Apply segment</button>
      </div>
    `;
  }

  function segmentMatches(c, seg) {
    const old = state.filters;
    const trial = { ...old, search: "", persona: "All", lifecycle: "All", interest: "All", engagement: "All", readiness: "All", ...(seg.filters || {}) };
    const checks = [
      trial.persona === "All" || c.persona === trial.persona,
      trial.lifecycle === "All" || c.lifecycle === trial.lifecycle,
      trial.interest === "All" || c.interestsList.includes(trial.interest),
      trial.engagement === "All" || (trial.engagement === "Warm+" ? ["Warm", "Hot"].includes(c.engagement) : c.engagement === trial.engagement),
      trial.readiness === "All" || c.readiness === trial.readiness,
      !seg.custom || seg.custom(c)
    ];
    return checks.every(Boolean);
  }

  function wireSegmentButtons(scope) {
    scope.querySelectorAll("[data-segment]").forEach(button => {
      button.addEventListener("click", () => {
        const seg = savedSegments[Number(button.dataset.segment)];
        state.filters = { search: "", persona: "All", lifecycle: "All", interest: "All", engagement: "All", readiness: "All", ...(seg.filters || {}) };
        for (const [id, value] of Object.entries(state.filters)) {
          const input = document.getElementById(id);
          if (input) input.value = value;
        }
        document.querySelector('[data-view="contacts"]').click();
        render();
      });
    });
  }

  function renderContacts() {
    els.resultCount.textContent = `${state.filtered.length.toLocaleString()} of ${state.contacts.length.toLocaleString()} contacts`;
    els.activeRule.textContent = Object.entries(state.filters)
      .filter(([, v]) => v && v !== "All")
      .map(([k, v]) => `${k}: ${v}`)
      .join(" · ");
    els.contactRows.innerHTML = state.filtered.slice(0, 500).map(c => `
      <tr data-id="${c.id}">
        <td class="name-cell"><strong>${escapeHtml(c.displayName)}</strong><small>${escapeHtml(c.email || "")}</small></td>
        <td>${escapeHtml(c.persona)}<br><small class="muted">${escapeHtml(c.seniority)}</small></td>
        <td>${escapeHtml(c.lifecycle)}</td>
        <td>${escapeHtml(c.organization || "")}<br><small class="muted">${escapeHtml(c.role_title || "")}</small></td>
        <td>${c.interestsList.slice(0, 4).map(t => `<span class="chip">${escapeHtml(t)}</span>`).join(" ")}</td>
        <td class="score">${c.score}</td>
        <td class="${c.engagement === "Hot" ? "status-hot" : c.engagement === "Warm" ? "status-warm" : ""}">${escapeHtml(c.engagement)}<br><small class="muted">${escapeHtml(c.readiness)}</small></td>
      </tr>
    `).join("");
    els.contactRows.querySelectorAll("tr").forEach(row => {
      row.addEventListener("click", () => {
        state.selectedId = Number(row.dataset.id);
        localStorage.setItem(selectedKey, String(state.selectedId));
        renderProfile();
        document.querySelector('[data-view="profile"]').click();
      });
    });
  }

  function renderSegments() {
    els.savedSegments.innerHTML = savedSegments.map(segmentCardHtml).join("");
    wireSegmentButtons(els.savedSegments);
  }

  function renderProfile() {
    const c = state.contacts.find(x => Number(x.id) === Number(state.selectedId));
    if (!c) {
      els.profilePane.className = "profile-empty";
      els.profilePane.textContent = "Select a contact from Contacts.";
      return;
    }
    els.profilePane.className = "profile";
    els.profilePane.innerHTML = `
      <article class="profile-card">
        <div class="profile-title">
          <strong>${escapeHtml(c.displayName)}</strong>
          <span class="muted">${escapeHtml(c.email || "")}</span>
        </div>
        <dl>
          <dt>Persona</dt><dd>${escapeHtml(c.persona)}</dd>
          <dt>Lifecycle</dt><dd>${escapeHtml(c.lifecycle)}</dd>
          <dt>Engagement</dt><dd>${escapeHtml(c.engagement)} · ${c.score}</dd>
          <dt>Seniority</dt><dd>${escapeHtml(c.seniority)}</dd>
          <dt>Consent</dt><dd>${escapeHtml(c.consent)}</dd>
          <dt>Organization</dt><dd>${escapeHtml(c.organization || "")}</dd>
          <dt>Role</dt><dd>${escapeHtml(c.role_title || "")}</dd>
          <dt>LinkedIn</dt><dd>${c.linkedin ? `<a href="${escapeAttr(c.linkedin)}" target="_blank" rel="noreferrer">Open</a>` : ""}</dd>
        </dl>
        <div class="chips" style="margin-top:16px">${c.interestsList.map(t => `<span class="chip">${escapeHtml(t)}</span>`).join("")}</div>
        <div class="note-box">
          <label>Lifecycle
            <select id="editLifecycle">
              ${["Lead", "Registered", "Attendee", "Partner", "Speaker prospect"].map(x => `<option ${x === c.lifecycle ? "selected" : ""}>${x}</option>`).join("")}
            </select>
          </label>
          <label>Persona override
            <select id="editPersona">
              ${["Founder / Operator", "Research / Technical", "Product / Business", "Student / Early Career", "General Community"].map(x => `<option ${x === c.persona ? "selected" : ""}>${x}</option>`).join("")}
            </select>
          </label>
          <label>Notes
            <textarea id="editNotes" rows="5">${escapeHtml(c.notes || "")}</textarea>
          </label>
          <label>Manual tags
            <input id="editTags" value="${escapeAttr(c.tags || "")}" />
          </label>
          <button id="saveProfile" class="primary">Save locally</button>
        </div>
      </article>
      <article class="profile-card">
        <h2>Event Timeline</h2>
        <div class="timeline">
          ${c.attendance.length ? c.attendance.map(a => `
            <div class="timeline-item">
              <strong>${escapeHtml(a.event_name || "")}</strong>
              <div class="muted">${escapeHtml(a.registered_at || "")} · ${escapeHtml(a.approval_status || "")}</div>
              <p>${escapeHtml(a.motivation || a.experience || "")}</p>
            </div>
          `).join("") : '<p class="muted">No event history.</p>'}
        </div>
      </article>
    `;
    document.getElementById("saveProfile").addEventListener("click", () => {
      saveEdit(c.id, {
        lifecycle: document.getElementById("editLifecycle").value,
        persona: document.getElementById("editPersona").value,
        notes: document.getElementById("editNotes").value,
        tags: document.getElementById("editTags").value
      });
      buildContacts();
      render();
    });
  }

  function render() {
    filterContacts();
    renderDashboard();
    renderContacts();
    renderSegments();
    renderProfile();
  }

  function downloadCsv() {
    const headers = ["Name", "Email", "Persona", "Lifecycle", "Engagement", "Score", "Readiness", "Organization", "Role", "Interests", "Events", "Notes", "Tags"];
    const rows = state.filtered.map(c => [
      c.displayName, c.email, c.persona, c.lifecycle, c.engagement, c.score, c.readiness, c.organization, c.role_title, c.interestsList.join("; "), c.eventCount, c.notes, c.tags
    ]);
    const csv = [headers, ...rows].map(row => row.map(csvCell).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `shallwe-audience-${state.filtered.length}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function copyEmails() {
    const emails = state.filtered.map(c => c.email).filter(Boolean).join("\n");
    await navigator.clipboard.writeText(emails);
    const button = document.getElementById("exportEmails");
    const old = button.textContent;
    button.textContent = `Copied ${state.filtered.length}`;
    setTimeout(() => (button.textContent = old), 1200);
  }

  function csvCell(value) {
    return `"${String(value || "").replaceAll('"', '""')}"`;
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, ch => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[ch]);
  }

  function escapeAttr(value) {
    return escapeHtml(value).replaceAll("`", "&#96;");
  }

  els.dataMode.textContent = dataMode;
  buildContacts();
  setupControls();
  render();
});
