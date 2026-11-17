(() => {
  const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
  const SUPPORTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"];
  const fileInput = document.getElementById("report-file");
  const dropZone = document.getElementById("report-drop-zone");
  const form = document.getElementById("report-upload-form");
  const message = document.getElementById("report-message");
  const progress = document.getElementById("report-progress");
  const uploadButton = document.getElementById("upload-report-button");
  const history = document.getElementById("report-history");
  const historyMessage = document.getElementById("report-history-message");
  const resultPanel = document.getElementById("report-result");
  let selectedFile = null;
  let activeReportId = null;
  let currentState = "idle";

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function handleUnauthorized() {
    window.HealthBridge.clearSession();
    window.location.replace("login.html?reason=session-expired");
  }

  function setState(state, title = "", detail = "") {
    currentState = state;
    progress.dataset.state = state;
    progress.hidden = !["uploading", "processing"].includes(state);
    document.getElementById("report-progress-title").textContent = title;
    document.getElementById("report-progress-detail").textContent = detail;
    form.setAttribute("aria-busy", String(["uploading", "processing"].includes(state)));
    uploadButton.disabled = !selectedFile || ["uploading", "processing"].includes(state);
    uploadButton.querySelector("span").textContent = ["uploading", "processing"].includes(state)
      ? "Please wait..."
      : "Upload and analyze";
  }

  function validateFile(file) {
    if (!file) return "Choose a report file to continue.";
    const lowerName = file.name.toLowerCase();
    if (!SUPPORTED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
      return "Unsupported file. Choose a PDF, PNG, JPG, or JPEG report.";
    }
    if (file.size === 0) return "This file is empty. Choose another report.";
    if (file.size > MAX_UPLOAD_BYTES) return "This file is larger than the 10 MB default upload limit.";
    return "";
  }

  function chooseFile(file) {
    selectedFile = file || null;
    window.HealthBridge.showMessage(message, "");
    if (!selectedFile) {
      document.getElementById("selected-file").hidden = true;
      setState("idle");
      return;
    }
    const validationError = validateFile(selectedFile);
    if (validationError) {
      document.getElementById("selected-file").hidden = true;
      setState("unsupported file");
      window.HealthBridge.showMessage(message, validationError);
      return;
    }
    document.getElementById("selected-file-name").textContent = `${selectedFile.name} · ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`;
    document.getElementById("selected-file").hidden = false;
    setState("idle");
  }

  function appendList(parent, items, emptyMessage) {
    parent.replaceChildren();
    if (!Array.isArray(items) || items.length === 0) {
      parent.append(element("li", "report-empty-item", emptyMessage));
      return;
    }
    items.forEach((item) => parent.append(element("li", "", item)));
  }

  function renderLabResults(results) {
    const container = document.getElementById("report-lab-results");
    container.replaceChildren();
    if (!Array.isArray(results) || results.length === 0) {
      container.append(element("p", "report-empty-state", "No known test results were confidently detected in readable report text."));
      return;
    }

    const table = element("table", "report-lab-table");
    const caption = element("caption", "visually-hidden", "Extracted laboratory test values and ranges");
    const head = element("thead");
    const headRow = element("tr");
    ["Test", "Value", "Reference range", "Status"].forEach((heading) => headRow.append(element("th", "", heading)));
    head.append(headRow);
    const body = element("tbody");
    results.forEach((result) => {
      const row = element("tr");
      row.append(element("th", "report-test-name", result.test_name || "Recognized test"));
      const value = result.value ? `${result.value}${result.unit ? ` ${result.unit}` : ""}` : "Value not clearly detected";
      row.append(element("td", "", value));
      row.append(element("td", "", result.reference_range || "Reference range was not provided in the uploaded report."));
      const status = element("td", `report-result-status status-${String(result.status || "unknown").toLowerCase().replaceAll(" ", "-")}`, (result.status || "Status unavailable").replaceAll("_", " "));
      row.append(status);
      body.append(row);
    });
    table.append(caption, head, body);
    container.append(table);
  }

  function renderTerms(terms) {
    const container = document.getElementById("report-medical-terms");
    container.replaceChildren();
    if (!Array.isArray(terms) || terms.length === 0) {
      container.append(element("p", "report-empty-state", "No terms from the current medical terminology knowledge base were detected."));
      return;
    }
    terms.forEach((term) => {
      const item = element("article", "report-term-item");
      const heading = element("div", "report-term-heading");
      heading.append(element("h4", "", term.term || "Medical term"));
      if (term.category) heading.append(element("span", "term-category", term.category));
      item.append(heading, element("p", "", term.simple_explanation || "No simple explanation is available in the knowledge base."));
      if (term.source) item.append(element("p", "report-term-source", `Source: ${term.source}`));
      container.append(item);
    });
  }

  function renderReport(report) {
    if (!report || typeof report !== "object" || !report.analysis || typeof report.analysis !== "object") {
      throw new Error("The report response was incomplete. Please reload your report list.");
    }
    activeReportId = report.id;
    const analysis = report.analysis;
    const documentInfo = analysis.document || {};
    document.getElementById("result-filename").textContent = report.filename || documentInfo.filename || "Report summary";
    document.getElementById("result-document-meta").textContent = `${documentInfo.media_type || report.file_type || "Document"}${documentInfo.page_count ? ` · ${documentInfo.page_count} page${documentInfo.page_count === 1 ? "" : "s"}` : ""} · Uploaded ${report.uploaded_at || "recently"}`;
    document.getElementById("result-summary").textContent = analysis.summary || "The readable report information was processed.";
    document.getElementById("result-status").textContent = report.status || "Completed";
    renderLabResults(analysis.detected_tests);
    renderTerms(analysis.medical_terms);
    appendList(document.getElementById("report-observations"), analysis.important_observations, "No additional observations were generated from readable content.");
    appendList(document.getElementById("report-questions"), analysis.questions_for_healthcare_professional, "Ask a healthcare professional to review the report with you.");
    document.getElementById("report-disclaimer").textContent = analysis.disclaimer || "This report explanation is educational only and is not a diagnosis.";
    resultPanel.hidden = false;
    resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function loadReport(reportId) {
    window.HealthBridge.showMessage(historyMessage, "Loading report summary...", "info");
    try {
      const report = await window.HealthBridge.apiRequest(`/reports/${reportId}/analyze`, { method: "POST", auth: true });
      renderReport(report);
      window.HealthBridge.showMessage(historyMessage, "", "info");
    } catch (error) {
      if (error.status === 401) return handleUnauthorized();
      window.HealthBridge.showMessage(historyMessage, error.message || "This report could not be opened.");
    }
  }

  async function deleteReport(reportId) {
    if (!window.confirm("Delete this saved report summary? This cannot be undone.")) return;
    try {
      await window.HealthBridge.apiRequest(`/reports/${reportId}`, { method: "DELETE", auth: true });
      if (activeReportId === reportId) {
        activeReportId = null;
        resultPanel.hidden = true;
      }
      await loadHistory();
    } catch (error) {
      if (error.status === 401) return handleUnauthorized();
      window.HealthBridge.showMessage(historyMessage, error.message || "The report could not be deleted.");
    }
  }

  async function loadHistory() {
    history.replaceChildren();
    window.HealthBridge.showMessage(historyMessage, "Loading saved reports...", "info");
    try {
      const data = await window.HealthBridge.apiRequest("/reports", { auth: true });
      if (!data || !Array.isArray(data.reports)) throw new Error("The report list response was incomplete.");
      window.HealthBridge.showMessage(historyMessage, "", "info");
      if (data.reports.length === 0) {
        history.append(element("p", "report-empty-state", "No report summaries have been saved to this account."));
        return;
      }
      data.reports.forEach((report) => {
        const item = element("article", "report-history-item");
        const details = element("div", "report-history-details");
        details.append(element("strong", "", report.filename || "Medical report"));
        details.append(element("span", "", report.summary || "Structured report summary"));
        const actions = element("div", "report-history-actions");
        const viewButton = element("button", "button button-outline button-small", "View");
        viewButton.type = "button";
        viewButton.addEventListener("click", () => loadReport(report.id));
        const deleteButton = element("button", "button button-quiet button-small", "Delete");
        deleteButton.type = "button";
        deleteButton.addEventListener("click", () => deleteReport(report.id));
        actions.append(viewButton, deleteButton);
        item.append(details, actions);
        history.append(item);
      });
    } catch (error) {
      if (error.status === 401) return handleUnauthorized();
      window.HealthBridge.showMessage(historyMessage, error.message || "Saved reports could not be loaded.");
    }
  }

  fileInput.addEventListener("change", () => chooseFile(fileInput.files?.[0]));
  document.getElementById("clear-file").addEventListener("click", () => {
    fileInput.value = "";
    chooseFile(null);
  });
  ["dragenter", "dragover"].forEach((type) => dropZone.addEventListener(type, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  }));
  ["dragleave", "drop"].forEach((type) => dropZone.addEventListener(type, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  }));
  dropZone.addEventListener("drop", (event) => chooseFile(event.dataTransfer?.files?.[0]));
  dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    window.HealthBridge.showMessage(message, "");
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setState("unsupported file");
      window.HealthBridge.showMessage(message, validationError);
      return;
    }

    const data = new FormData();
    data.append("upload", selectedFile, selectedFile.name);
    resultPanel.hidden = true;
    setState("uploading", "Uploading report...", "The server validates and processes your document temporarily.");
    const processingTimer = window.setTimeout(() => {
      if (currentState === "uploading") setState("processing", "Processing report...", "Reading document text and matching known tests and terms.");
    }, 250);
    try {
      const uploaded = await window.HealthBridge.apiRequest("/reports/upload", { method: "POST", body: data, auth: true });
      setState("processing", "Preparing your summary...", "Only extracted structured information is saved.");
      const analyzed = await window.HealthBridge.apiRequest(`/reports/${uploaded.id}/analyze`, { method: "POST", auth: true });
      window.clearTimeout(processingTimer);
      renderReport(analyzed);
      setState("completed", "Report analysis complete.", "Review the extracted details below.");
      await loadHistory();
    } catch (error) {
      window.clearTimeout(processingTimer);
      if (error.status === 401) return handleUnauthorized();
      const isUnreadable = error.status === 422 && /scanned|ocr|read|text/i.test(error.message);
      setState(isUnreadable ? "unreadable document" : "failed");
      window.HealthBridge.showMessage(message, error.message || "The report could not be processed. Choose another file or try again.");
    }
  });

  setState("idle");
  loadHistory();
})();