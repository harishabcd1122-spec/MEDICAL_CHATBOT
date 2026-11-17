(() => {
  const form = document.getElementById("symptom-form");
  const input = document.getElementById("symptoms-input");
  const language = document.getElementById("symptom-language");
  const submitButton = document.getElementById("analyze-button");
  const loading = document.getElementById("analysis-loading");
  const message = document.getElementById("chat-message");
  const result = document.getElementById("analysis-result");
  const disclaimerText = "This chatbot provides general health information and educational assistance. It does not provide a medical diagnosis and does not replace a qualified doctor or healthcare professional.";

  function setBusy(busy) {
    submitButton.disabled = busy;
    loading.hidden = !busy;
    form.setAttribute("aria-busy", String(busy));
  }

  function makeElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function renderSymptoms(symptoms) {
    const container = document.getElementById("recognized-symptoms");
    container.replaceChildren();
    (Array.isArray(symptoms) ? symptoms : []).forEach((symptom) => {
      container.append(makeElement("span", "symptom-tag", String(symptom).replaceAll("_", " ")));
    });
    if (!container.childElementCount) container.append(makeElement("span", "result-supporting", "No specific symptoms were recognized."));
  }

  function renderConditions(conditions) {
    const list = document.getElementById("condition-list");
    list.replaceChildren();
    (Array.isArray(conditions) ? conditions : []).forEach((condition) => {
      const item = makeElement("article", "condition-item");
      item.append(makeElement("h4", "", condition.condition || "Possible condition"));
      const scoreLine = makeElement("div", "score-line");
      scoreLine.append(makeElement("span", "", "Model Match Score"));
      scoreLine.append(makeElement("strong", "", condition.score_display || `${Number(condition.model_match_score || 0).toFixed(1)}%`));
      const meter = makeElement("div", "score-meter");
      meter.setAttribute("aria-hidden", "true");
      const fill = makeElement("span");
      const score = Math.max(0, Math.min(100, Number(condition.model_match_score) || 0));
      fill.style.width = `${score}%`;
      meter.append(fill);
      item.append(scoreLine, meter);
      list.append(item);
    });
  }

  function renderQuestions(questions) {
    const section = document.getElementById("doctor-questions-section");
    const list = document.getElementById("doctor-questions");
    list.replaceChildren();
    (Array.isArray(questions) ? questions : []).forEach((question) => {
      list.append(makeElement("li", "", question));
    });
    section.hidden = list.childElementCount === 0;
  }

  function renderResult(data) {
    if (!data || typeof data !== "object" || typeof data.status !== "string") {
      throw new Error("The backend returned an unexpected response. Please try again.");
    }

    result.hidden = false;
    document.getElementById("result-status").textContent = data.status.replaceAll("_", " ");
    document.getElementById("result-disclaimer").textContent = data.disclaimer || disclaimerText;
    document.getElementById("score-note").textContent = data.score_note || "";
    document.getElementById("score-note").hidden = !data.score_note;

    const emergency = data.is_emergency === true || data.status === "emergency_detected";
    const emergencyPanel = document.getElementById("emergency-result");
    const normalPanel = document.getElementById("normal-result");
    const insufficientPanel = document.getElementById("insufficient-result");
    emergencyPanel.hidden = !emergency;
    normalPanel.hidden = emergency;
    insufficientPanel.hidden = emergency || data.status !== "insufficient_information";

    if (emergency) {
      document.getElementById("result-heading").textContent = "Safety response";
      document.getElementById("emergency-copy").textContent = data.emergency_details?.message || data.explanation || "These symptoms may require urgent medical attention. Please seek immediate professional medical care or emergency assistance.";
      document.getElementById("condition-list").replaceChildren();
      document.getElementById("recognized-symptoms").replaceChildren();
      document.getElementById("score-note").hidden = true;
      return;
    }

    document.getElementById("result-heading").textContent = data.status === "insufficient_information" ? "More information may help" : "Symptom analysis";
    if (data.status === "insufficient_information") {
      document.getElementById("insufficient-copy").textContent = data.explanation || "I don't have enough reliable information to answer that safely.";
      return;
    }

    renderSymptoms(data.extracted_symptoms);
    renderConditions(data.possible_conditions);
    const urgency = data.urgency || {};
    const urgencyValue = String(urgency.urgency_level || "LOW").toUpperCase();
    const urgencyBadge = document.getElementById("urgency-value");
    urgencyBadge.className = `urgency-badge urgency-${urgencyValue.toLowerCase()}`;
    urgencyBadge.textContent = urgencyValue;
    document.getElementById("urgency-explanation").textContent = urgency.explanation || "Follow up with a qualified healthcare professional if you are concerned.";
    document.getElementById("analysis-explanation").textContent = data.explanation || "The backend did not provide an explanation for this response.";
    renderQuestions(data.questions_for_doctor || urgency.questions_for_doctor);

    const conditionSection = document.getElementById("condition-section");
    conditionSection.hidden = !Array.isArray(data.possible_conditions) || data.possible_conditions.length === 0;
  }

  input.addEventListener("input", () => {
    document.getElementById("character-count").textContent = `${input.value.length} / 2000`;
  });

  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      input.value = button.dataset.example || "";
      input.dispatchEvent(new Event("input"));
      input.focus();
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const symptoms = input.value.trim();
    window.HealthBridge.showMessage(message, "");
    result.hidden = true;

    if (symptoms.length < 2) {
      window.HealthBridge.showMessage(message, "Please describe at least two characters of symptom information.");
      input.focus();
      return;
    }

    setBusy(true);
    try {
      const data = await window.HealthBridge.apiRequest("/symptoms/analyze", {
        method: "POST",
        body: JSON.stringify({ symptoms, language: language.value })
      });
      renderResult(data);
      result.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      window.HealthBridge.showMessage(message, error.message || "Symptom analysis could not be completed. Please try again.");
    } finally {
      setBusy(false);
    }
  });
})();
