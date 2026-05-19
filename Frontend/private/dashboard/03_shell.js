      // ── INIT ─────────────────────────────────────────────────────────────────
      async function initApp() {
        CURRENT_VIEW = null;
        CHARTS = {};
        SELECTED_INTERN = null;
        destroyCharts();
        
        const vc = document.getElementById("view-container");
        if (vc) {
          vc.innerHTML = '<div style="padding:20px; text-align:center;"><p>Chargement des données...</p></div>';
        }
        
        document.getElementById("user-name").textContent = AUTH.username;
        document.getElementById("user-avatar").textContent =
          AUTH.username[0].toUpperCase();
        document.getElementById("user-role").textContent = ROLE_LABELS[AUTH.role] || AUTH.role;
        buildNav();
        updateClock();
        setInterval(updateClock, 1000);
        applyRolePermissions();

        startTokenExpirationCheck();
        await loadData();
        if (!AUTH) return;
        switchView("global");
      }

      function applyRolePermissions() {
        // Hide export button for Directeur
        const exportBtn = document.getElementById("btn-excel-export");
        if (exportBtn) {
          exportBtn.style.display = isDirecteur() ? "none" : "flex";
        }
      }

      function buildNav() {
        const nav = document.getElementById("nav-links");
        const role = userRole();
        const items = NAV_ALL.filter((n) => n.roles.includes(role));
        nav.innerHTML = items
          .map(
            (n) =>
              `<button class="nav-item" id="nav-${n.id}" onclick="switchView('${n.id}')"><span class="material-symbols-outlined">${n.icon}</span>${n.label}</button>`,
          )
          .join("");
      }
      function updateNav(active) {
        document
          .querySelectorAll(".nav-item")
          .forEach((el) => el.classList.remove("active"));
        const el = document.getElementById(`nav-${active}`);
        if (el) el.classList.add("active");
      }
      function updateClock() {
        const now = new Date();
        document.getElementById("topbar-time").textContent =
          now.toLocaleDateString("fr-FR", {
            weekday: "short",
            day: "numeric",
            month: "short",
          }) +
          " · " +
          now.toLocaleTimeString("fr-FR", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          });
      }
      function destroyCharts() {
        Object.values(CHARTS).forEach((c) => c.destroy());
        CHARTS = {};
      }
      function switchView(id) {
        CURRENT_VIEW = id;
        updateNav(id);
        const titles = {
          global: "Vue Globale",
          individual: "Vue Individuelle",
          department: "Vue des Services",
          clusters: "Clusters & ML",
          alerts: "Journal des Alertes",
          archives: "Archivés",
          admin: "Administration",
          audit: "Journal d'Audit",
          about: "À propos"
        };
        document.getElementById("topbar-title").textContent = titles[id] || id;
        const vc = document.getElementById("view-container");
        vc.classList.add("fading");
        destroyCharts();
        setTimeout(() => {
          switch (id) {
            case "global":
              renderGlobal();
              break;
            case "individual":
              renderIndividual();
              break;
            case "department":
              renderDepartment();
              break;
            case "clusters":
              renderClusters();
              break;
            case "alerts":
              renderAlerts();
              break;
            case "archives":
              renderArchives();
              break;
            case "admin":
              renderAdmin();
              break;
            case "audit":
              renderAudit();
              break;
            case "about":
              renderAbout();
              break;
          }
          vc.classList.remove("fading");
        }, 220);
      }

