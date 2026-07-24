(() => {
  "use strict";

  document.querySelectorAll("[data-sidebar-toggle]").forEach((element) => {
    element.addEventListener("click", () => {
      document.body.classList.toggle("sidebar-open");
    });
  });

  document.querySelectorAll("[data-auto-dismiss]").forEach((toastElement) => {
    window.setTimeout(() => {
      const toast = bootstrap.Toast.getOrCreateInstance(toastElement);
      toast.hide();
    }, 5000);
  });

  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      const submit = form.querySelector("button[type='submit'], input[type='submit']");
      if (submit) {
        submit.disabled = true;
        submit.setAttribute("aria-busy", "true");
      }
    });
  });
})();
