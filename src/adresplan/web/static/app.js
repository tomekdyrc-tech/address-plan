"use strict";
let editGeneration = 0;
let savedGeneration = 0;
let previewGeneration = null;
let projectRequests = 0;

function previewControls() {
  const button = document.querySelector('#apply-preview button[type="submit"]');
  if (!button) return;
  const current = previewGeneration === editGeneration && projectRequests === 0;
  button.disabled = !current;
  document.querySelector("#preview-status").textContent = current
    ? "Podgląd jest aktualny. Możesz zatwierdzić zmiany."
    : "Trwa przeliczanie lub dane wymagają poprawy. Zatwierdzenie będzie dostępne po aktualizacji podglądu.";
}

// HTMX replaces results only during ordinary edits; inputs retain focus and pending changes.
document.addEventListener("htmx:configRequest", (event) => {
  event.detail.headers["X-CSRF-Token"] = document.querySelector('meta[name="csrf-token"]').content;
  const form = event.detail.elt.closest("#project-form");
  if (form) {
    event.detail.parameters.revision = form.elements.revision.value;
    if (form.elements.ipv6_usage.value !== form.dataset.ipv6Usage &&
        (!event.detail.parameters.action || event.detail.parameters.action === "save")) {
      event.detail.parameters.action = "ipv6-toggle";
    }
  }
});

document.addEventListener("htmx:beforeRequest", (event) => {
  const form = event.detail.elt.closest("#project-form");
  if (!form) return;
  event.detail.xhr.editGeneration = editGeneration;
  projectRequests += 1;
  previewControls();
  const badge = document.querySelector("#save-status");
  if (badge) badge.textContent = "Zapisywanie…";
  const action = event.detail.requestConfig.parameters.action;
  if (action && action !== "save") {
    form.dataset.locked = "true";
    form.querySelectorAll("input,select,textarea,button").forEach((input) => { input.disabled = true; });
  }
});

document.addEventListener("htmx:beforeSwap", (event) => {
  const xhr = event.detail.xhr;
  if ([409, 422].includes(xhr.status)) {
    event.detail.shouldSwap = true;
    event.detail.isError = false;
  }
  const revision = Number(xhr.getResponseHeader("X-Project-Revision"));
  const current = document.querySelector('#project-form input[name="revision"]');
  if (revision && current && revision < Number(current.value)) {
    event.detail.shouldSwap = false;
    return;
  }
  if (revision && current && xhr.status === 200) current.value = String(revision);
});

document.addEventListener("htmx:afterRequest", (event) => {
  if (event.detail.xhr.editGeneration === undefined) return;
  projectRequests = Math.max(0, projectRequests - 1);
  const form = document.querySelector("#project-form");
  if (!form) return;
  if (form.dataset.locked) {
    form.querySelectorAll("input,select,textarea,button").forEach((input) => { input.disabled = false; });
    delete form.dataset.locked;
  }
  const badge = document.querySelector("#save-status");
  if (event.detail.xhr.status === 200) {
    const preview = event.detail.xhr.getResponseHeader("X-Plan-Preview") === "1";
    previewGeneration = preview ? event.detail.xhr.editGeneration : null;
    if (!preview) savedGeneration = event.detail.xhr.editGeneration ?? savedGeneration;
    if (badge) badge.textContent = preview ? "Podgląd — niezapisane zmiany" : editGeneration > savedGeneration
      ? "Oczekuje na zapis…" : `Zapisano · wersja ${form.elements.revision.value}`;
    const title = document.querySelector(".tree-root")?.textContent;
    if (title) {
      document.querySelector("h1").textContent = title;
      document.title = `${title} · Address Plan`;
    }
  } else {
    previewGeneration = null;
    if (badge) badge.textContent = "Nie zapisano — sprawdź komunikat poniżej";
  }
  previewControls();
});

