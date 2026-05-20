// ── CONFIG ──────────────────────────────────────────────────────────────
      const API = window.location.origin;

      // ── ROLES ───────────────────────────────────────────────────────────────
      const ROLES = {
        DFRI:         "dfri",
        DIRECTEUR:    "directeur",
        CHEF_SERVICE: "chef_service",
        SECRETAIRE:   "secretaire"
      };

      const ROLE_LABELS = {
        dfri:         "Directeur IT",
        directeur:    "Directeur",
        chef_service: "Chef de Service",
        secretaire:   "Secrétaire"
      };

      const FILIERE_OPTIONS = ["Médecine générale", "Pharmacie", "Infirmerie"];
      const ETABLISSEMENT_OPTIONS = ["ISPITS", "Médecine"];

      // ── STATE ───────────────────────────────────────────────────────────────
      let AUTH = null;
      let CURRENT_VIEW = "global";
      let DATA = {};
      let CHARTS = {};
      let SELECTED_INTERN = null;
      let TOKEN_CHECK_INTERVAL = null;
      let IS_DATA_LOADING = false;
      let FILTERS = {
        type: "",
        school: "",
        start_date: "",
        end_date: "",
        status: "active",
      };

      function normalizeFilterValue(value) {
        return String(value || "").trim().toLowerCase();
      }

      function getInternType(intern) {
        return (
          intern.intern_type || intern.type || intern.type_stagiaire || intern.filiere || ""
        ).toString();
      }

      function getInternSchool(intern) {
        return (
          intern.school || intern.ecole || intern.university || intern.universite || ""
        ).toString();
      }

      function getInternStatus(intern) {
        if (intern.archived) return "archived";
        if (intern.end_date) {
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          const endDate = new Date(intern.end_date);
          endDate.setHours(0, 0, 0, 0);
          if (endDate <= today) return "pending";
        }
        return "active";
      }

      function activeInterns() {
        return (DATA.interns || []).filter((i) => !i.archived);
      }

      function archivedInterns() {
        return (DATA.interns || []).filter((i) => i.archived);
      }

      function getBaseInterns() {
        let interns = DATA.interns || [];
        if (isChefService()) {
          interns = interns.filter((i) => i.department_id === AUTH.department_id);
        }
        return interns;
      }

      function filterInterns(interns) {
        const typeFilter = normalizeFilterValue(FILTERS.type);
        const schoolFilter = normalizeFilterValue(FILTERS.school);
        const statusFilter = FILTERS.status;
        const from = FILTERS.start_date ? new Date(FILTERS.start_date) : null;
        const to = FILTERS.end_date ? new Date(FILTERS.end_date) : null;

        return interns.filter((i) => {
          if (typeFilter) {
            const internType = normalizeFilterValue(getInternType(i));
            if (!internType.includes(typeFilter)) return false;
          }
          if (schoolFilter) {
            const school = normalizeFilterValue(getInternSchool(i));
            if (!school.includes(schoolFilter)) return false;
          }
          if (statusFilter && statusFilter !== "all") {
            if (getInternStatus(i) !== statusFilter) return false;
          }
          if (from || to) {
            const start = i.start_date ? new Date(i.start_date) : null;
            const end = i.end_date ? new Date(i.end_date) : null;
            if (from && (!start || start < from)) return false;
            if (to && (!end || end > to)) return false;
          }
          return true;
        });
      }

      function getVisibleInterns() {
        return filterInterns(getBaseInterns());
      }

      function getHistoryForInterns(interns) {
        const ids = interns.map((i) => i.id);
        return (DATA.history || []).filter((h) => ids.includes(h.intern_id));
      }

      function getVisibleHistory() {
        return getHistoryForInterns(getVisibleInterns());
      }

      function internDepartmentName(intern) {
        const dept = (DATA.departments || []).find((d) => d.id === intern.department_id);
        return dept ? dept.name : "—";
      }

      function fmtDateShort(value) {
        return value ? new Date(value).toLocaleDateString("fr-FR") : "—";
      }

      function getFilterOptions() {
        return {
          types: FILIERE_OPTIONS,
          schools: ETABLISSEMENT_OPTIONS,
        };
      }

      function renderFilterBar() {
        const { types, schools } = getFilterOptions();
        return `
          <div class="filter-bar" style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:18px">
            <div style="min-width:180px;flex:1;max-width:260px">
              <label class="form-label" style="margin-bottom:4px">Filière</label>
              <select id="filter-type" class="form-control" onchange="onFilterChange()">
                <option value="">Toutes</option>
                ${types.map((t) => `<option value="${t}" ${FILTERS.type === t ? "selected" : ""}>${t}</option>`).join("")}
              </select>
            </div>
            <div style="min-width:180px;flex:1;max-width:260px">
              <label class="form-label" style="margin-bottom:4px">Établissement</label>
              <select id="filter-school" class="form-control" onchange="onFilterChange()">
                <option value="">Toutes</option>
                ${schools.map((s) => `<option value="${s}" ${FILTERS.school === s ? "selected" : ""}>${s}</option>`).join("")}
              </select>
            </div>
            <div style="min-width:160px;flex:1;max-width:220px">
              <label class="form-label" style="margin-bottom:4px">Début</label>
              <input id="filter-start" class="form-control" type="date" value="${FILTERS.start_date}" onchange="onFilterChange()" />
            </div>
            <div style="min-width:160px;flex:1;max-width:220px">
              <label class="form-label" style="margin-bottom:4px">Fin</label>
              <input id="filter-end" class="form-control" type="date" value="${FILTERS.end_date}" onchange="onFilterChange()" />
            </div>
            <div style="min-width:180px;flex:1;max-width:220px">
              <label class="form-label" style="margin-bottom:4px">Statut</label>
              <select id="filter-status" class="form-control" onchange="onFilterChange()">
                <option value="active" ${FILTERS.status === "active" ? "selected" : ""}>Actif</option>
                <option value="pending" ${FILTERS.status === "pending" ? "selected" : ""}>En attente d'archivage</option>
                <option value="archived" ${FILTERS.status === "archived" ? "selected" : ""}>Archivé</option>
                <option value="all" ${FILTERS.status === "all" ? "selected" : ""}>Tous</option>
              </select>
            </div>
          </div>`;
      }

      function onFilterChange() {
        FILTERS.type = document.getElementById("filter-type").value;
        FILTERS.school = document.getElementById("filter-school").value;
        FILTERS.start_date = document.getElementById("filter-start").value;
        FILTERS.end_date = document.getElementById("filter-end").value;
        FILTERS.status = document.getElementById("filter-status").value;
        switch (CURRENT_VIEW) {
          case "global":
            renderGlobal();
            break;
          case "department":
            renderDepartment();
            break;
          case "individual":
            renderIndividual();
            break;
          case "archives":
            renderArchives();
            break;
        }
      }

      // ── NAV ─────────────────────────────────────────────────────────────────
      const NAV_ALL = [
        { id: "global", label: "Vue Globale", icon: "dashboard", roles: ["dfri", "directeur", "secretaire"] },
        { id: "individual", label: "Vue Individuelle", icon: "person_search", roles: ["dfri", "directeur", "chef_service", "secretaire"] },
        { id: "department", label: "Vue des Services", icon: "corporate_fare", roles: ["dfri", "directeur", "chef_service"] },
        { id: "clusters", label: "Clusters & ML", icon: "hub", roles: ["dfri"] },
        { id: "alerts", label: "Journal des Alertes", icon: "notifications_active", roles: ["dfri", "directeur", "chef_service", "secretaire"] },
        { id: "archives", label: "Archivés", icon: "archive", roles: ["dfri", "directeur", "chef_service", "secretaire"] },
        { id: "admin", label: "Administration", icon: "manage_accounts", roles: ["dfri", "chef_service"] },
        { id: "audit", label: "Journal d'Audit", icon: "history", roles: ["dfri", "directeur"] }
      ];
