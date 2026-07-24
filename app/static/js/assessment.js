(() => {
  "use strict";

  const form = document.querySelector("[data-response-form]");
  if (!form || form.querySelector("fieldset")?.disabled) return;

  const state = form.querySelector("[data-autosave-state]");
  const csrf = document.querySelector("meta[name='csrf-token']")?.content || "";
  const autosaveUrl = form.dataset.autosaveUrl;
  const intervalSeconds = Number.parseInt(form.dataset.autosaveSeconds || "30", 10);
  const notApplicable = form.querySelector("[data-not-applicable]");
  const notApplicableContainer = form.querySelector("[data-not-applicable-container]");
  let dirty = false;
  let submitting = false;
  let timer = null;

  const setState = (message, className = "") => {
    if (!state) return;
    state.classList.remove("saving", "error");
    if (className) state.classList.add(className);
    state.textContent = message;
  };

  const toggleNotApplicable = () => {
    const enabled = Boolean(notApplicable?.checked);
    if (notApplicableContainer) notApplicableContainer.hidden = !enabled;
    form.querySelectorAll("[data-response-input='option']").forEach((input) => {
      input.disabled = enabled;
      if (enabled) input.checked = false;
    });
    form.querySelectorAll(".answer-choice").forEach((label) => label.classList.toggle("disabled", enabled));
  };

  const markSelected = () => {
    form.querySelectorAll(".answer-choice").forEach((label) => {
      const input = label.querySelector("input[type='radio']");
      label.classList.toggle("selected", Boolean(input?.checked));
    });
  };

  const payload = () => ({
    selected_option_code: form.querySelector("[data-response-input='option']:checked")?.value || null,
    respondent_comment: form.querySelector("textarea[name$='respondent_comment']")?.value || "",
    is_not_applicable: Boolean(notApplicable?.checked),
    not_applicable_justification: form.querySelector("textarea[name$='not_applicable_justification']")?.value || "",
  });

  const autosave = async () => {
    if (!dirty || submitting || !autosaveUrl) return;
    setState("Guardando borrador...", "saving");
    try {
      const response = await fetch(autosaveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": csrf, "Accept": "application/json"},
        body: JSON.stringify(payload()),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || "No fue posible guardar");
      dirty = false;
      const time = new Date(data.saved_at).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
      setState(`Borrador guardado a las ${time}`);
    } catch (error) {
      setState(error.message || "Error de guardado automático", "error");
    }
  };

  form.addEventListener("input", (event) => {
    if (event.target.matches("input, textarea")) {
      dirty = true;
      setState("Cambios pendientes");
    }
  });
  form.addEventListener("change", () => {
    dirty = true;
    toggleNotApplicable();
    markSelected();
    setState("Cambios pendientes");
  });
  form.addEventListener("submit", () => {
    submitting = true;
    dirty = false;
  });
  window.addEventListener("beforeunload", (event) => {
    if (!dirty || submitting) return;
    event.preventDefault();
    event.returnValue = "";
  });

  toggleNotApplicable();
  markSelected();
  timer = window.setInterval(autosave, Math.max(intervalSeconds, 10) * 1000);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") autosave();
  });
  window.addEventListener("pagehide", () => window.clearInterval(timer));
})();
