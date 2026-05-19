      // ── API HELPERS ──────────────────────────────────────────────────────────
      async function apiFetch(path, opts = {}) {
        const res = await fetch(API + path, {
          headers: authHeaders(),
          ...opts,
        });
        if (res.status === 401) {
          doLogout();
          throw new Error("Session expirée");
        }
        return res;
      }

      async function readJsonResponse(res, label) {
        const text = await res.text();
        let data = null;
        if (text) {
          try {
            data = JSON.parse(text);
          } catch (error) {
            throw new Error(`${label}: r?ponse non JSON (${res.status}) - ${text.slice(0, 120)}`);
          }
        }
        if (!res.ok) {
          const detail = data && (data.detail || data.message);
          throw new Error(`${label}: ${detail || `erreur ${res.status}`}`);
        }
        return data;
      }

      async function loadData() {
        IS_DATA_LOADING = true;
        try {
          const [intRes, attRes, dlyRes] = await Promise.all([
            apiFetch("/interns"),
            apiFetch("/dashboard/history"),
            apiFetch("/departments"),
          ]);
          const interns = await readJsonResponse(intRes, "stagiaires");
          const history = await readJsonResponse(attRes, "historique");
          const departments = await readJsonResponse(dlyRes, "services");
          DATA.interns = Array.isArray(interns) ? interns : [];
          DATA.history = Array.isArray(history) ? history : [];
          DATA.departments = Array.isArray(departments) ? departments : [];
          
          // Load admins only for DFRI
          if (isDFRI()) {
            const admRes = await apiFetch("/auth/admins");
            DATA.admins = admRes.ok ? await readJsonResponse(admRes, "comptes") : [];
          }
          
          // Load audit log only for DFRI and Directeur
          if (isDFRI() || isDirecteur()) {
            const auditRes = await apiFetch("/audit/logs");
            DATA.auditLogs = auditRes.ok ? await readJsonResponse(auditRes, "audit") : [];
          }
          
          // Update last-refresh timestamp
          const now = new Date();
          const timeStr = now.toLocaleTimeString("fr-FR", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          });
          const el = document.getElementById("last-refresh-time");
          if (el) el.textContent = timeStr;
          
          // Update alert bell count
          updateAlertBell();
        } catch (e) {
          if (e.message === "Session expirée") {
            return;
          }
          showToast("Erreur chargement données: " + e.message, "error");
          const vc = document.getElementById("view-container");
          if (vc) {
            vc.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">warning</span><p>Impossible de charger les données, veuillez réessayer.</p></div>`;
          }
        } finally {
          IS_DATA_LOADING = false;
        }
      }

      function updateAlertBell() {
        const alertCount = (DATA.history || []).filter(
          (h) => h.needs_attention,
        ).length;
        const countEl = document.getElementById("topbar-alert-count");
        if (!countEl) return;
        if (alertCount > 0) {
          countEl.textContent = alertCount > 99 ? "99+" : alertCount;
          countEl.classList.remove("hidden");
        } else {
          countEl.classList.add("hidden");
        }
      }

      async function refreshData() {
        const btn = document.getElementById("btn-refresh");
        btn.classList.add("spinning");
        btn.disabled = true;
        await loadData();
        // Re-render current view with fresh data
        switchView(CURRENT_VIEW);
        btn.classList.remove("spinning");
        btn.disabled = false;
        showToast("Données actualisées", "success");
      }

      function toggleFullscreen() {
        const icon = document.getElementById("fullscreen-icon");
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
          if (icon) icon.textContent = "fullscreen_exit";
        } else {
          document.exitFullscreen().catch(() => {});
          if (icon) icon.textContent = "fullscreen";
        }
      }
      document.addEventListener("fullscreenchange", () => {
        const icon = document.getElementById("fullscreen-icon");
        if (icon)
          icon.textContent = document.fullscreenElement
            ? "fullscreen_exit"
            : "fullscreen";
      });

