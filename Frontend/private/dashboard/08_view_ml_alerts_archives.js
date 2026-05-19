      // ── CLUSTERS & ML ────────────────────────────────────────────────────────
      function filterPlanningRotations() {
        const input = document.getElementById('planning-search');
        const term = input ? normalizeSearchText(input.value.trim()) : '';
        document.querySelectorAll('.planning-dept').forEach((dept) => {
          const haystack = normalizeSearchText(dept.getAttribute('data-planning-search') || '');
          dept.style.display = haystack.includes(term) ? '' : 'none';
        });
      }

      function renderClusters() {
        document.getElementById("view-container").innerHTML = `
                <div class="grid3">
                  <div class="card">
                    <div class="card-header"><div><h3>Analyse Comportementale ML</h3><p>Visualisation PCA — données de présence</p></div><div style="display:flex;gap:8px"><button class="toggle-btn active" id="kmeans-btn" onclick="setAlgoActive('kmeans')">K-MEANS</button><button class="toggle-btn" id="dbscan-btn" onclick="setAlgoActive('dbscan')">DBSCAN</button></div></div>
                    <div class="card-body"><div class="chart-wrap" style="height:420px"><canvas id="ch-pca"></canvas></div></div>
                  </div>
                  <div style="display:flex;flex-direction:column;gap:0">
                    <div class="card"><div class="card-header"><h3>Segments Détectés</h3></div><div class="card-body">
                      ${[
                        {
                          label: "Cluster Alpha — Profils Fiables",
                          color: "#45f1c3",
                          pct: 65,
                          desc: "Régularité exemplaire, scans stables. Faible variabilité horaire.",
                        },
                        {
                          label: "Cluster Beta — Instabilité Modérée",
                          color: "#ffcea6",
                          pct: 25,
                          desc: "Horaires variables, anomalies mineures fréquentes.",
                        },
                        {
                          label: "Cluster Gamma — Profils à Risque",
                          color: "#ffb4ab",
                          pct: 10,
                          desc: "Retards fréquents, absences prolongées.",
                        },
                      ]
                        .map(
                          (c) =>
                            `<div class="cluster-segment"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px"><h4>${c.label}</h4><span style="font-family:'DM Mono',monospace;font-size:11px;color:${c.color}">${c.pct}%</span></div><p>${c.desc}</p><div class="cluster-bar"><div style="width:${c.pct}%;background:${c.color}"></div></div></div>`,
                        )
                        .join("")}
                      <div style="background:var(--primary-d);border:1px solid var(--primary-g);border-radius:var(--radius);padding:12px;margin-top:4px"><div style="font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;color:var(--primary);letter-spacing:.1em;margin-bottom:4px">Shadow Mode Actif</div><p style="font-size:12px;color:var(--text-m)">Modèle entraîné sur données synthétiques. Résultats indicatifs seulement.</p></div>
                    </div></div>
                  </div>
                </div>`;

        nextTick(() => {
          function genCluster(cx, cy, n, s = 1.5) {
            return Array.from({ length: n }, () => ({
              x: cx + (Math.random() - 0.5) * s,
              y: cy + (Math.random() - 0.5) * s,
            }));
          }
          CHARTS["pca"] = new Chart(document.getElementById("ch-pca"), {
            type: "scatter",
            data: {
              datasets: [
                {
                  label: "Alpha (Fiables)",
                  data: genCluster(
                    -2,
                    -1.5,
                    Math.round(activeInterns().length * 0.65 || 10),
                  ),
                  backgroundColor: "rgba(69,241,195,.7)",
                  pointRadius: 6,
                },
                {
                  label: "Beta (Modéré)",
                  data: genCluster(
                    2,
                    2,
                    Math.round(activeInterns().length * 0.25 || 4),
                  ),
                  backgroundColor: "rgba(255,206,166,.7)",
                  pointRadius: 6,
                },
                {
                  label: "Gamma (Risque)",
                  data: genCluster(
                    3,
                    -3,
                    Math.round(activeInterns().length * 0.1 || 2),
                  ),
                  backgroundColor: "rgba(255,180,171,.7)",
                  pointRadius: 6,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  labels: {
                    color: "#dce4df",
                    usePointStyle: true,
                    font: { size: 11 },
                  },
                },
              },
              scales: {
                x: {
                  grid: { color: "#1a2130" },
                  ticks: { color: "#85948d", font: { size: 10 } },
                },
                y: {
                  grid: { color: "#1a2130" },
                  ticks: { color: "#85948d", font: { size: 10 } },
                },
              },
            },
          });
        });
      }
      function setAlgoActive(algo) {
        document
          .getElementById("kmeans-btn")
          .classList.toggle("active", algo === "kmeans");
        document
          .getElementById("dbscan-btn")
          .classList.toggle("active", algo === "dbscan");
      }

      // ── JOURNAL DES ALERTES ──────────────────────────────────────────────────
      function renderAlerts() {
        const interns = getVisibleInterns();
        const history = getVisibleHistory();
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const pending = interns
          .filter((i) => i.end_date)
          .filter((i) => {
            const end = new Date(i.end_date);
            end.setHours(0, 0, 0, 0);
            return end <= today;
          })
          .sort((a, b) => new Date(a.end_date) - new Date(b.end_date));
        const alerts = history
          .filter((h) => h.needs_attention)
          .sort((a, b) => new Date(b.date) - new Date(a.date));

        document.getElementById("view-container").innerHTML = `
                <div class="grid2" style="grid-template-columns:1fr;">
                  <div class="card" style="margin-bottom:20px">
                    <div class="card-header" style="padding-bottom:16px">
                      <div><h3>Stages à traiter</h3><p>${pending.length} stagiaire(s) dont le stage est terminé ou à archiver</p></div>
                    </div>
                    <div class="card-body" style="padding-top:0">
                      ${
                        pending.length === 0
                          ? '<div class="empty-state"><span class="material-symbols-outlined">check_circle</span><p>Aucun stage en attente d\'archivage.</p></div>'
                          : `
                      <div class="table-responsive"><table class="data-table"><thead><tr><th>Stagiaire</th><th>Service</th><th>Fin de stage</th><th>Actions</th></tr></thead><tbody>
                        ${pending
                          .map((i) => {
                            const name = `${i.first_name} ${i.last_name}`;
                            return `<tr><td style="font-weight:600">${name}</td><td>${internDepartmentName(i)}</td><td style="font-family:'DM Mono',monospace;font-size:12px">${fmtDateShort(i.end_date)}</td><td><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-danger btn-sm" onclick="archiveIntern('${i.id}')">Archiver</button><button class="btn btn-ghost btn-sm" onclick="promptProlongIntern('${i.id}')">Prolonger</button></div></td></tr>`;
                          })
                          .join("")}
                      </tbody></table></div>`
                      }
                    </div>
                  </div>
                  <div class="card">
                    <div class="card-header" style="padding-bottom:16px">
                      <div><h3>Journal des Anomalies</h3><p>${alerts.length} événement(s) nécessitant attention</p></div>
                      ${
                        isDFRI()
                          ? `
                      <div style="display:flex;gap:8px">
                        <button class="btn btn-danger" onclick="markAbsences()"><span class="material-symbols-outlined">event_busy</span> Marquer absences du jour</button>
                        <button class="btn btn-ghost" onclick="undoAbsences()"><span class="material-symbols-outlined">undo</span> Annuler les absences</button>
                      </div>`
                          : ""
                      }
                    </div>
                    <div class="card-body" style="padding-top:0">
                      ${
                        alerts.length === 0
                          ? '<div class="empty-state"><span class="material-symbols-outlined">check_circle</span><p>Aucune anomalie détectée — tout est nominal.</p></div>'
                          : `
                    <div id="alerts-msg"></div>
                    <table class="data-table"><thead><tr><th>Date</th><th>Stagiaire</th><th>Arrivée</th><th>Départ</th><th>Durée</th><th>Statut</th></tr></thead><tbody>
                      ${alerts
                        .map((h) => {
                          const intern = interns.find(
                            (i) => i.id === h.intern_id,
                          );
                          const name = intern
                            ? `${intern.first_name} ${intern.last_name}`
                            : h.intern_id.substring(0, 8) + "…";
                          return `<tr><td style="font-family:'DM Mono',monospace;font-size:11px">${fmtDate(h.date)}</td><td style="font-weight:600">${name}</td><td style="font-family:'DM Mono',monospace;font-size:12px">${fmtTime(h.arrival_time)}</td><td style="font-family:'DM Mono',monospace;font-size:12px">${fmtTime(h.departure_time)}</td><td style="color:var(--text-m);font-size:12px">${(h.work_duration || 0).toFixed(1)}h</td><td>${statusBadge(h.status, h.needs_attention)}</td></tr>`;
                        })
                        .join("")}
                    </tbody></table>`
                      }
                    </div>
                  </div>
                </div>`;
      }

      async function markAbsences() {
        try {
          const res = await apiFetch("/admin/mark-absences", {
            method: "POST",
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur serveur");
          showToast(data.message || "Absences marquées", "success");
          await loadData();
          renderAlerts();
        } catch (e) {
          showToast(e.message, "error");
        }
      }

      async function undoAbsences() {
        try {
          const res = await apiFetch("/admin/undo-absences", {
            method: "DELETE",
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur serveur");
          showToast(data.message || "Absences annulées", "success");
          await loadData();
          renderAlerts();
        } catch (e) {
          showToast(e.message, "error");
        }
      }

      async function archiveIntern(internId) {
        try {
          const res = await apiFetch(`/interns/${internId}/archive`, {
            method: "POST",
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur serveur");
          showToast(data.message || "Stagiaire archivé", "success");
          await loadData();
          if (CURRENT_VIEW === "archives") renderArchives();
          else renderAlerts();
        } catch (e) {
          showToast(e.message, "error");
        }
      }

      async function promptProlongIntern(internId) {
        const intern = activeInterns().find((i) => i.id === internId);
        if (!intern) {
          showToast("Stagiaire introuvable.", "error");
          return;
        }
        const currentDate = intern.end_date || new Date().toISOString().slice(0, 10);
        const newEndDate = prompt(
          "Nouvelle date de fin (AAAA-MM-JJ)",
          currentDate,
        );
        if (!newEndDate) return;
        if (!/^\d{4}-\d{2}-\d{2}$/.test(newEndDate)) {
          showToast("Format de date invalide. Utilisez AAAA-MM-JJ.", "error");
          return;
        }
        const parsed = new Date(newEndDate + "T00:00:00");
        if (Number.isNaN(parsed.getTime())) {
          showToast("Date invalide.", "error");
          return;
        }
        if (intern.end_date && parsed < new Date(intern.end_date + "T00:00:00")) {
          showToast("La nouvelle date doit être égale ou postérieure à la date actuelle.", "error");
          return;
        }
        try {
          const res = await apiFetch(`/interns/${internId}`, {
            method: "PATCH",
            body: JSON.stringify({ end_date: newEndDate }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur serveur");
          showToast("Date de fin prolongée.", "success");
          await loadData();
          renderAlerts();
        } catch (e) {
          showToast(e.message, "error");
        }
      }

      function renderArchives() {
        let depts = DATA.departments || [];
        let interns = archivedInterns();
        if (isChefService()) {
          interns = interns.filter((i) => i.department_id === AUTH.department_id);
          depts = depts.filter((d) => d.id === AUTH.department_id);
        }
        const selectedDept = document.getElementById("archive-service-filter")?.value || "";
        const searchTerm = (document.getElementById("archive-search")?.value || "").trim().toLowerCase();
        const filtered = interns.filter((i) => {
          const matchesDept = !selectedDept || i.department_id === selectedDept;
          const haystack = `${i.first_name} ${i.last_name} ${internDepartmentName(i)} ${i.end_date || ""}`.toLowerCase();
          return matchesDept && haystack.includes(searchTerm);
        });

        document.getElementById("view-container").innerHTML = `
                <div class="card">
                  <div class="card-header" style="padding-bottom:16px">
                    <div><h3>Stagiaires Archivés</h3><p>${interns.length} stagiaire(s) archivés</p></div>
                  </div>
                  <div class="card-body" style="padding-top:0">
                    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
                      <div style="min-width:220px;flex:1;display:flex;align-items:center;background:var(--surface-d);border:1px solid var(--border);border-radius:8px;padding:0 12px">
                        <span class="material-symbols-outlined" style="color:var(--text-m);margin-right:8px">search</span>
                        <input id="archive-search" class="form-control" placeholder="Rechercher un stagiaire..." style="border:none;background:transparent;color:#fff;font-size:14px;padding:10px 0;width:100%;outline:none" oninput="renderArchives()" />
                      </div>
                      <div style="min-width:220px;display:flex;align-items:center;background:var(--surface-d);border:1px solid var(--border);border-radius:8px;padding:0 12px">
                        <span class="material-symbols-outlined" style="color:var(--text-m);margin-right:8px">business</span>
                        <select id="archive-service-filter" class="form-control" onchange="renderArchives()" style="border:none;background:transparent;color:#fff;font-size:14px;padding:10px 0;width:100%;outline:none">
                          <option value="">Tous les services</option>
                          ${depts
                            .map((d) => `<option value="${d.id}" ${d.id === selectedDept ? "selected" : ""}>${d.name}</option>`)
                            .join("")}
                        </select>
                      </div>
                    </div>
                    ${
                      filtered.length === 0
                        ? '<div class="empty-state"><span class="material-symbols-outlined">archive</span><p>Aucun stagiaire archivé ne correspond aux filtres.</p></div>'
                        : `
                    <div class="table-responsive"><table class="data-table"><thead><tr><th>Nom</th><th>Service</th><th>Fin de stage</th></tr></thead><tbody>
                      ${filtered
                        .map((i) => `<tr><td style="font-weight:600">${i.first_name} ${i.last_name}</td><td>${internDepartmentName(i)}</td><td style="font-family:'DM Mono',monospace;font-size:12px">${fmtDateShort(i.end_date)}</td></tr>`)
                        .join("")}
                    </tbody></table></div>`
                    }
                  </div>
                </div>`;
      }

