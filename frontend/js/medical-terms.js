(() => {
  const form = document.getElementById("term-search-form");
  const search = document.getElementById("term-search");
  const list = document.getElementById("term-list");
  const detail = document.getElementById("term-detail");
  const message = document.getElementById("term-message");
  const count = document.getElementById("term-result-count");

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

  function renderTerm(term) {
    detail.replaceChildren();
    const heading = el("header", "detail-heading");
    heading.append(el("h2", "", term.term || "Medical term"));
    if (term.category) heading.append(el("p", "", term.category));
    detail.append(heading);
    appendTextSection(detail, "Medical definition", term.medical_definition);
    appendTextSection(detail, "Simple explanation", term.simple_explanation);
    appendTextSection(detail, "Very simple explanation", term.very_simple_explanation);

    const translations = [];
    if (term.tamil_explanation) translations.push({ language: "Tamil", explanation: term.tamil_explanation });
    if (term.hindi_explanation) translations.push({ language: "Hindi", explanation: term.hindi_explanation });
    if (translations.length) {
      const section = el("section", "detail-section");
      section.append(el("h3", "", "Translations"));
      const grid = el("div", "translation-section");
      translations.forEach(({ language, explanation }) => {
        const item = el("div", "translation-item");
        item.append(el("h3", "", language), el("p", "", explanation));
        grid.append(item);
      });
      section.append(grid);
      detail.append(section);
    }

    if (Array.isArray(term.related_terms) && term.related_terms.length) {
      const section = el("section", "detail-section");
      section.append(el("h3", "", "Related terms"));
      const related = el("div", "related-list");
      term.related_terms.forEach((value) => related.append(el("span", "related-chip", value)));
      section.append(related);
      detail.append(section);
    }
    appendTextSection(detail, "Source", term.source);
  }

  async function selectTerm(term, selectedButton) {
    document.querySelectorAll(".library-result-button").forEach((button) => button.setAttribute("aria-current", "false"));
    selectedButton?.setAttribute("aria-current", "true");
    try {
      const full = await window.HealthBridge.apiRequest(`/medical-terms/${encodeURIComponent(term.id)}`);
      renderTerm(full);
    } catch (error) {
      window.HealthBridge.showMessage(message, error.message || "The term explanation could not be loaded.");
    }
  }

  function renderList(terms) {
    list.replaceChildren();
    count.textContent = `${terms.length} ${terms.length === 1 ? "term" : "terms"}`;
    if (!terms.length) {
      list.append(el("p", "inline-status", "No terms matched that search."));
      detail.replaceChildren(el("div", "empty-detail", "Try another medical term."));
      return;
    }
    terms.forEach((term, index) => {
      const button = el("button", "library-result-button");
      button.type = "button";
      button.setAttribute("aria-current", "false");
      button.append(el("strong", "", term.term || "Medical term"));
      button.append(el("span", "", term.category || "Health terminology"));
      button.addEventListener("click", () => selectTerm(term, button));
      list.append(button);
      if (index === 0) selectTerm(term, button);
    });
  }

  async function searchTerms(query) {
    window.HealthBridge.showMessage(message, "Searching medical terminology...", "info");
    try {
      const result = await window.HealthBridge.apiRequest(`/medical-terms${query ? `?q=${encodeURIComponent(query)}` : ""}`);
      if (!Array.isArray(result)) throw new Error("The medical-terms response was not in the expected format.");
      window.HealthBridge.showMessage(message, "", "info");
      renderList(result);
    } catch (error) {
      window.HealthBridge.showMessage(message, error.message || "Medical terms could not be loaded.");
      count.textContent = "";
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    searchTerms(search.value.trim());
  });
  searchTerms("");
})();