function pendingEdit(event) {
  const form = event.target.closest("#project-form");
  if (!form) return;
  editGeneration += 1;
  previewControls();
  const badge = document.querySelector("#save-status");
  if (badge) badge.textContent = "Oczekuje na zapis…";
}
document.addEventListener("change", pendingEdit);
document.addEventListener("input", pendingEdit);
window.addEventListener("beforeunload", (event) => {
  if (editGeneration > savedGeneration) {
    event.preventDefault();
    event.returnValue = "";
  }
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-confirm]");
  if (button && !window.confirm(button.dataset.confirm)) {
    event.preventDefault();
    event.stopPropagation();
  }
}, true);

document.addEventListener("click", (event) => {
  const link = event.target.closest("[data-focus-field]");
  if (!link) return;
  const field = document.querySelector("#project-form")?.elements.namedItem(link.dataset.focusField);
  if (!field || field.disabled) return;
  event.preventDefault();
  if (field.closest("tr")?.hidden) clearStructureFilter();
  let parent = field.parentElement;
  while (parent) {
    if (parent.tagName === "DETAILS") parent.open = true;
    parent = parent.parentElement;
  }
  field.focus();
  field.scrollIntoView({block: "center"});
});

function parentChoices() {
  const form = document.querySelector("#project-form");
  if (!form) return;
  const kind = form.elements.new_kind;
  const parent = form.elements.new_parent;
  const update = () => {
    const wanted = kind.value === "building" ? "site" : "building";
    for (const option of parent.options) {
      option.disabled = option.dataset.kind !== wanted;
      option.hidden = option.disabled;
    }
    if (!parent.selectedOptions.length || parent.selectedOptions[0].disabled) {
      parent.value = [...parent.options].find((o) => !o.disabled)?.value || "";
    }
    parent.disabled = kind.value === "site";
    form.querySelectorAll("[data-new-segment]").forEach((label) => {
      label.hidden = kind.value !== "segment";
      label.querySelector("input").disabled = label.hidden;
    });
    const names = {segment: "Nowy segment", building: "Nowy budynek", site: "Nowa lokalizacja"};
    if (Object.values(names).includes(form.elements.new_name.value)) form.elements.new_name.value = names[kind.value];
  };
  if (!kind.dataset.parentChoicesBound) {
    kind.addEventListener("change", update);
    kind.dataset.parentChoicesBound = "true";
  }
  update();
}
document.addEventListener("DOMContentLoaded", parentChoices);
document.addEventListener("htmx:afterSwap", parentChoices);
document.addEventListener("htmx:afterRequest", parentChoices);

function ipv6Controls() {
  const form = document.querySelector("#project-form");
  if (!form || form.dataset.locked) return;
  const choice = form.elements.ipv6_usage;
  const update = () => form.querySelectorAll("[data-ipv6]").forEach((panel) => {
    panel.hidden = choice.value !== "yes";
    panel.querySelectorAll("input,select,button").forEach((input) => { input.disabled = panel.hidden; });
  });
  if (!choice.dataset.bound) {
    choice.addEventListener("change", update);
    choice.dataset.bound = "true";
  }
  update();
}
document.addEventListener("DOMContentLoaded", ipv6Controls);
document.addEventListener("htmx:afterSwap", ipv6Controls);
document.addEventListener("htmx:afterRequest", ipv6Controls);

