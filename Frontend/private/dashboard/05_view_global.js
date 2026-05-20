      // ── VUE GLOBALE ──────────────────────────────────────────────────────────
      function renderGlobal() {
        const interns = getVisibleInterns();
        const history = getVisibleHistory();
        
        const depts = DATA.departments || [];
        const today = new Date().toDateString();
        const todayRec = history.filter(
          (h) => new Date(h.date).toDateString() === today,
        );
        const presentToday = new Set(
          todayRec.filter((h) => h.arrival_time).map((h) => h.intern_id),
        ).size;
        const alertCount = history.filter((h) => h.needs_attention).length;
        const dayMap = {};
        history.forEach((h) => {
          const d = fmtDate(h.date);
          if (!dayMap[d]) dayMap[d] = { scans: 0, alerts: 0 };
          dayMap[d].scans++;
          if (h.needs_attention) dayMap[d].alerts++;
        });
        const days = Object.keys(dayMap).slice(-30);
        const scans = days.map((d) => dayMap[d].scans);
        const alerts = days.map((d) => dayMap[d].alerts);
        const weeklyIntensity = renderWeeklyIntensity(history);
        let rFaible = 0,
          rMoyen = 0,
          rEleve = 0;
        const internStatusMap = {};
        history.forEach((h) => {
          if (!internStatusMap[h.intern_id]) internStatusMap[h.intern_id] = 0;
          if (h.needs_attention) internStatusMap[h.intern_id]++;
        });
        interns.forEach((i) => {
          const n = internStatusMap[i.id] || 0;
          if (n === 0) rFaible++;
          else if (n <= 3) rMoyen++;
          else rEleve++;
        });

        document.getElementById("view-container").innerHTML = `
                ${renderFilterBar()}
                <div class="kpi-grid">
                  ${kpiCard("Total Stagiaires", interns.length, "group", "", "primary")}
                  ${kpiCard("Présents Aujourd'hui", presentToday, "how_to_reg", "", "primary")}
                  ${kpiCard("Services", isChefService() ? 1 : depts.length, "corporate_fare", "", "primary")}
                  ${kpiCard("Alertes Actives", alertCount, "warning", "", "error")}
                </div>
                <div class="grid3" style="margin-bottom:16px">
                  <div class="card"><div class="card-header"><div><h3>Activité des Scans (30j)</h3><p>Présences & anomalies quotidiennes</p></div></div><div class="card-body"><div class="chart-wrap" style="height:280px"><canvas id="ch-global"></canvas></div></div></div>
                  <div class="card"><div class="card-header"><div><h3>Répartition Risque</h3></div></div><div class="card-body"><div class="chart-wrap" style="height:280px;display:flex;align-items:center;justify-content:center"><canvas id="ch-donut"></canvas></div></div></div>
                </div>
                <div class="grid2">
                  <div class="card">
                    <div class="card-header" style="padding-bottom:16px"><div><h3>Derniers Scans</h3></div></div>
                    <div class="card-body" style="padding-top:0;overflow-x:auto">
                      <table class="data-table"><thead><tr><th>Stagiaire</th><th>Arrivée</th><th>Départ</th><th>Statut</th></tr></thead><tbody>
                        ${history
                          .slice(-15)
                          .reverse()
                          .map((h) => {
                            const intern = interns.find(
                              (i) => i.id === h.intern_id,
                            );
                            const name = intern
                              ? `${intern.first_name} ${intern.last_name}`
                              : h.intern_id.substring(0, 8) + "…";
                            return `<tr><td><div style="display:flex;align-items:center;gap:8px"><div style="width:28px;height:28px;border-radius:8px;background:var(--primary-d);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--primary)">${name[0]}</div><span style="font-weight:600;font-size:13px">${name}</span></div></td><td style="font-family:'DM Mono',monospace;font-size:12px">${fmtTime(h.arrival_time)}</td><td style="font-family:'DM Mono',monospace;font-size:12px">${fmtTime(h.departure_time)}</td><td>${statusBadge(h.status, h.needs_attention)}</td></tr>`;
                          })
                          .join("")}
                      </tbody></table>
                    </div>
                  </div>
                  <div class="card">
                    <div class="card-header" style="padding-bottom:16px"><div><h3>Activité hebdomadaire</h3><p>Nombre de pointages par jour et tranche horaire</p></div></div>
                    <div class="card-body" style="padding-top:0">
                      ${weeklyIntensity}
                    </div>
                  </div>
                </div>`;

        nextTick(() => {
          CHARTS["global"] = new Chart(document.getElementById("ch-global"), {
            type: "line",
            data: {
              labels: days,
              datasets: [
                {
                  label: "Scans",
                  data: scans,
                  borderColor: "#45f1c3",
                  backgroundColor: "rgba(69,241,195,.08)",
                  fill: true,
                  tension: 0.4,
                  pointRadius: 2,
                },
                {
                  label: "Alertes",
                  data: alerts,
                  borderColor: "#ffb4ab",
                  backgroundColor: "rgba(255,180,171,.08)",
                  fill: true,
                  tension: 0.4,
                  pointRadius: 2,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  labels: {
                    color: "#bacac2",
                    boxWidth: 10,
                    font: { size: 11 },
                  },
                },
              },
              scales: {
                y: {
                  grid: { color: "#1a2130" },
                  ticks: { color: "#85948d", font: { size: 10 } },
                },
                x: {
                  grid: { display: false },
                  ticks: {
                    color: "#85948d",
                    font: { size: 10 },
                    maxTicksLimit: 8,
                  },
                },
              },
            },
          });
          CHARTS["donut"] = new Chart(document.getElementById("ch-donut"), {
            type: "doughnut",
            data: {
              labels: ["Faible", "Moyen", "Élevé"],
              datasets: [
                {
                  data: [rFaible, rMoyen, rEleve],
                  backgroundColor: ["#45f1c3", "#ffcea6", "#ffb4ab"],
                  borderWidth: 0,
                  hoverOffset: 8,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              cutout: "78%",
              plugins: {
                legend: {
                  position: "bottom",
                  labels: {
                    color: "#dce4df",
                    usePointStyle: true,
                    font: { size: 11 },
                  },
                },
              },
            },
          });
        });
      }


      function renderWeeklyIntensity(history) {
        const slots = [
          { label: "08-10", start: 8, end: 10 },
          { label: "10-12", start: 10, end: 12 },
          { label: "12-14", start: 12, end: 14 },
          { label: "14-16", start: 14, end: 16 },
          { label: "16-18", start: 16, end: 18 },
          { label: "18+", start: 18, end: 24 },
        ];
        const dayKeys = [];
        const dayLabels = [];
        for (let offset = 6; offset >= 0; offset--) {
          const day = new Date();
          day.setHours(0, 0, 0, 0);
          day.setDate(day.getDate() - offset);
          dayKeys.push(day.toISOString().slice(0, 10));
          dayLabels.push(day.toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit" }));
        }
        const counts = Object.fromEntries(dayKeys.map((key) => [key, Array(slots.length).fill(0)]));
        history.forEach((entry) => {
          const timestamp = entry.arrival_time || entry.departure_time || entry.date;
          if (!timestamp) return;
          const dt = new Date(timestamp);
          if (Number.isNaN(dt.getTime())) return;
          const key = dt.toISOString().slice(0, 10);
          if (!counts[key]) return;
          const hour = dt.getHours() + dt.getMinutes() / 60;
          const slotIndex = slots.findIndex((slot) => hour >= slot.start && hour < slot.end);
          if (slotIndex >= 0) counts[key][slotIndex] += 1;
        });
        const max = Math.max(1, ...Object.values(counts).flat());
        const colorFor = (value) => {
          if (!value) return "rgba(255,255,255,0.035)";
          const alpha = 0.18 + (value / max) * 0.72;
          return `rgba(69,241,195,${alpha.toFixed(2)})`;
        };
        const rows = dayKeys.map((key, index) => `
          <div style="font-family:'DM Mono',monospace;font-size:10px;color:var(--text-f);align-self:center;text-transform:capitalize">${dayLabels[index]}</div>
          ${counts[key].map((value) => `<div title="${value} pointage${value > 1 ? "s" : ""}" style="height:30px;border-radius:6px;background:${colorFor(value)};border:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;justify-content:center;font-family:'DM Mono',monospace;font-size:10px;color:${value ? '#dce4df' : 'var(--text-f)'}">${value || ""}</div>`).join("")}
        `).join("");
        return `
          <div style="display:grid;grid-template-columns:72px repeat(${slots.length}, minmax(42px,1fr));gap:6px;align-items:center">
            <div></div>
            ${slots.map((slot) => `<div style="font-family:'DM Mono',monospace;font-size:9px;color:var(--text-m);text-align:center">${slot.label}</div>`).join("")}
            ${rows}
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;margin-top:12px;font-size:11px;color:var(--text-f)">
            <span>0 pointage</span>
            <span>Plus l'intensité est forte, plus la case est claire</span>
            <span>${max} max</span>
          </div>`;
      }

      function kpiCard(label, value, icon, trend, color) {
        const iconColor =
          color === "error"
            ? "color:var(--error)"
            : color === "warn"
              ? "color:var(--warn)"
              : "color:var(--primary)";
        return `<div class="kpi-card"><div class="kpi-top"><div class="kpi-label">${label}</div><div class="kpi-icon"><span class="material-symbols-outlined" style="${iconColor}">${icon}</span></div></div><div class="kpi-value">${value}</div><div class="kpi-bg-icon"><span class="material-symbols-outlined">${icon}</span></div></div>`;
      }

