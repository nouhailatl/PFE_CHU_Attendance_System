      // ── INTERNS TAB (with inline edit + badge buttons) ────────────────────────
      function renderAdminInterns() {
        let interns = activeInterns();
        let depts = DATA.departments || [];
        // Chef de Service: voir seulement ses stagiaires
        if (isChefService()) {
          interns = interns.filter((i) => i.department_id === AUTH.department_id);
          depts = depts.filter((d) => d.id === AUTH.department_id);
        }
        document.getElementById("admin-content").innerHTML = `
                <div class="grid2" style="align-items:start">
                  <div class="card">
                    <div class="admin-section-header card-header">
                      <h3>Liste des Stagiaires</h3>
                      <span style="font-family:'DM Mono',monospace;font-size:11px;color:var(--text-f)">${interns.length} enregistrés</span>
                    </div>
                    <div class="card-body" style="padding-top:0;overflow-x:auto">
                      <div style="display:flex;align-items:center;background:var(--surface-d);border:1px solid var(--border);border-radius:8px;padding:0 12px;margin-bottom:12px;min-width:520px">
                        <span class="material-symbols-outlined" style="color:var(--text-m);margin-right:8px">search</span>
                        <input type="text" id="admin-intern-search" placeholder="Rechercher un stagiaire ou un service..." oninput="filterAdminInterns()" style="border:none;background:transparent;color:#fff;font-size:14px;padding:10px 0;width:100%;outline:none" />
                      </div>
                      <table class="data-table">
                        <thead><tr><th>Prénom</th><th>Nom</th><th>Service</th><th>Badge</th><th>Actions</th></tr></thead>
                        <tbody>
                          ${interns
                            .map((i) => {
                              const dept = depts.find(
                                (d) => d.id === i.department_id,
                              );
                              const dName = dept ? dept.name : "—";
                              const deptOptions = depts
                                .map(
                                  (d) =>
                                    `<option value="${d.id}" ${d.id === i.department_id ? "selected" : ""}>${d.name}</option>`,
                                )
                                .join("");
                              return `<tr id="intern-row-${i.id}" data-admin-intern-search="${`${i.first_name} ${i.last_name} ${dName}`.toLowerCase()}">
                              <!-- FIRST NAME: display / edit -->
                              <td>
                                <span id="intern-fn-label-${i.id}" style="font-weight:600">${i.first_name}</span>
                                <input id="intern-fn-input-${i.id}" class="form-control" value="${i.first_name}"
                                  style="display:none;padding:5px 8px;font-size:13px;min-width:90px"
                                  onkeydown="if(event.key==='Enter')saveIntern('${i.id}');if(event.key==='Escape')cancelEditIntern('${i.id}','${i.first_name}','${i.last_name}','${i.department_id}')" />
                              </td>
                              <!-- LAST NAME: display / edit -->
                              <td>
                                <span id="intern-ln-label-${i.id}" style="font-weight:600">${i.last_name}</span>
                                <input id="intern-ln-input-${i.id}" class="form-control" value="${i.last_name}"
                                  style="display:none;padding:5px 8px;font-size:13px;min-width:90px"
                                  onkeydown="if(event.key==='Enter')saveIntern('${i.id}');if(event.key==='Escape')cancelEditIntern('${i.id}','${i.first_name}','${i.last_name}','${i.department_id}')" />
                              </td>
                              <!-- DEPT: display / edit -->
                              <td>
                                <span id="intern-dept-label-${i.id}">${dName}</span>
                                <select id="intern-dept-select-${i.id}" class="form-control"
                                  style="display:none;padding:5px 8px;font-size:13px;min-width:120px">
                                  ${deptOptions}
                                </select>
                              </td>
                              <!-- BADGE -->
                              <td>
                                <button class="btn btn-badge" style="padding:4px 10px;font-size:11px"
                                  onclick="generateBadgePDF('${i.id}','${i.first_name} ${i.last_name}','${dName}')">
                                  <span class="material-symbols-outlined" style="font-size:13px">badge</span> PDF
                                </button>
                              </td>
                              <!-- ACTIONS -->
                              <td>
                                <div style="display:flex;gap:6px">
                                  <button id="intern-edit-btn-${i.id}" class="btn btn-ghost" style="padding:4px 10px;font-size:11px" onclick="startEditIntern('${i.id}')" title="Modifier">
                                    <span class="material-symbols-outlined" style="font-size:13px">edit</span>
                                  </button>
                                  <button id="intern-save-btn-${i.id}" class="btn btn-primary" style="padding:4px 10px;font-size:11px;display:none" onclick="saveIntern('${i.id}')">
                                    <span class="material-symbols-outlined" style="font-size:13px">check</span>
                                  </button>
                                  <button id="intern-cancel-btn-${i.id}" class="btn btn-ghost" style="padding:4px 10px;font-size:11px;display:none" onclick="cancelEditIntern('${i.id}','${i.first_name}','${i.last_name}','${i.department_id}')">
                                    <span class="material-symbols-outlined" style="font-size:13px">close</span>
                                  </button>
                                  <button class="btn btn-danger" style="padding:4px 10px;font-size:11px"
                                    onclick="confirmDeleteIntern('${i.id}','${i.first_name} ${i.last_name}')">
                                    <span class="material-symbols-outlined" style="font-size:13px">delete</span>
                                  </button>
                                </div>
                              </td>
                            </tr>`;
                            })
                            .join("")}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <div class="card">
                    <div class="card-header"><h3>Ajouter un Stagiaire</h3></div>
                    <div class="card-body">
                      <div id="add-intern-msg"></div>
                      <div class="form-group"><label class="form-label">Prénom</label><input class="form-control" id="inp-fn" placeholder="Prénom"/></div>
                      <div class="form-group"><label class="form-label">Nom</label><input class="form-control" id="inp-ln" placeholder="Nom de famille"/></div>
                      <div class="form-group"><label class="form-label">Service</label>
                        <select class="form-control" id="inp-dept">
                          ${isChefService() ? `<option value="${AUTH.department_id}">${depts.length > 0 ? depts[0].name : 'Mon Service'}</option>` : (depts.length === 0 ? '<option value="" disabled>— Aucun service disponible —</option>' : depts.map((d) => `<option value="${d.id}">${d.name}</option>`).join(""))}
                        </select>
                      </div>
                      <button class="btn btn-primary" style="width:100%;justify-content:center;padding:12px" onclick="addIntern()" ${depts.length === 0 ? "disabled" : ""}>
                        <span class="material-symbols-outlined">person_add</span> Enregistrer
                      </button>
                      ${depts.length === 0 ? '<div class="alert alert-warn" style="margin-top:12px"><span class="material-symbols-outlined" style="font-size:16px">warning</span> Créez d\'abord un service dans l\'onglet Services.</div>' : ""}
                      <div style="margin-top:16px;padding:12px;background:var(--surface2);border-radius:var(--radius);border:1px solid var(--border)">
                        <div style="font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;color:var(--text-f);margin-bottom:4px">ℹ Modifier un stagiaire</div>
                        <p style="font-size:12px;color:var(--text-m)">Cliquez ✏️ sur une ligne pour modifier le nom ou le service. Confirmez avec ✓ ou annulez avec ✕. Vous pouvez aussi double-cliquer sur le nom.</p>
                      </div>
                    </div>
                  </div>
                </div>`;

        // Wire up double-click to edit on name cells
        interns.forEach((i) => {
          const fn = document.getElementById(`intern-fn-label-${i.id}`);
          const ln = document.getElementById(`intern-ln-label-${i.id}`);
          if (fn) fn.addEventListener("dblclick", () => startEditIntern(i.id));
          if (ln) ln.addEventListener("dblclick", () => startEditIntern(i.id));
        });
      }

      function filterAdminInterns() {
        const input = document.getElementById('admin-intern-search');
        const term = input ? normalizeSearchText(input.value.trim()) : '';
        document.querySelectorAll('[data-admin-intern-search]').forEach((row) => {
          const haystack = normalizeSearchText(row.getAttribute('data-admin-intern-search') || '');
          row.style.display = haystack.includes(term) ? '' : 'none';
        });
      }

      function startEditIntern(id) {
        // show inputs, hide labels
        ["fn", "ln"].forEach((f) => {
          document.getElementById(`intern-${f}-label-${id}`).style.display =
            "none";
          document.getElementById(`intern-${f}-input-${id}`).style.display =
            "block";
        });
        // Chef de Service ne peut pas changer le service
        document.getElementById(`intern-dept-label-${id}`).style.display =
          "none";
        const deptSelect = document.getElementById(`intern-dept-select-${id}`);
        deptSelect.style.display = "block";
        if (isChefService()) {
          deptSelect.disabled = true;
        }
        document.getElementById(`intern-edit-btn-${id}`).style.display = "none";
        document.getElementById(`intern-save-btn-${id}`).style.display =
          "inline-flex";
        document.getElementById(`intern-cancel-btn-${id}`).style.display =
          "inline-flex";
        document.getElementById(`intern-fn-input-${id}`).focus();
      }

      function cancelEditIntern(id, origFn, origLn, origDeptId) {
        document.getElementById(`intern-fn-input-${id}`).value = origFn;
        document.getElementById(`intern-ln-input-${id}`).value = origLn;
        const sel = document.getElementById(`intern-dept-select-${id}`);
        if (sel) sel.value = origDeptId;
        ["fn", "ln"].forEach((f) => {
          document.getElementById(`intern-${f}-label-${id}`).style.display = "";
          document.getElementById(`intern-${f}-input-${id}`).style.display =
            "none";
        });
        document.getElementById(`intern-dept-label-${id}`).style.display = "";
        document.getElementById(`intern-dept-select-${id}`).style.display =
          "none";
        document.getElementById(`intern-edit-btn-${id}`).style.display =
          "inline-flex";
        document.getElementById(`intern-save-btn-${id}`).style.display = "none";
        document.getElementById(`intern-cancel-btn-${id}`).style.display =
          "none";
      }

      async function saveIntern(id) {
        const first_name = document
          .getElementById(`intern-fn-input-${id}`)
          .value.trim();
        const last_name = document
          .getElementById(`intern-ln-input-${id}`)
          .value.trim();
        const department_id = document.getElementById(
          `intern-dept-select-${id}`,
        ).value;
        if (!first_name || !last_name) {
          showToast("Le nom ne peut pas être vide", "error");
          return;
        }
        try {
          const res = await apiFetch(`/interns/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ first_name, last_name, department_id }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur");
          showToast(`${first_name} ${last_name} mis à jour`, "success");

          // Update DATA in-place
          const intern = DATA.interns.find((i) => i.id === id);
          if (intern) {
            intern.first_name = first_name;
            intern.last_name = last_name;
            intern.department_id = department_id;
          }

          // Update labels in-place
          document.getElementById(`intern-fn-label-${id}`).textContent =
            first_name;
          document.getElementById(`intern-ln-label-${id}`).textContent =
            last_name;
          const dept = DATA.departments.find((d) => d.id === department_id);
          const deptName = dept ? dept.name : "—";
          document.getElementById(`intern-dept-label-${id}`).textContent =
            deptName;
          const row = document.getElementById(`intern-row-${id}`);
          if (row) row.setAttribute('data-admin-intern-search', normalizeSearchText(`${first_name} ${last_name} ${deptName}`));

          // Refresh badge button onclick with updated name + department
          const badgeBtn = document.querySelector(
            `#intern-row-${id} .btn-badge`,
          );
          if (badgeBtn) {
            badgeBtn.onclick = () =>
              generateBadgePDF(id, `${first_name} ${last_name}`, deptName);
          }

          cancelEditIntern(id, first_name, last_name, department_id);
        } catch (e) {
          showToast(e.message, "error");
        }
      }

      async function addIntern() {
        const first_name = document.getElementById("inp-fn").value.trim();
        const last_name = document.getElementById("inp-ln").value.trim();
        const department_id = document.getElementById("inp-dept").value;
        const msgEl = document.getElementById("add-intern-msg");
        if (!first_name || !last_name) {
          msgEl.innerHTML =
            '<div class="alert alert-error">Veuillez remplir tous les champs.</div>';
          return;
        }
        try {
          const res = await apiFetch("/interns/add", {
            method: "POST",
            body: JSON.stringify({ first_name, last_name, department_id }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur serveur");
          showToast(`${first_name} ${last_name} ajouté(e)`, "success");
          document.getElementById("inp-fn").value = "";
          document.getElementById("inp-ln").value = "";
          await loadData();
          renderAdminInterns();
        } catch (e) {
          msgEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
        }
      }

      function confirmDeleteIntern(id, name) {
        openModal(
          "Supprimer ce stagiaire ?",
          `Êtes-vous sûr de vouloir supprimer <strong style="color:#fff">${name}</strong> ? Cette action est irréversible.`,
          `<button class="btn btn-danger" onclick="deleteIntern('${id}')"><span class="material-symbols-outlined">delete_forever</span> Supprimer</button><button class="btn btn-ghost" onclick="closeModal()">Annuler</button>`,
        );
      }
      async function deleteIntern(id) {
        try {
          const res = await apiFetch(`/interns/${id}`, { method: "DELETE" });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur");
          showToast(data.message || "Supprimé", "success");
          closeModal();
          await loadData();
          renderAdminInterns();
        } catch (e) {
          showToast(e.message, "error");
          closeModal();
        }
      }

