      // ── VUE DÉPARTEMENTALE ───────────────────────────────────────────────────
      function renderDepartment() {
        let depts = DATA.departments || [];
        // Chef de Service: voir seulement son service
        if (isChefService()) {
          depts = depts.filter((d) => d.id === AUTH.department_id);
        }
        const interns = getVisibleInterns();
        const history = getVisibleHistory();
        const deptStats = depts.map((d) => {
          const dInterns = interns.filter((i) => i.department_id === d.id);
          const ids = dInterns.map((i) => i.id);
          const dHistory = history.filter((h) => ids.includes(h.intern_id));
          const present = dHistory.filter((h) => h.status !== "absent").length;
          const total = dHistory.length;
          const rate = total ? Math.round((present / total) * 100) : 0;
          const totalH = dHistory
            .reduce((s, h) => s + (h.work_duration || 0), 0)
            .toFixed(1);
          const alerts = dHistory.filter((h) => h.needs_attention).length;
          return {
            ...d,
            nb: dInterns.length,
            rate,
            totalH,
            alerts,
            present,
            total,
          };
        });

        const visibleCount = 6;
        
        // Tab system for department views
        document.getElementById("view-container").innerHTML = `
                <div style="margin-bottom:24px">
                  ${renderFilterBar()}
                  <div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:2px solid var(--border);padding-bottom:0">
                    <button onclick="switchDeptTab('overview')" id="dept-tab-overview" style="padding:12px 16px;background:transparent;color:var(--primary);border:none;border-bottom:3px solid var(--primary);cursor:pointer;font-weight:600;font-size:14px">Vue d'ensemble</button>
                    <button onclick="switchDeptTab('planning')" id="dept-tab-planning" style="padding:12px 16px;background:transparent;color:var(--text-m);border:none;border-bottom:3px solid transparent;cursor:pointer;font-weight:600;font-size:14px">Planning des rotations</button>
                  </div>
                  
                  <div id="dept-overview" style="display:block">
                    <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px">
                      <div style="flex:1;display:flex;align-items:center;background:var(--surface-d);border:1px solid var(--border);border-radius:8px;padding:0 12px">
                        <span class="material-symbols-outlined" style="color:var(--text-m);margin-right:8px">search</span>
                        <input type="text" id="dept-search" placeholder="Rechercher un service..." style="border:none;background:transparent;color:#fff;font-size:14px;padding:10px 0;width:100%;outline:none" />
                      </div>
                    </div>
                    <div id="dept-cards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:12px">
                      ${deptStats.slice(0, visibleCount).map((d) => `<div class="dept-card" data-service="${d.name.toLowerCase()}"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px"><div style="font-family:'Syne',sans-serif;font-size:15px;font-weight:700;color:#fff">${d.name}</div><span class="material-symbols-outlined" style="color:var(--primary);font-size:20px">local_hospital</span></div><div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:700;color:${d.rate >= 80 ? "var(--primary)" : d.rate >= 60 ? "var(--warn)" : "var(--error)"}">${d.rate}%</div><div style="font-size:11px;color:var(--text-f);margin-bottom:6px">taux de présence</div><div class="dept-bar-track"><div class="dept-bar-fill" style="width:${d.rate}%;background:${d.rate >= 80 ? "var(--primary)" : d.rate >= 60 ? "var(--warn)" : "var(--error)"}"></div></div><div style="display:flex;justify-content:space-between;font-size:12px;margin-top:10px;padding-top:10px;border-top:1px solid var(--border)"><span style="color:var(--text-m)">${d.nb} stagiaires</span><span style="color:${d.alerts > 0 ? "var(--error)" : "var(--primary)"};">${d.alerts} alertes</span></div></div>`).join("")}
                    </div>
                    <div id="service-actions" style="display:flex;justify-content:flex-end;margin:0 0 20px">
                      ${deptStats.length > visibleCount ? `<button id="services-plus-btn" onclick="showMoreServices()" style="width:auto;min-width:104px;padding:10px 14px;background:var(--primary);color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;gap:6px"><span class="material-symbols-outlined" style="font-size:18px">add</span> Plus</button>` : ''}
                    </div>
                    <div class="card"><div class="card-header" style="margin-bottom:0"><h3>Performance par service</h3></div><div class="card-body"><div class="chart-wrap" style="height:260px"><canvas id="ch-dept2"></canvas></div></div></div>
                  </div>
                  
                  <div id="dept-planning" style="display:none">
                    ${canPlanRotations() ? `
                    <div class="card" style="margin-bottom:16px">
                      <div class="card-header">
                        <div>
                          <h3>Planifier une rotation</h3>
                          <p>La rotation est enregistrée sur le stagiaire : service, date de début et date de fin.</p>
                        </div>
                      </div>
                      <div class="card-body">
                        <div id="rotation-plan-msg"></div>
                        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;align-items:end">
                          <div class="form-group" style="margin-bottom:0">
                            <label class="form-label">Stagiaire</label>
                            <select id="rotation-intern" class="form-control" onchange="prefillRotationForm()">
                              ${getRotationInterns().map((i) => `<option value="${i.id}">${i.first_name} ${i.last_name}</option>`).join("")}
                            </select>
                          </div>
                          <div class="form-group" style="margin-bottom:0">
                            <label class="form-label">Service</label>
                            <select id="rotation-dept" class="form-control" ${isChefService() ? "disabled" : ""}>
                              ${getRotationDepartments().map((d) => `<option value="${d.id}">${d.name}</option>`).join("")}
                            </select>
                          </div>
                          <div class="form-group" style="margin-bottom:0">
                            <label class="form-label">Date de début</label>
                            <input id="rotation-start" class="form-control" type="date" />
                          </div>
                          <div class="form-group" style="margin-bottom:0">
                            <label class="form-label">Date de fin</label>
                            <input id="rotation-end" class="form-control" type="date" />
                          </div>
                          <button class="btn btn-primary" style="height:42px;justify-content:center" onclick="saveRotationPlan()" ${getRotationInterns().length === 0 ? "disabled" : ""}>
                            <span class="material-symbols-outlined">event_available</span> Planifier
                          </button>
                        </div>
                      </div>
                    </div>` : `
                    <div class="alert alert-info" style="margin-bottom:16px">
                      <span class="material-symbols-outlined" style="font-size:16px">info</span>
                      Directeur : consultation uniquement. La planification est centralisée par DFRI / Administration ou par le Chef de service.
                    </div>`}
                    <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px">
                      <div style="flex:1;display:flex;align-items:center;background:var(--surface-d);border:1px solid var(--border);border-radius:8px;padding:0 12px">
                        <span class="material-symbols-outlined" style="color:var(--text-m);margin-right:8px">search</span>
                        <input type="text" id="planning-search" placeholder="Rechercher un service ou un stagiaire..." oninput="filterPlanningRotations()" style="border:none;background:transparent;color:#fff;font-size:14px;padding:10px 0;width:100%;outline:none" />
                      </div>
                    </div>
                    <div id="planning-content" style="display:flex;flex-direction:column;gap:20px"></div>
                  </div>
                </div>`;

        nextTick(() => {
          if (document.getElementById("ch-dept")) CHARTS["dept"] = new Chart(document.getElementById("ch-dept"), {
            type: "bar",
            data: {
              labels: deptStats.map((d) => d.name),
              datasets: [
                {
                  label: "Taux présence (%)",
                  data: deptStats.map((d) => d.rate),
                  backgroundColor: "rgba(69,241,195,.6)",
                  borderColor: "#45f1c3",
                  borderWidth: 1,
                  borderRadius: 4,
                },
                {
                  label: "Alertes",
                  data: deptStats.map((d) => d.alerts),
                  backgroundColor: "rgba(255,180,171,.6)",
                  borderColor: "#ffb4ab",
                  borderWidth: 1,
                  borderRadius: 4,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { labels: { color: "#dce4df", font: { size: 11 } } },
              },
              scales: {
                y: { grid: { color: "#1a2130" }, ticks: { color: "#85948d" } },
                x: { grid: { display: false }, ticks: { color: "#85948d" } },
              },
            },
          });
          CHARTS["dept2"] = new Chart(document.getElementById("ch-dept2"), {
            type: "bar",
            data: {
              labels: deptStats.map((d) => d.name),
              datasets: [
                {
                  label: "Taux (%)",
                  data: deptStats.map((d) => d.rate),
                  backgroundColor: deptStats.map((d) =>
                    d.rate >= 80
                      ? "rgba(69,241,195,.7)"
                      : d.rate >= 60
                        ? "rgba(255,206,166,.7)"
                        : "rgba(255,180,171,.7)",
                  ),
                  borderRadius: 4,
                },
              ],
            },
            options: {
              indexAxis: "y",
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                x: {
                  grid: { color: "#1a2130" },
                  ticks: { color: "#85948d" },
                  max: 100,
                },
                y: { grid: { display: false }, ticks: { color: "#85948d" } },
              },
            },
          });
        });
        
        // Add search functionality
        nextTick(() => {
          const searchInput = document.getElementById('dept-search');
          if (searchInput) {
            searchInput.addEventListener('input', (e) => {
              const searchTerm = normalizeSearchText(e.target.value);
              const cards = document.querySelectorAll('[data-service]');
              cards.forEach(card => {
                const serviceName = normalizeSearchText(card.getAttribute('data-service'));
                card.style.display = serviceName.includes(searchTerm) ? '' : 'none';
              });
            });
          }
        });
      }
      
      function normalizeSearchText(value) {
        return String(value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
      }

      function showMoreServices() {
        let allDepts = DATA.departments || [];
        if (isChefService()) {
          allDepts = allDepts.filter((d) => d.id === AUTH.department_id);
        }
        const interns = getVisibleInterns();
        const history = getVisibleHistory();
        const deptStats = allDepts.map((d) => {
          const dInterns = interns.filter((i) => i.department_id === d.id);
          const ids = dInterns.map((i) => i.id);
          const dHistory = history.filter((h) => ids.includes(h.intern_id));
          const present = dHistory.filter((h) => h.status !== "absent").length;
          const total = dHistory.length;
          const rate = total ? Math.round((present / total) * 100) : 0;
          const totalH = dHistory
            .reduce((s, h) => s + (h.work_duration || 0), 0)
            .toFixed(1);
          const alerts = dHistory.filter((h) => h.needs_attention).length;
          return {
            ...d,
            nb: dInterns.length,
            rate,
            totalH,
            alerts,
            present,
            total,
          };
        });
        
        const cardsContainer = document.getElementById('dept-cards');
        const newCards = deptStats.slice(6).map((d) => `<div class="dept-card" data-service="${d.name.toLowerCase()}"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px"><div style="font-family:'Syne',sans-serif;font-size:15px;font-weight:700;color:#fff">${d.name}</div><span class="material-symbols-outlined" style="color:var(--primary);font-size:20px">local_hospital</span></div><div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:700;color:${d.rate >= 80 ? "var(--primary)" : d.rate >= 60 ? "var(--warn)" : "var(--error)"}">${d.rate}%</div><div style="font-size:11px;color:var(--text-f);margin-bottom:6px">taux de présence</div><div class="dept-bar-track"><div class="dept-bar-fill" style="width:${d.rate}%;background:${d.rate >= 80 ? "var(--primary)" : d.rate >= 60 ? "var(--warn)" : "var(--error)"}"></div></div><div style="display:flex;justify-content:space-between;font-size:12px;margin-top:10px;padding-top:10px;border-top:1px solid var(--border)"><span style="color:var(--text-m)">${d.nb} stagiaires</span><span style="color:${d.alerts > 0 ? "var(--error)" : "var(--primary)"};">${d.alerts} alertes</span></div></div>`).join('');
        
        cardsContainer.innerHTML += newCards;
        
        const button = document.querySelector('button[onclick="showMoreServices()"]');
        if (button) button.style.display = 'none';
        const actions = document.getElementById('service-actions');
        if (actions) {
          actions.innerHTML = `<button id="services-less-btn" onclick="resetServicesOverview()" style="width:auto;min-width:104px;padding:10px 14px;background:var(--surface-d);color:var(--primary);border:1px solid var(--primary-g);border-radius:8px;font-weight:600;cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;gap:6px"><span class="material-symbols-outlined" style="font-size:18px">remove</span> Moins</button>`;
        }
        
        // Re-apply search filter after adding new cards
        const searchInput = document.getElementById('dept-search');
        if (searchInput && searchInput.value) {
          const searchTerm = normalizeSearchText(searchInput.value);
          const cards = document.querySelectorAll('[data-service]');
          cards.forEach(card => {
            const serviceName = normalizeSearchText(card.getAttribute('data-service'));
            card.style.display = serviceName.includes(searchTerm) ? '' : 'none';
          });
        }
      }

      function resetServicesOverview() {
        renderDepartment();
      }
      
      function switchDeptTab(tab) {
        const overviewTab = document.getElementById('dept-tab-overview');
        const planningTab = document.getElementById('dept-tab-planning');
        const overviewContent = document.getElementById('dept-overview');
        const planningContent = document.getElementById('dept-planning');
        
        if (tab === 'overview') {
          overviewTab.style.borderBottomColor = 'var(--primary)';
          overviewTab.style.color = 'var(--primary)';
          planningTab.style.borderBottomColor = 'transparent';
          planningTab.style.color = 'var(--text-m)';
          overviewContent.style.display = 'block';
          planningContent.style.display = 'none';
        } else if (tab === 'planning') {
          overviewTab.style.borderBottomColor = 'transparent';
          overviewTab.style.color = 'var(--text-m)';
          planningTab.style.borderBottomColor = 'var(--primary)';
          planningTab.style.color = 'var(--primary)';
          overviewContent.style.display = 'none';
          planningContent.style.display = 'block';
          renderPlanningView();
          nextTick(filterPlanningRotations);
          nextTick(prefillRotationForm);
        }
      }

      function canPlanRotations() {
        return isDFRI() || isChefService();
      }

      function getRotationDepartments() {
        const depts = DATA.departments || [];
        return isChefService() ? depts.filter((d) => d.id === AUTH.department_id) : depts;
      }

      function getRotationInterns() {
        const interns = activeInterns();
        return isChefService() ? interns.filter((i) => i.department_id === AUTH.department_id) : interns;
      }

      function prefillRotationForm() {
        const internId = document.getElementById('rotation-intern')?.value;
        const intern = getRotationInterns().find((i) => i.id === internId);
        if (!intern) return;
        const deptSelect = document.getElementById('rotation-dept');
        const startInput = document.getElementById('rotation-start');
        const endInput = document.getElementById('rotation-end');
        if (deptSelect) deptSelect.value = intern.department_id || '';
        if (startInput) startInput.value = intern.start_date || '';
        if (endInput) endInput.value = intern.end_date || '';
      }

      async function saveRotationPlan() {
        const msgEl = document.getElementById('rotation-plan-msg');
        const internId = document.getElementById('rotation-intern')?.value;
        const department_id = document.getElementById('rotation-dept')?.value;
        const start_date = document.getElementById('rotation-start')?.value;
        const end_date = document.getElementById('rotation-end')?.value;
        if (!internId || !department_id || !start_date || !end_date) {
          if (msgEl) msgEl.innerHTML = '<div class="alert alert-error">Veuillez choisir le stagiaire, le service et les deux dates.</div>';
          return;
        }
        if (new Date(start_date) > new Date(end_date)) {
          if (msgEl) msgEl.innerHTML = '<div class="alert alert-error">La date de début doit être avant ou égale à la date de fin.</div>';
          return;
        }
        try {
          const res = await apiFetch(`/interns/${internId}`, {
            method: "PATCH",
            body: JSON.stringify({ department_id, start_date, end_date }),
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || "Erreur serveur");
          const intern = DATA.interns.find((i) => i.id === internId);
          if (intern) {
            intern.department_id = department_id;
            intern.start_date = start_date;
            intern.end_date = end_date;
          }
          showToast("Rotation planifiée", "success");
          renderPlanningView();
          nextTick(filterPlanningRotations);
          nextTick(prefillRotationForm);
        } catch (e) {
          if (msgEl) msgEl.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
        }
      }
      
      function renderPlanningView() {
        const depts = (DATA.departments || []).filter(d => !isChefService() || d.id === AUTH.department_id);
        const interns = activeInterns();
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const planningHTML = depts.map(dept => {
          const deptInterns = interns.filter(i => i.department_id === dept.id);
          
          // Separate interns into categories
          const current = [];
          const upcoming = [];
          const ending = [];
          
          deptInterns.forEach(intern => {
            // Using placeholder logic - will work with real dates from backend
            const endDate = intern.end_date ? new Date(intern.end_date) : null;
            const startDate = intern.start_date ? new Date(intern.start_date) : null;
            
            if (startDate && endDate) {
              const daysUntilEnd = endDate ? Math.ceil((endDate - today) / (1000 * 60 * 60 * 24)) : null;
              const daysFromStart = startDate ? Math.ceil((today - startDate) / (1000 * 60 * 60 * 24)) : null;
              
              if (daysFromStart >= 0 && daysUntilEnd > 0) {
                if (daysUntilEnd <= 3) {
                  ending.push({...intern, daysLeft: daysUntilEnd});
                } else {
                  current.push({...intern, daysLeft: daysUntilEnd});
                }
              } else if (daysUntilEnd > 0 && daysFromStart < 0) {
                const daysUntilStart = Math.ceil((startDate - today) / (1000 * 60 * 60 * 24));
                if (daysUntilStart <= 7) {
                  upcoming.push({...intern, daysUntilStart});
                }
              }
            }
          });
          
          const sections = [];
          
          if (ending.length > 0) {
            sections.push(`
              <div class="card" style="border-left:4px solid #ff6b6b">
                <div class="card-header"><h3 style="color:#ff6b6b">Rotations se terminant sous 3 jours</h3></div>
                <div class="card-body">
                  ${ending.map(i => `
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:12px;border-bottom:1px solid var(--border);background:rgba(255,107,107,0.05);border-radius:6px;margin-bottom:8px">
                      <div>
                        <div style="font-weight:600;color:#fff">${i.first_name} ${i.last_name}</div>
                        <div style="font-size:12px;color:var(--text-m)">Fin : ${new Date(i.end_date).toLocaleDateString('fr-FR')}</div>
                      </div>
                      <span style="background:#ff6b6b;color:#fff;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600">${i.daysLeft} jour${i.daysLeft > 1 ? 's' : ''}</span>
                    </div>
                  `).join('')}
                </div>
              </div>
            `);
          }
          
          if (current.length > 0) {
            sections.push(`
              <div class="card" style="border-left:4px solid #45f1c3">
                <div class="card-header"><h3 style="color:#45f1c3">En cours dans le service</h3></div>
                <div class="card-body">
                  ${current.map(i => `
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:12px;border-bottom:1px solid var(--border);background:rgba(69,241,195,0.05);border-radius:6px;margin-bottom:8px">
                      <div>
                        <div style="font-weight:600;color:#fff">${i.first_name} ${i.last_name}</div>
                        <div style="font-size:12px;color:var(--text-m)">Fin : ${new Date(i.end_date).toLocaleDateString('fr-FR')}</div>
                      </div>
                      <span style="background:#45f1c3;color:#0a0e27;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600">${i.daysLeft} jours</span>
                    </div>
                  `).join('')}
                </div>
              </div>
            `);
          }
          
          if (upcoming.length > 0) {
            sections.push(`
              <div class="card" style="border-left:4px solid #4dabf7">
                <div class="card-header"><h3 style="color:#4dabf7">À venir (7 prochains jours)</h3></div>
                <div class="card-body">
                  ${upcoming.map(i => `
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:12px;border-bottom:1px solid var(--border);background:rgba(77,171,247,0.05);border-radius:6px;margin-bottom:8px">
                      <div>
                        <div style="font-weight:600;color:#fff">${i.first_name} ${i.last_name}</div>
                        <div style="font-size:12px;color:var(--text-m)">Début : ${new Date(i.start_date).toLocaleDateString('fr-FR')}</div>
                      </div>
                      <span style="background:#4dabf7;color:#fff;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600">${i.daysUntilStart} jour${i.daysUntilStart > 1 ? 's' : ''}</span>
                    </div>
                  `).join('')}
                </div>
              </div>
            `);
          }
          
          if (sections.length === 0) {
            sections.push(`<div class="card"><div class="card-body"><div style="text-align:center;color:var(--text-m);padding:40px 20px"><span class="material-symbols-outlined" style="font-size:48px;color:var(--text-f);display:block;margin-bottom:12px">event_note</span><p>Aucune rotation planifiée pour le moment</p></div></div></div>`);
          }
          
          const searchTerms = [
            dept.name,
            ...deptInterns.map(i => `${i.first_name} ${i.last_name}`),
            ...deptInterns.map(i => i.start_date || ''),
            ...deptInterns.map(i => i.end_date || '')
          ].join(' ').toLowerCase();
          
          return `<div class="planning-dept" data-planning-search="${searchTerms}"><h3 style="margin-bottom:16px;font-size:16px;color:var(--primary)">${dept.name}</h3>${sections.join('')}</div>`;
        }).join('<div style="margin:24px 0;border-bottom:1px solid var(--border)"></div>');
        
        document.getElementById('planning-content').innerHTML = planningHTML || '<div class="card"><div class="card-body"><p>Aucune donnée de rotation disponible. Les rotations seront affichées une fois configurées dans le système.</p></div></div>';
      }

