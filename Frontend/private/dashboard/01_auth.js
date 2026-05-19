      // ── AUTH ─────────────────────────────────────────────────────────────────
      const AUTH_STORAGE_KEY = "chu_auth";

      function showLoginError(msg) {
        showToast(msg, "error");
      }
      let popstateHandlerRegistered = false;
      async function doLogout(reason = "") {
        if (TOKEN_CHECK_INTERVAL) {
          clearInterval(TOKEN_CHECK_INTERVAL);
          TOKEN_CHECK_INTERVAL = null;
        }
        
        AUTH = null;
        DATA = {};
        CURRENT_VIEW = null;
        CHARTS = {};
        SELECTED_INTERN = null;
        IS_DATA_LOADING = false;
        
        localStorage.removeItem("chu_last_view");
        
        destroyCharts();
        
        const viewContainer = document.getElementById("view-container");
        if (viewContainer) viewContainer.innerHTML = "";

        if (reason) sessionStorage.setItem("chu_logout_reason", reason);
        try {
          await fetch(`${API}/logout`, { method: "POST" });
        } finally {
          window.location.href = "/login";
        }
        
        if (!popstateHandlerRegistered) {
          history.pushState(null, '', window.location.href);
          window.addEventListener('popstate', function() {
            history.pushState(null, '', window.location.href);
          });
          popstateHandlerRegistered = true;
        }
      }

      function parseJWT(token) {
        try {
          const base64Url = token.split('.')[1];
          const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
          const jsonPayload = decodeURIComponent(
            atob(base64)
              .split('')
              .map((c) => '%'+('00'+c.charCodeAt(0).toString(16)).slice(-2))
              .join(''),
          );
          return JSON.parse(jsonPayload);
        } catch (e) {
          return null;
        }
      }

      function startTokenExpirationCheck() {
        if (!AUTH || !AUTH.access_token) return;
        if (TOKEN_CHECK_INTERVAL) clearInterval(TOKEN_CHECK_INTERVAL);

        TOKEN_CHECK_INTERVAL = setInterval(() => {
          if (!AUTH || !AUTH.access_token) return;
          const decoded = parseJWT(AUTH.access_token);
          if (!decoded || !decoded.exp) return;

          const now = Math.floor(Date.now() / 1000);
          const secsUntilExpire = decoded.exp - now;
          if (secsUntilExpire <= 0) {
            doLogout("Votre session a expiré. Veuillez vous reconnecter.");
            return;
          }
          if (secsUntilExpire <= 300) {
            const mins = Math.ceil(secsUntilExpire / 60);
            showToast(`Votre session expire dans ${mins} minute${mins > 1 ? 's' : ''}.`, "warning");
          }
        }, 60000);
      }
      function authHeaders() {
        if (!AUTH || !AUTH.access_token) {
          return { "Content-Type": "application/json" };
        }
        return {
          Authorization: `Bearer ${AUTH.access_token}`,
          "Content-Type": "application/json",
        };
      }
      function userRole() {
        return AUTH ? AUTH.role : null;
      }
      function isDFRI() {
        return AUTH && AUTH.role === "dfri";
      }
      function isDirecteur() {
        return AUTH && AUTH.role === "directeur";
      }
      function isChefService() {
        return AUTH && AUTH.role === "chef_service";
      }
      function isSecretaire() {
        return AUTH && AUTH.role === "secretaire";
      }
      // Old compatibility function - kept for backward compatibility
      function isSuperAdmin() {
        return isDFRI();
      }
