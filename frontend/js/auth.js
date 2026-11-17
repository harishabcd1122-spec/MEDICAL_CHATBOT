(() => {
  const API_BASE_URL = window.location.protocol === "file:"
    ? "http://127.0.0.1:8000"
    : window.location.origin;
  const TOKEN_KEY = "healthbridge_access_token";
  const REQUEST_TIMEOUT_MS = 12000;

  window.API_BASE_URL = API_BASE_URL;

  function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  function clearSession() {
    sessionStorage.removeItem(TOKEN_KEY);
  }

  async function apiRequest(path, options = {}) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    const headers = new Headers(options.headers || {});

    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (options.auth && getToken()) {
      headers.set("Authorization", `Bearer ${getToken()}`);
    }

    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers,
        signal: controller.signal
      });
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : null;

      if (!response.ok) {
        const error = new Error(readableError(payload, response.status));
        error.status = response.status;
        throw error;
      }
      return payload;
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error("The request timed out. Please try again.");
      }
      if (error instanceof TypeError) {
        throw new Error("HealthBridge could not reach the backend. Check that the server is running and try again.");
      }
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  function readableError(payload, status) {
    if (status >= 500) return "The service had a problem. Please try again in a moment.";
    const detail = payload && payload.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "Please check the information you entered and try again.";
    return "The request could not be completed. Please try again.";
  }

  function showMessage(target, message, kind = "error") {
    if (!target) return;
    target.textContent = message;
    target.hidden = !message;
    target.dataset.kind = kind;
  }

  function logout() {
    clearSession();
    window.location.replace("login.html");
  }

  async function requireAuth() {
    const token = getToken();
    if (!token) {
      window.location.replace("login.html?reason=sign-in");
      return null;
    }

    try {
      const user = await apiRequest("/auth/me", { auth: true });
      document.querySelectorAll("[data-user-name]").forEach((element) => {
        element.textContent = user.name || "Your account";
      });
      return user;
    } catch (error) {
      if (error.status === 401) {
        clearSession();
        window.location.replace("login.html?reason=session-expired");
        return null;
      }
      const notice = document.createElement("p");
      notice.className = "form-message auth-connection-message";
      notice.setAttribute("role", "alert");
      notice.textContent = error.message || "Your session could not be checked. Please try again.";
      document.body.prepend(notice);
      return null;
    }
  }

  function isValidEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  function setFormBusy(form, busy, label) {
    const button = form.querySelector("button[type='submit']");
    const buttonLabel = button?.querySelector("span");
    if (!button) return;
    if (busy) button.dataset.originalLabel = buttonLabel?.textContent || button.textContent;
    button.disabled = busy;
    form.setAttribute("aria-busy", String(busy));
    if (buttonLabel) buttonLabel.textContent = busy ? label : button.dataset.originalLabel;
  }

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    const message = document.getElementById("login-message");
    const params = new URLSearchParams(window.location.search);
    if (params.get("reason") === "session-expired") {
      showMessage(message, "Your session has expired. Please sign in again.");
    } else if (params.get("registered") === "1") {
      showMessage(message, "Your account was created. Please sign in to continue.", "success");
    } else if (params.get("reason") === "sign-in") {
      showMessage(message, "Please sign in to access that page.");
    }

    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = loginForm.elements.namedItem("email").value.trim();
      const password = loginForm.elements.namedItem("password").value;
      showMessage(message, "");
      if (!isValidEmail(email) || !password) {
        showMessage(message, "Enter a valid email address and your password.");
        return;
      }

      setFormBusy(loginForm, true, "Signing in...");
      try {
        const data = await apiRequest("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password })
        });
        if (!data || typeof data.access_token !== "string") {
          throw new Error("The sign-in response was incomplete. Please try again.");
        }
        sessionStorage.setItem(TOKEN_KEY, data.access_token);
        const next = params.get("next");
        const allowedPages = ["dashboard.html", "chat.html", "diseases.html", "medical-terms.html"];
        window.location.replace(allowedPages.includes(next) ? next : "dashboard.html");
      } catch (error) {
        const userMessage = error.status === 401
          ? "Invalid email or password."
          : error.message || "Sign-in could not be completed. Please try again.";
        showMessage(message, userMessage);
      } finally {
        setFormBusy(loginForm, false, "Sign in");
      }
    });
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    const message = document.getElementById("register-message");
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const name = registerForm.elements.namedItem("name").value.trim();
      const email = registerForm.elements.namedItem("email").value.trim();
      const password = registerForm.elements.namedItem("password").value;
      const confirmPassword = registerForm.elements.namedItem("confirm_password").value;
      showMessage(message, "");

      if (!name || !email || !password || !confirmPassword) {
        showMessage(message, "Complete every field to create your account.");
        return;
      }
      if (name.length < 2 || name.length > 100) {
        showMessage(message, "Name must be between 2 and 100 characters.");
        return;
      }
      if (!isValidEmail(email)) {
        showMessage(message, "Enter a valid email address.");
        return;
      }
      if (password.length < 6 || password.length > 128) {
        showMessage(message, "Password must be between 6 and 128 characters.");
        return;
      }
      if (password !== confirmPassword) {
        showMessage(message, "Passwords do not match.");
        return;
      }

      setFormBusy(registerForm, true, "Creating account...");
      try {
        await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify({ name, email, password, confirm_password: confirmPassword })
        });
        window.location.replace("login.html?registered=1");
      } catch (error) {
        showMessage(message, error.message || "Registration could not be completed. Please try again.");
      } finally {
        setFormBusy(registerForm, false, "Create account");
      }
    });
  }

  document.querySelectorAll("[data-logout]").forEach((button) => {
    button.addEventListener("click", logout);
  });

  if (document.body.dataset.protected === "true") {
    requireAuth();
  }

  window.HealthBridge = {
    apiRequest,
    clearSession,
    getToken,
    logout,
    requireAuth,
    showMessage
  };
})();
