      // ── ADMINISTRATION ───────────────────────────────────────────────────────
      function renderAdmin() {
        // Chef de Service ne voit que l'onglet Stagiaires
        const tabs = [
          { id: 'interns', label: 'Stagiaires', visible: true }
        ];
        if (isDFRI()) {
          tabs.push(
            { id: 'import', label: 'Import Stagiaires', visible: true },
            { id: 'depts', label: 'Services', visible: true },
            { id: 'accounts', label: 'Comptes Admin', visible: true },
            { id: 'pwd', label: 'Mot de passe', visible: true }
          );
        }
        const tabsHTML = tabs.map(t => `<button class="tab ${t.id === 'interns' ? 'active' : ''}" id="tab-${t.id}" onclick="showAdminTab('${t.id}')">${t.label}</button>`).join('');
        document.getElementById("view-container").innerHTML = `
                <div class="tabs">
                  ${tabsHTML}
                </div>
                <div id="admin-content"></div>`;
        showAdminTab("interns");
      }

      function showAdminTab(tab) {
        document
          .querySelectorAll(".tab")
          .forEach((t) => t.classList.remove("active"));
        document.getElementById(`tab-${tab}`).classList.add("active");
        switch (tab) {
          case "interns":
            renderAdminInterns();
            break;
          case "import":
            document.getElementById("admin-content").innerHTML = '<div id="admin-view-container"></div>';
            renderAdminImport();
            break;
          case "depts":
            renderAdminDepts();
            break;
          case "accounts":
            renderAdminAccounts();
            break;
          case "pwd":
            renderAdminPwd();
            break;
        }
      }

      // ── ★ DEPARTMENTS TAB ────────────────────────────────────────────────────
      function renderAdminDepts() {
        const depts = DATA.departments || [];
        const interns = activeInterns();

        document.getElementById("admin-content").innerHTML = `
                <div class="grid2" style="align-items:start">
                  <div class="card">
                    <div class="admin-section-header card-header">
                      <h3>Services</h3>
                      <span style="font-family:'DM Mono',monospace;font-size:11px;color:var(--text-f)">${depts.length} enregistrés</span>
                    </div>
                    <div class="card-body" style="padding-top:0">
                      <div id="dept-list-msg"></div>
                      ${
                        depts.length === 0
                          ? '<div class="empty-state"><span class="material-symbols-outlined">corporate_fare</span><p>Aucun service. Commencez par en créer un.</p></div>'
                          : `
                      <div style="display:flex;align-items:center;background:var(--surface-d);border:1px solid var(--border);border-radius:8px;padding:0 12px;margin-bottom:12px">
                        <span class="material-symbols-outlined" style="color:var(--text-m);margin-right:8px">search</span>
                        <input type="text" id="admin-dept-search" placeholder="Rechercher un service..." oninput="filterAdminDepartments()" style="border:none;background:transparent;color:#fff;font-size:14px;padding:10px 0;width:100%;outline:none" />
                      </div>
                      <table class="data-table">
                        <thead><tr><th>Nom du service</th><th>Stagiaires</th><th>Actions</th></tr></thead>
                        <tbody>
                          ${depts
                            .map((d) => {
                              const nb = interns.filter(
                                (i) => i.department_id === d.id,
                              ).length;
                              return `<tr id="dept-row-${d.id}" data-admin-dept-search="${d.name.toLowerCase()}">
                              <td>
                                <span id="dept-label-${d.id}" style="font-weight:600">${d.name}</span>
                                <input id="dept-input-${d.id}" class="form-control" value="${d.name}"
                                  style="display:none;padding:5px 10px;font-size:13px;width:100%"
                                  onkeydown="if(event.key==='Enter')saveDeptName('${d.id}');if(event.key==='Escape')cancelEditDept('${d.id}','${d.name}')" />
                              </td>
                              <td><span class="badge badge-grey">${nb}</span></td>
                              <td>
                                <div style="display:flex;gap:6px">
                                  <button id="dept-edit-btn-${d.id}" class="btn btn-ghost" style="padding:4px 10px;font-size:11px" onclick="startEditDept('${d.id}')" title="Renommer">
                                    <span class="material-symbols-outlined" style="font-size:13px">edit</span>
                                  </button>
                                  <button id="dept-save-btn-${d.id}" class="btn btn-primary" style="padding:4px 10px;font-size:11px;display:none" onclick="saveDeptName('${d.id}')">
                                    <span class="material-symbols-outlined" style="font-size:13px">check</span>
                                  </button>
                                  <button id="dept-cancel-btn-${d.id}" class="btn btn-ghost" style="padding:4px 10px;font-size:11px;display:none" onclick="cancelEditDept('${d.id}','${d.name}')">
                                    <span class="material-symbols-outlined" style="font-size:13px">close</span>
                                  </button>
                                  <button class="btn btn-danger" style="padding:4px 10px;font-size:11px" onclick="confirmDeleteDept('${d.id}','${d.name}',${nb})" ${nb > 0 ? "disabled title='Réassignez les stagiaires d\\'abord'" : ""}>
                                    <span class="material-symbols-outlined" style="font-size:13px">delete</span>
                                  </button>
                                </div>
                              </td>
                            </tr>`;
                            })
                            .join("")}
                        </tbody>
                      </table>`
                      }
                    </div>
                  </div>

                  <div class="card">
                    <div class="card-header"><h3>Ajouter un Service</h3></div>
                    <div class="card-body">
                      <div id="add-dept-msg"></div>
                      <div class="form-group">
                        <label class="form-label">Nom du service</label>
                        <input class="form-control" id="inp-dept-name" placeholder="Ex: Radiologie, Ophtalmologie…" />
                      </div>
                      <button class="btn btn-primary" style="width:100%;justify-content:center;padding:12px" onclick="addDept()">
                        <span class="material-symbols-outlined">add_circle</span> Créer le service
                      </button>
                      <div style="margin-top:20px;padding:12px;background:var(--surface2);border-radius:var(--radius);border:1px solid var(--border)">
                        <div style="font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;color:var(--text-f);margin-bottom:6px">ℹ Note</div>
                        <p style="font-size:12px;color:var(--text-m)">Double-cliquez sur un nom ou cliquez ✏️ pour renommer. Un service ne peut pas être supprimé tant qu'il contient des stagiaires.</p>
                      </div>
                    </div>
                  </div>
                </div>`;

        // Also wire up double-click to edit
        depts.forEach((d) => {
          const label = document.getElementById(`dept-label-${d.id}`);
          if (label)
            label.addEventListener("dblclick", () => startEditDept(d.id));
        });
      }

      function filterAdminDepartments() {
        const input = document.getElementById('admin-dept-search');
        const term = input ? normalizeSearchText(input.value.trim()) : '';
        document.querySelectorAll('[data-admin-dept-search]').forEach((row) => {
          const haystack = normalizeSearchText(row.getAttribute('data-admin-dept-search') || '');
          row.style.display = haystack.includes(term) ? '' : 'none';
        });
      }

      function startEditDept(id) {
        document.getElementById(`dept-label-${id}`).style.display = "none";
        document.getElementById(`dept-input-${id}`).style.display = "block";
        document.getElementById(`dept-edit-btn-${id}`).style.display = "none";
        document.getElementById(`dept-save-btn-${id}`).style.display =
          "inline-flex";
        document.getElementById(`dept-cancel-btn-${id}`).style.display =
          "inline-flex";
        document.getElementById(`dept-input-${id}`).focus();
        document.getElementById(`dept-input-${id}`).select();
      }

      function cancelEditDept(id, originalName) {
        document.getElementById(`dept-label-${id}`).style.display = "";
        document.getElementById(`dept-input-${id}`).style.display = "none";
        document.getElementById(`dept-input-${id}`).value = originalName;
        document.getElementById(`dept-edit-btn-${id}`).style.display =
          "inline-flex";
        document.getElementById(`dept-save-btn-${id}`).style.display = "none";
        document.getElementById(`dept-cancel-btn-${id}`).style.display = "none";
      }

      async function saveDeptName(id) {
        const newName = document
          .getElementById(`dept-input-${id}`)
          .value.trim();
        if (!newName) {
          showToast("Le nom ne peut pas être vide", "error");
          return;
        }
        try {
          const res = await apiFetch(`/departments/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ name: newName }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur");
          showToast(`Service renommé en "${newName}"`, "success");
          // Update local DATA without full reload
          const dept = DATA.departments.find((d) => d.id === id);
          if (dept) dept.name = newName;
          // Update label in-place without re-render
          const label = document.getElementById(`dept-label-${id}`);
          if (label) label.textContent = newName;
          const row = document.getElementById(`dept-row-${id}`);
          if (row) row.setAttribute('data-admin-dept-search', normalizeSearchText(newName));
          cancelEditDept(id, newName);
        } catch (e) {
          showToast(e.message, "error");
        }
      }

      async function addDept() {
        const name = document.getElementById("inp-dept-name").value.trim();
        const msgEl = document.getElementById("add-dept-msg");
        if (!name) {
          msgEl.innerHTML =
            '<div class="alert alert-error">Veuillez saisir un nom.</div>';
          return;
        }
        try {
          const res = await apiFetch("/departments", {
            method: "POST",
            body: JSON.stringify({ name }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur serveur");
          showToast(`Service "${name}" créé`, "success");
          document.getElementById("inp-dept-name").value = "";
          // Refresh departments in DATA
          const dRes = await apiFetch("/departments");
          DATA.departments = await dRes.json();
          renderAdminDepts();
        } catch (e) {
          msgEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
        }
      }

      function confirmDeleteDept(id, name, internCount) {
        if (internCount > 0) {
          showToast(
            `Impossible : ${internCount} stagiaire(s) assigné(s) à "${name}"`,
            "error",
          );
          return;
        }
        openModal(
          "Supprimer ce service ?",
          `Êtes-vous sûr de vouloir supprimer <strong style="color:#fff">${name}</strong> ? Cette action est irréversible.`,
          `<button class="btn btn-danger" onclick="deleteDept('${id}')"><span class="material-symbols-outlined">delete_forever</span> Supprimer</button>
                 <button class="btn btn-ghost" onclick="closeModal()">Annuler</button>`,
        );
      }

      async function deleteDept(id) {
        try {
          const res = await apiFetch(`/departments/${id}`, {
            method: "DELETE",
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur");
          showToast(data.message || "Service supprimé", "success");
          closeModal();
          const dRes = await apiFetch("/departments");
          DATA.departments = await dRes.json();
          renderAdminDepts();
        } catch (e) {
          showToast(e.message, "error");
          closeModal();
        }
      }

