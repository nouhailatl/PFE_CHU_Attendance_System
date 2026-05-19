      // ── VUE INDIVIDUELLE ─────────────────────────────────────────────────────
      function renderIndividual() {
        const interns = getVisibleInterns();
        const history = getVisibleHistory();
        if (!SELECTED_INTERN && interns.length) SELECTED_INTERN = interns[0].id;
        const intern =
          interns.find((i) => i.id === SELECTED_INTERN) || interns[0];
        if (!intern) {
          document.getElementById("view-container").innerHTML =
            '<div class="empty-state"><span class="material-symbols-outlined">person_off</span><p>Aucun stagiaire trouvé.</p></div>';
          return;
        }
        const internHistory = history
          .filter((h) => h.intern_id === intern.id)
          .sort((a, b) => new Date(b.date) - new Date(a.date));
        const presentDays = internHistory.filter(
          (h) => h.status !== "absent",
        ).length;
        const totalDays = internHistory.length;
        const rate = totalDays
          ? Math.round((presentDays / totalDays) * 100)
          : 0;
        const avgDur = internHistory.length
          ? (
              internHistory.reduce((s, h) => s + (h.work_duration || 0), 0) /
              internHistory.length
            ).toFixed(1)
          : 0;
        const risk = 100 - rate;
        const riskColor =
          risk < 30 ? "#45f1c3" : risk < 60 ? "#ffcea6" : "#ffb4ab";
        const dept = (DATA.departments || []).find(
          (d) => d.id === intern.department_id,
        );
        const deptName = dept ? dept.name : "—";
        const chartDays = internHistory.slice(0, 14).reverse();
        const chartDates = chartDays.map((h) => fmtDate(h.date));
        const chartDurs = chartDays.map((h) => h.work_duration || 0);

        document.getElementById("view-container").innerHTML = `
                ${renderFilterBar()}
                <div class="grid3" style="align-items:start">
                  <div style="display:flex;flex-direction:column;gap:16px">
                    <div class="card card-body">
                      <label class="form-label" style="margin-bottom:8px">Sélectionner un stagiaire</label>
                      <select class="form-control" onchange="SELECTED_INTERN=this.value;switchView('individual')">
                        ${interns.map((i) => `<option value="${i.id}" ${i.id === intern.id ? "selected" : ""}>${i.first_name} ${i.last_name}</option>`).join("")}
                      </select>
                      <div style="text-align:center;margin-top:20px">
                        <div class="profile-avatar" style="width:64px;height:64px;border-radius:16px;font-size:22px;margin:0 auto 12px">${initials(intern.first_name, intern.last_name)}</div>
                        <div style="font-family:'Syne',sans-serif;font-size:17px;font-weight:700;color:#fff">${intern.first_name} ${intern.last_name}</div>
                        <div style="color:var(--text-f);font-size:12px;margin:4px 0 10px">${deptName}</div>
                        <!-- ★ Badge download button in individual view -->
                        <button class="btn btn-badge" style="margin:0 auto;justify-content:center"
                          onclick="generateBadgePDF('${intern.id}','${intern.first_name} ${intern.last_name}','${deptName}')">
                          <span class="material-symbols-outlined">badge</span> Télécharger Badge PDF
                        </button>
                      </div>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px;padding-top:16px;border-top:1px solid var(--border)">
                        <div style="text-align:center;background:var(--surface2);border-radius:var(--radius);padding:12px"><div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:700;color:var(--primary)">${rate}%</div><div style="font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;color:var(--text-f)">Présence</div></div>
                        <div style="text-align:center;background:var(--surface2);border-radius:var(--radius);padding:12px"><div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:700;color:#fff">${avgDur}h</div><div style="font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;color:var(--text-f)">Moy/jour</div></div>
                      </div>
                    </div>
                    <div class="card card-body">
                      <div style="font-family:'DM Mono',monospace;font-size:10px;text-transform:uppercase;color:var(--text-m);margin-bottom:12px">Indice de Risque</div>
                      <div class="risk-gauge">
                        <svg viewBox="0 0 160 85">
                          <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="#1a2130" stroke-width="10" stroke-linecap="round"/>
                          <path d="M 20 80 A 60 60 0 0 1 140 80" fill="none" stroke="${riskColor}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${risk * 1.88} 188"/>
                          <text x="80" y="78" text-anchor="middle" font-family="Syne" font-size="24" font-weight="700" fill="${riskColor}">${risk}</text>
                          <text x="80" y="90" text-anchor="middle" font-family="DM Mono" font-size="8" fill="#85948d">/ 100</text>
                        </svg>
                        <div class="risk-label">${risk < 30 ? "Risque Faible ✓" : risk < 60 ? "Risque Modéré" : "Risque Élevé !"}</div>
                      </div>
                    </div>
                  </div>
                  <div style="display:flex;flex-direction:column;gap:16px">
                    <div class="card"><div class="card-header"><h3>Activité — 14 derniers jours</h3></div><div class="card-body"><div class="chart-wrap" style="height:240px"><canvas id="ch-ind"></canvas></div></div></div>
                    <div class="card">
                      <div class="card-header" style="margin-bottom:0"><h3>Historique des pointages</h3></div>
                      <div class="card-body" style="overflow-x:auto">
                        <table class="data-table"><thead><tr><th>Date</th><th>Arrivée</th><th>Départ</th><th>Durée</th><th>Statut</th></tr></thead><tbody>
                          ${internHistory
                            .slice(0, 20)
                            .map(
                              (h) =>
                                `<tr><td style="font-family:'DM Mono',monospace;font-size:11px">${fmtDate(h.date)}</td><td style="font-family:'DM Mono',monospace;font-size:12px">${fmtTime(h.arrival_time)}</td><td style="font-family:'DM Mono',monospace;font-size:12px">${fmtTime(h.departure_time)}</td><td style="font-weight:600;color:var(--primary)">${(h.work_duration || 0).toFixed(1)}h</td><td>${statusBadge(h.status, h.needs_attention)}</td></tr>`,
                            )
                            .join("")}
                        </tbody></table>
                        ${!internHistory.length ? '<div class="empty-state"><p>Aucun enregistrement pour ce stagiaire.</p></div>' : ""}
                      </div>
                    </div>
                  </div>
                </div>`;

        nextTick(() => {
          CHARTS["ind"] = new Chart(document.getElementById("ch-ind"), {
            type: "bar",
            data: {
              labels: chartDates,
              datasets: [
                {
                  label: "Heures travaillées",
                  data: chartDurs,
                  backgroundColor: "rgba(69,241,195,.6)",
                  borderColor: "#45f1c3",
                  borderWidth: 1,
                  borderRadius: 4,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                y: {
                  grid: { color: "#1a2130" },
                  ticks: { color: "#85948d", font: { size: 10 } },
                  min: 0,
                },
                x: {
                  grid: { display: false },
                  ticks: {
                    color: "#85948d",
                    font: { size: 10 },
                    maxTicksLimit: 7,
                  },
                },
              },
            },
          });
        });
      }

