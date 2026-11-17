(() => {
  const form = document.getElementById("disease-search-form");
  const search = document.getElementById("disease-search");
  const list = document.getElementById("disease-list");
  const detail = document.getElementById("disease-detail");
  const message = document.getElementById("disease-message");
  const count = document.getElementById("disease-result-count");

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function appendTextSection(parent, title, value) {
    if (!value) return;
    const section = el("section", "detail-section");
    section.append(el("h3", "", title), el("p", "", value));
    parent.append(section);
  }

  function appendListSection(parent, title, values) {
    if (!Array.isArray(values) || values.length === 0) return;
    const section = el("section", "detail-section");
    section.append(el("h3", "", title));
    const listNode = el("ul");
    values.forEach((value) => listNode.append(el("li", "", value)));
    section.append(listNode);
    parent.append(section);
  }

  function safeSourceUrl(value) {
    if (!value) return null;
    try {
      const parsed = new URL(value);
      return ["https:", "http:"].includes(parsed.protocol) ? parsed.href : null;
    } catch {
      return null;
    }
  }

  function renderDisease(disease) {
    detail.replaceChildren();
    const heading = el("header", "detail-heading");
    heading.append(el("h2", "", disease.name || "Disease information"));
    if (disease.last_updated) heading.append(el("p", "", `Last updated: ${disease.last_updated}`));
    detail.append(heading);
    appendTextSection(detail, "Definition", disease.simple_definition);
    if (disease.medical_definition && disease.medical_definition !== disease.simple_definition) {
      appendTextSection(detail, "Medical definition", disease.medical_definition);
    }
    appendListSection(detail, "Common symptoms", disease.common_symptoms);
    appendListSection(detail, "Possible causes", disease.possible_causes);
    appendListSection(detail, "Risk factors", disease.risk_factors);
    appendListSection(detail, "General prevention", disease.general_prevention);
    appendListSection(detail, "Common diagnostic tests", disease.common_diagnostic_tests);
    appendTextSection(detail, "General information", disease.general_treatment);
    appendTextSection(detail, "Warning signs", disease.warning_signs);
    appendTextSection(detail, "When professional care may be appropriate", disease.when_to_seek_doctor);

    if (disease.source || disease.source_url) {
      const source = el("section", "detail-section detail-source");
      source.append(el("h3", "", "Source information"));
      if (disease.source) source.append(el("p", "", disease.source));
      const href = safeSourceUrl(disease.source_url);
      if (href) {
        const link = el("a", "", "Open source reference");
        link.href = href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        source.append(link);
      }
      detail.append(source);
    }
  }

  async function selectDisease(disease, selectedButton) {
    document.querySelectorAll(".library-result-button").forEach((button) => button.setAttribute("aria-current", "false"));
    selectedButton?.setAttribute("aria-current", "true");
    try {
      const full = await window.HealthBridge.apiRequest(`/diseases/${encodeURIComponent(disease.id)}`);
      renderDisease(full);
    } catch (error) {
      window.HealthBridge.showMessage(message, error.message || "Disease information could not be loaded.");
    }
  }

  function renderList(diseases) {
    list.replaceChildren();
    count.textContent = `${diseases.length} ${diseases.length === 1 ? "condition" : "conditions"}`;
    if (!diseases.length) {
      list.append(el("p", "inline-status", "No supported conditions matched that search."));
      detail.replaceChildren(el("div", "empty-detail", "Try another condition or symptom."));
      return;
    }

    diseases.forEach((disease, index) => {
      const button = el("button", "library-result-button");
      button.type = "button";
      button.setAttribute("aria-current", "false");
      button.append(el("strong", "", disease.name || "Condition"));
      button.append(el("span", "", disease.simple_definition || "Condition information"));
      button.addEventListener("click", () => selectDisease(disease, button));
      list.append(button);
      if (index === 0) selectDisease(disease, button);
    });
  }

  async function searchDiseases(query) {
    window.HealthBridge.showMessage(message, "Searching the disease library...", "info");
    try {
      const result = await window.HealthBridge.apiRequest(`/diseases${query ? `?q=${encodeURIComponent(query)}` : ""}`);
      if (!Array.isArray(result)) throw new Error("The disease response was not in the expected format.");
      window.HealthBridge.showMessage(message, "", "info");
      renderList(result);
    } catch (error) {
      window.HealthBridge.showMessage(message, error.message || "Disease information could not be loaded.");
      count.textContent = "";
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    searchDiseases(search.value.trim());
  });
  searchDiseases("");
})();
