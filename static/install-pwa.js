// Add this script to your existing templates/index.html (and other public templates if desired).
// It registers the service worker and optionally shows an install button when supported.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch((error) => {
      console.error("Service worker registration failed:", error);
    });
  });
}

let ayuSafaInstallPrompt = null;
window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  ayuSafaInstallPrompt = event;
  const button = document.getElementById("installAppButton");
  if (button) button.hidden = false;
});

window.addEventListener("appinstalled", () => {
  ayuSafaInstallPrompt = null;
  const button = document.getElementById("installAppButton");
  if (button) button.hidden = true;
});

async function installAyuSafaApp() {
  if (!ayuSafaInstallPrompt) {
    alert("To install: open the browser menu and choose Install app or Add to Home screen.");
    return;
  }
  ayuSafaInstallPrompt.prompt();
  await ayuSafaInstallPrompt.userChoice;
  ayuSafaInstallPrompt = null;
  const button = document.getElementById("installAppButton");
  if (button) button.hidden = true;
}
