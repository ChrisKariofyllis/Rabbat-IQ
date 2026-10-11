const body = document.body;

document.querySelectorAll("form.scan-form").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector("button");
    if (!button || button.disabled) {
      return;
    }
    button.disabled = true;
    button.textContent = "Scanning…";
  });
});

document.querySelectorAll("[data-fill]").forEach((chip) => {
  chip.addEventListener("click", () => {
    const input = document.querySelector("#interest-text");
    if (!input) {
      return;
    }
    input.value = chip.getAttribute("data-fill") || "";
    input.focus();
  });
});

if (body.dataset.poll === "1") {
  const timer = window.setInterval(async () => {
    try {
      const response = await fetch("/api/scan/status", { headers: { Accept: "application/json" } });
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      if (!data.running) {
        window.clearInterval(timer);
        const failed = data.last && data.last.status === "error";
        window.location.href = failed ? "/?notice=scan-failed" : "/?notice=scanned";
      }
    } catch (_error) {
      /* The next tick tries again. A manual refresh still shows the latest scan. */
    }
  }, 2000);
}
