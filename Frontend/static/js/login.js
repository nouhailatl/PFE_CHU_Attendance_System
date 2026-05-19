const form = document.getElementById("login-form");
const usernameInput = document.getElementById("inp-username");
const passwordInput = document.getElementById("inp-password");
const errorBox = document.getElementById("login-error");
const submitButton = document.getElementById("btn-login");

function showLoginError(message) {
  errorBox.textContent = `⚠ ${message}`;
  errorBox.classList.add("visible");
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.innerHTML = isLoading
    ? '<span class="spinner"></span> Connexion...'
    : '<span>Se connecter</span><span class="material-symbols-outlined" style="font-size:18px">arrow_forward</span>';
}

const logoutReason = sessionStorage.getItem("chu_logout_reason");
if (logoutReason) {
  sessionStorage.removeItem("chu_logout_reason");
  showLoginError(logoutReason);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    showLoginError("Veuillez remplir tous les champs.");
    return;
  }

  errorBox.classList.remove("visible");
  setLoading(true);

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Identifiants incorrects");
    }
    window.location.href = data.redirect || "/dashboard";
  } catch (error) {
    showLoginError(error.message);
  } finally {
    setLoading(false);
  }
});
