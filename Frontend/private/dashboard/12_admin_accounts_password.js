      // ── ACCOUNTS TAB ─────────────────────────────────────────────────────────
      function renderAdminAccounts() {
        const admins = DATA.admins || [];
        const depts = DATA.departments || [];
        document.getElementById("admin-content").innerHTML = `
                <div class="grid2" style="align-items:start">
                  <div class="card">
                    <div class="card-header"><h3>Comptes Administrateurs</h3></div>
                    <div class="card-body" style="padding-top:0">
                      <table class="data-table"><thead><tr><th>Identifiant</th><th>Rôle</th><th>Service</th><th></th></tr></thead><tbody>
                        ${admins
                          .map((a) => {
                            const dept = depts.find(
                              (d) => d.id === a.department_id,
                            );
                            const isMe = a.username === AUTH.username;
                            const roleLabels = {
                              "dfri": "Directeur IT",
                              "directeur": "Directeur",
                              "chef_service": "Chef de Service",
                              "secretaire": "Secrétaire"
                            };
                            const roleBadgeColors = {
                              "dfri": "badge-green",
                              "directeur": "badge-blue",
                              "chef_service": "badge-orange",
                              "secretaire": "badge-grey"
                            };
                            return `<tr><td style="font-weight:600">${a.username}${isMe ? ' <span style="font-size:10px;color:var(--primary)">(moi)</span>' : ""}</td><td><span class="badge ${roleBadgeColors[a.role] || 'badge-grey'}">${roleLabels[a.role] || a.role}</span></td><td style="font-size:12px;color:var(--text-m)">${dept ? dept.name : "—"}</td><td>${!isMe ? `<button class="btn btn-danger" style="padding:4px 10px;font-size:11px" onclick="confirmDeleteAdmin('${a.id}','${a.username}')"><span class="material-symbols-outlined" style="font-size:13px">delete</span></button>` : ""}</td></tr>`;
                          })
                          .join("")}
                      </tbody></table>
                    </div>
                  </div>
                  <div class="card">
                    <div class="card-header"><h3>Créer un Compte</h3></div>
                    <div class="card-body">
                      <div id="create-admin-msg"></div>
                      <div class="form-group"><label class="form-label">Identifiant</label><input class="form-control" id="ca-user" placeholder="nom_utilisateur"/></div>
                      <div class="form-group"><label class="form-label">Mot de passe (min. 8 car.)</label><input class="form-control" id="ca-pwd" type="password" placeholder="••••••••"/></div>
                      <div class="form-group"><label class="form-label">Rôle</label><select class="form-control" id="ca-role" onchange="toggleDeptField()"><option value="secretaire">Secrétaire</option><option value="directeur">Directeur</option><option value="chef_service">Chef de Service</option><option value="dfri">Directeur IT</option></select></div>
                      <div class="form-group" id="ca-dept-group" style="display:none"><label class="form-label">Service (obligatoire pour Chef de Service)</label><select class="form-control" id="ca-dept">${depts.map((d) => `<option value="${d.id}">${d.name}</option>`).join("")}</select></div>
                      <button class="btn btn-primary" style="width:100%;justify-content:center;padding:12px" onclick="createAdmin()"><span class="material-symbols-outlined">person_add</span> Créer le compte</button>
                    </div>
                  </div>
                </div>`;
      }

      function toggleDeptField() {
        const role = document.getElementById("ca-role").value;
        document.getElementById("ca-dept-group").style.display =
          role === "chef_service" ? "block" : "none";
      }

      async function createAdmin() {
        const username = document.getElementById("ca-user").value.trim();
        const password = document.getElementById("ca-pwd").value;
        const role = document.getElementById("ca-role").value;
        const department_id =
          role === "chef_service"
            ? document.getElementById("ca-dept").value
            : null;
        const msgEl = document.getElementById("create-admin-msg");
        if (!username || !password) {
          msgEl.innerHTML =
            '<div class="alert alert-error">Identifiant et mot de passe requis.</div>';
          return;
        }
        if (password.length < 8) {
          msgEl.innerHTML =
            '<div class="alert alert-error">Mot de passe trop court (min. 8 car.).</div>';
          return;
        }
        if (role === "chef_service" && !department_id) {
          msgEl.innerHTML =
            '<div class="alert alert-error">Un Chef de Service doit avoir un service assign.</div>';
          return;
        }
        try {
          const res = await apiFetch("/auth/create-admin", {
            method: "POST",
            body: JSON.stringify({ username, password, role, department_id }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur");
          showToast(`Compte '${username}' créé`, "success");
          document.getElementById("ca-user").value = "";
          document.getElementById("ca-pwd").value = "";
          const admRes = await apiFetch("/auth/admins");
          DATA.admins = admRes.ok ? await admRes.json() : DATA.admins;
          renderAdminAccounts();
        } catch (e) {
          msgEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
        }
      }

      function confirmDeleteAdmin(id, username) {
        openModal(
          "Supprimer ce compte ?",
          `Êtes-vous sûr de vouloir supprimer le compte <strong style="color:#fff">${username}</strong> ?`,
          `<button class="btn btn-danger" onclick="deleteAdmin('${id}')"><span class="material-symbols-outlined">delete_forever</span> Supprimer</button><button class="btn btn-ghost" onclick="closeModal()">Annuler</button>`,
        );
      }
      async function deleteAdmin(id) {
        try {
          const res = await apiFetch(`/auth/admins/${id}`, {
            method: "DELETE",
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur");
          showToast(data.message || "Compte supprimé", "success");
          closeModal();
          const admRes = await apiFetch("/auth/admins");
          DATA.admins = admRes.ok ? await admRes.json() : DATA.admins;
          renderAdminAccounts();
        } catch (e) {
          showToast(e.message, "error");
          closeModal();
        }
      }

      // ── PASSWORD TAB ─────────────────────────────────────────────────────────
      function renderAdminPwd() {
        document.getElementById("admin-content").innerHTML = `
                <div style="max-width:440px">
                  <div class="card">
                    <div class="card-header"><h3>Changer mon mot de passe</h3></div>
                    <div class="card-body">
                      <div id="pwd-msg"></div>
                      <div class="form-group"><label class="form-label">Mot de passe actuel</label><input class="form-control" id="pwd-cur" type="password" placeholder="••••••••"/></div>
                      <div class="form-group"><label class="form-label">Nouveau mot de passe</label><input class="form-control" id="pwd-new" type="password" placeholder="••••••••"/></div>
                      <div class="form-group"><label class="form-label">Confirmer le nouveau mot de passe</label><input class="form-control" id="pwd-new2" type="password" placeholder="••••••••"/></div>
                      <button class="btn btn-primary" style="width:100%;justify-content:center;padding:12px" onclick="changePwd()"><span class="material-symbols-outlined">lock_reset</span> Mettre à jour</button>
                    </div>
                  </div>
                </div>`;
      }

      async function changePwd() {
        const current_password = document.getElementById("pwd-cur").value;
        const new_password = document.getElementById("pwd-new").value;
        const confirm = document.getElementById("pwd-new2").value;
        const msgEl = document.getElementById("pwd-msg");
        if (new_password !== confirm) {
          msgEl.innerHTML =
            '<div class="alert alert-error">Les mots de passe ne correspondent pas.</div>';
          return;
        }
        if (new_password.length < 8) {
          msgEl.innerHTML =
            '<div class="alert alert-error">Mot de passe trop court (min. 8 car.).</div>';
          return;
        }
        try {
          const res = await apiFetch("/auth/change-password", {
            method: "POST",
            body: JSON.stringify({ current_password, new_password }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur");
          showToast("Mot de passe mis à jour", "success");
          msgEl.innerHTML =
            '<div class="alert alert-success"><span class="material-symbols-outlined">check_circle</span> Mot de passe mis à jour avec succès.</div>';
          document.getElementById("pwd-cur").value = "";
          document.getElementById("pwd-new").value = "";
          document.getElementById("pwd-new2").value = "";
        } catch (e) {
          msgEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
        }
      }

