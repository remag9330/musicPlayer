function main() {
  automate_volume();
}

function automate_volume() {
  const form = document.getElementById("volume_form");
  if (!(form instanceof HTMLFormElement)) {
    throw new Error("form not found");
  }

  const slider = form.elements["volume"];
  if (!(slider instanceof HTMLInputElement)) {
    throw new Error("slider not found");
  }

  const submitButton = form.querySelector("button[type='submit']");
  if (!(submitButton instanceof HTMLButtonElement)) {
    throw new Error("submit button not found");
  }

  async function onChange() {
    const body = new FormData(form);
    try {
      await fetch(form.getAttribute("action"), { method: "POST", body });
    } catch (ex) {
      console.error("Error sending volume data update", ex);
    }
  }

  slider.addEventListener("change", onChange);
  submitButton.style.display = "none";
}

window.addEventListener("load", main, { once: true });