function applyStructureFilter() {
  const panel = document.querySelector("#view-filters");
  if (!panel) return;
  const query = panel.querySelector("#structure-query").value.trim().toLocaleLowerCase("pl");
  const scope = panel.querySelector("#structure-scope").value;
  const visible = new Set();
  document.querySelectorAll("[data-filter-node]").forEach((row) => {
    const inside = !scope || row.dataset.filterScope.split(" ").includes(scope);
    row.hidden = !inside || !row.dataset.filterSearch.toLocaleLowerCase("pl").includes(query);
    if (!row.hidden) visible.add(row.dataset.filterNode);
  });
  document.querySelectorAll("[data-filter-detail]").forEach((row) => { row.hidden = !visible.has(row.dataset.filterDetail); });
  document.querySelectorAll("[data-filter-result]").forEach((row) => { row.hidden = !visible.has(row.dataset.filterResult); });
  panel.querySelector("#filter-status").textContent = `Widoczne elementy: ${visible.size}. Filtr zmienia tylko widok; wszystkie dane są zachowywane przy zapisie.`;
  try { sessionStorage.setItem(`address-plan-view-${panel.dataset.projectKey}`, JSON.stringify({query,scope})); } catch {}
}
function clearStructureFilter() {
  const query = document.querySelector("#structure-query");
  if (!query) return;
  query.value = "";
  document.querySelector("#structure-scope").value = "";
  applyStructureFilter();
}
function bindStructureFilter() {
  const panel = document.querySelector("#view-filters");
  if (!panel) return;
  const rows = new Map([...document.querySelectorAll("[data-filter-node]")]
    .map((row) => [row.dataset.filterNode, row]));
  const details = new Map([...document.querySelectorAll("[data-filter-detail]")]
    .map((row) => [row.dataset.filterDetail, row]));
  const labels = new Map();
  document.querySelectorAll("[data-derived-node]").forEach((data) => {
    labels.set(data.dataset.derivedNode, data.dataset.label);
    const row = rows.get(data.dataset.derivedNode);
    if (row) {
      row.dataset.filterSearch = data.dataset.search;
      row.dataset.filterScope = data.dataset.scope;
    }
    const detail = details.get(data.dataset.derivedNode);
    if (detail) {
      detail.querySelector("summary").textContent = `${data.dataset.name} · przypięcia i ustawienia szczegółowe`;
      const explanation = detail.querySelector("[data-sizing-explanation]");
      if (explanation) explanation.textContent = data.dataset.explanation;
    }
  });
  panel.querySelectorAll("#structure-scope option[value]").forEach((option) => {
    if (labels.has(option.value)) option.textContent = labels.get(option.value);
  });
  if (!panel.dataset.bound) {
    try {
      const state = JSON.parse(sessionStorage.getItem(`address-plan-view-${panel.dataset.projectKey}`) || "{}");
      panel.querySelector("#structure-query").value = state.query || "";
      panel.querySelector("#structure-scope").value = state.scope || "";
    } catch {}
    panel.addEventListener("input", applyStructureFilter);
    panel.addEventListener("change", applyStructureFilter);
    panel.querySelector("#clear-structure-filter").addEventListener("click", clearStructureFilter);
    panel.querySelector("#planning-choice").addEventListener("change", (event) => {
      document.querySelector("#project-form").elements.planning_mode.value = event.target.value;
      reviewControls();
    });
    panel.dataset.bound = "true";
  }
  applyStructureFilter();
  const draft = document.querySelector("#project-form")?.elements.draft_document.value;
  panel.querySelector("#planning-choice").disabled = !!draft;
  panel.querySelector("#planning-choice").value = document.querySelector("#project-form")?.elements.planning_mode.value || "auto";
  reviewControls();
}
function reviewControls() {
  const form = document.querySelector("#project-form");
  if (!form || form.dataset.locked) return;
  const reviewing = form.elements.planning_mode.value === "review";
  form.querySelectorAll('button[value^="template-save:"],button[value^="site-template-save:"]').forEach((button) => {
    button.disabled = reviewing;
    button.title = reviewing ? "Zatwierdź podgląd przed zapisaniem szablonu" : "";
  });
}
document.addEventListener("DOMContentLoaded", bindStructureFilter);
document.addEventListener("htmx:afterSwap", bindStructureFilter);
document.addEventListener("htmx:afterRequest", reviewControls);
document.addEventListener("submit", (event) => {
  if (event.target.id === "project-form") pendingEdit(event);
  if (event.target.id === "apply-preview") {
    if (previewGeneration !== editGeneration || projectRequests !== 0) {
      event.preventDefault();
      previewControls();
    } else savedGeneration = editGeneration;
  }
}, true);
document.addEventListener("click", (event) => {
  const discard = event.target.closest("[data-discard-preview]");
  if (discard) { savedGeneration = editGeneration; window.location.assign(discard.dataset.discardPreview); }
});

function templatePreview() {
  const select = document.querySelector("#building-template-choice");
  if (!select) return;
  const update = () => {
    document.querySelector("#building-template-description").textContent = select.selectedOptions[0]?.dataset.description || "";
  };
  if (!select.dataset.bound) {
    select.addEventListener("change", update);
    select.dataset.bound = "true";
  }
  update();
}
document.addEventListener("DOMContentLoaded", templatePreview);
document.addEventListener("htmx:afterSwap", templatePreview);

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#calculator-form");
  if (!form) return;
  const mode = form.elements.mode;
  const panels = () => form.querySelectorAll("[data-calc-panel]").forEach((panel) => {
    panel.hidden = !panel.dataset.calcPanel.split(" ").includes(mode.value);
    panel.querySelectorAll("input,button").forEach((input) => { input.disabled = panel.hidden; });
  });
  mode.addEventListener("change", panels);
  panels();
  const rows = form.querySelector("#vlsm-rows");
  const updateRows = () => {
    const all = rows.querySelectorAll(".vlsm-row");
    all.forEach((row) => { row.querySelector("[data-remove-subnet]").disabled = all.length === 1; });
    document.querySelector("#add-subnet").disabled = all.length >= 128;
  };
  document.querySelector("#add-subnet").addEventListener("click", () => {
    if (rows.children.length >= 128) return;
    const row = rows.firstElementChild.cloneNode(true);
    row.querySelector('[name="subnet_name"]').value = "";
    row.querySelector('[name="subnet_hosts"]').value = "10";
    rows.append(row);
    updateRows();
    row.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    if (!event.target.closest("[data-remove-subnet]") || rows.children.length <= 1) return;
    event.target.closest(".vlsm-row").remove();
    updateRows();
  });
  mode.addEventListener("change", updateRows);
  updateRows();
});

document.addEventListener("keydown", (event) => {
  const form = event.target.closest("#project-form");
  if (!form || event.isComposing) return;
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "d") {
    let row = event.target.closest("tr");
    if (row?.classList.contains("detail-row")) row = row.previousElementSibling;
    const duplicate = row?.querySelector('button[value^="duplicate:"]');
    if (duplicate && !duplicate.disabled) {
      event.preventDefault();
      duplicate.click();
    }
    return;
  }
  if (event.key === "Enter" && event.target.matches("input,select") &&
      !event.ctrlKey && !event.metaKey && !event.altKey) {
    event.preventDefault();
    const fields = [...form.querySelectorAll('input:not([type="hidden"]),select')]
      .filter((field) => !field.disabled && field.getClientRects().length);
    const next = fields[fields.indexOf(event.target) + (event.shiftKey ? -1 : 1)];
    next?.focus();
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  try {
    await navigator.clipboard.writeText(button.dataset.copy);
    document.querySelector("#copy-status").textContent = `Skopiowano ${button.dataset.copy}`;
  } catch {
    document.querySelector("#copy-status").textContent = "Nie udało się skopiować. Zaznacz adres i użyj Ctrl+C.";
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const zoom = document.querySelector("#diagram-zoom");
  if (zoom) zoom.addEventListener("change", () => {
    document.querySelector("#address-diagram").classList.toggle("diagram-fit", zoom.value === "fit");
  });
  const choice = document.querySelector("#theme-choice");
  let selected = "auto";
  try { selected = localStorage.getItem("address-plan-theme") || "auto"; } catch {}
  if (!["auto", "light", "dark"].includes(selected)) selected = "auto";
  choice.value = selected;
  const system = matchMedia("(prefers-color-scheme: dark)");
  const apply = () => {
    document.documentElement.dataset.theme = choice.value === "auto"
      ? (system.matches ? "dark" : "light") : choice.value;
  };
  choice.addEventListener("change", () => {
    try { localStorage.setItem("address-plan-theme", choice.value); } catch {}
    apply();
  });
  system.addEventListener("change", apply);
  apply();
  const printButton = document.querySelector("#print-button");
  if (printButton) {
    document.querySelectorAll(".print-report details:not(.technical-details)").forEach((detail) => { detail.open = true; });
    printButton.addEventListener("click", () => window.print());
  }
});
