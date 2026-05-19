      // ── JOURNAL D'AUDIT ──────────────────────────────────────────────────────
      function renderAudit() {
        const auditLogs = DATA.auditLogs || [];
        const sortedLogs = [...auditLogs].sort((a, b) => 
          new Date(b.timestamp) - new Date(a.timestamp)
        );

        document.getElementById("view-container").innerHTML = `
                <div class="card">
                  <div class="card-header">
                    <div>
                      <h3>Journal d'Audit Complet</h3>
                      <p>Toutes les actions effectuées par les utilisateurs</p>
                    </div>
                  </div>
                  <div class="card-body" style="padding-top:0;overflow-x:auto">
                    ${
                      sortedLogs.length === 0
                        ? '<div class="empty-state"><span class="material-symbols-outlined">history</span><p>Aucune activité enregistrée.</p></div>'
                        : `
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>Timestamp</th>
                          <th>Utilisateur</th>
                          <th>Rôle</th>
                          <th>Action</th>
                          <th>Ressource</th>
                          <th>Détails</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${sortedLogs
                          .map((log) => `
                          <tr>
                            <td style="font-family:'DM Mono',monospace;font-size:11px">${fmtDate(log.timestamp)} ${fmtTime(log.timestamp)}</td>
                            <td style="font-weight:600">${log.username || "—"}</td>
                            <td><span class="badge badge-grey">${log.role || "—"}</span></td>
                            <td>
                              <span class="badge ${
                                log.action_type === "create" ? "badge-green" :
                                log.action_type === "update" ? "badge-blue" :
                                log.action_type === "delete" ? "badge-red" :
                                log.action_type === "read" ? "badge-grey" :
                                "badge-grey"
                              }" style="text-transform:capitalize">${log.action_type || "—"}</span>
                            </td>
                            <td style="font-size:12px;color:var(--text-m)">${log.resource_type || "—"}</td>
                            <td style="font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${log.details || ""}">${log.details || "—"}</td>
                          </tr>
                        `)
                          .join("")}
                      </tbody>
                    </table>`
                    }
                  </div>
                </div>`;
      }

    // ── À PROPOS ─────────────────────────────────────────────────────────────
  function renderAbout() {
    document.getElementById("view-container").innerHTML = `
      <div class="card" style="max-width: 1000px;">
        <div class="card-header">
          <div>
            <h2 style="margin: 0 0 8px 0;">À propos de la Plateforme</h2>
            <p style="margin: 0;">GST-TTA Analytics — Plateforme de gestion des stages hospitaliers</p>
          </div>
        </div>
        <div class="card-body" style="padding: 24px;">
          
          <section style="margin-bottom: 32px;">
            <h3 style="color: var(--primary); margin-bottom: 12px;">Description</h3>
            <p style="line-height: 1.6; color: var(--text-m); margin: 0;">
              Cette plateforme est une solution complète de gestion des stages et de suivi d'assiduité pour le 
              <strong>Groupe sanitaire territorial (GST-TTA)</strong>. Elle permet de :
            </p>
            <ul style="margin: 12px 0; padding-left: 20px; line-height: 1.8; color: var(--text-m);">
              <li>Gérer l'attendance des stagiaires en temps réel via codes QR</li>
              <li>Suivre et analyser les présences par service et par période</li>
              <li>Générer des rapports et des statistiques détaillées</li>
              <li>Importer massivement des données depuis des fichiers Excel</li>
              <li>Archiver et historiser les données des stages</li>
              <li>Fournir des alertes et notifications automatiques</li>
            </ul>
          </section>

          <section style="margin-bottom: 32px;">
            <h3 style="color: var(--primary); margin-bottom: 12px;">Équipe de Développement</h3>
            <p style="line-height: 1.6; color: var(--text-m); margin-bottom: 16px;">
              Cette plateforme a été développée par trois étudiantes dans le cadre de leur projet de fin d'études en 2026.
            </p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px;">
              
              <div style="background: var(--surface2); padding: 16px; border-radius: var(--radius); border-left: 4px solid var(--primary);">
                <h4 style="margin: 0 0 8px 0; color: #fff;">Nouhaila Touil</h4>
                <p style="margin: 0; font-size: 13px; color: var(--text-f); line-height: 1.6;">
                  Responsable de l'architecture backend, de la base de données PostgreSQL, de la sécurité, 
                  de l'authentification JWT, et du système d'import/export Excel.
                </p>
              </div>

              <div style="background: var(--surface2); padding: 16px; border-radius: var(--radius); border-left: 4px solid var(--primary);">
                <h4 style="margin: 0 0 8px 0; color: #fff;">Imane Aithamou</h4>
                <p style="margin: 0; font-size: 13px; color: var(--text-f); line-height: 1.6;">
                  Responsable de la logique métier complexe, de la gestion des rotations entre services, 
                  de l'archivage automatique, et de la structure organisationnelle de l'hôpital.
                </p>
              </div>

              <div style="background: var(--surface2); padding: 16px; border-radius: var(--radius); border-left: 4px solid var(--primary);">
                <h4 style="margin: 0 0 8px 0; color: #fff;">Abir Fatah</h4>
                <p style="margin: 0; font-size: 13px; color: var(--text-f); line-height: 1.6;">
                  Responsable de la conception de l'interface utilisateur, du dashboard interactif, 
                  de l'expérience utilisateur, et des vues adaptées à chaque rôle.
                </p>
              </div>

            </div>
          </section>

          <section style="margin-bottom: 32px;">
            <h3 style="color: var(--primary); margin-bottom: 12px;">🛠 Stack Technologique</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
              <div style="background: rgba(69, 241, 195, 0.1); border: 1px solid rgba(69, 241, 195, 0.2); padding: 12px; border-radius: var(--radius);">
                <strong style="color: var(--primary); display: block; margin-bottom: 4px;">Backend & API</strong>
                <span style="font-size: 13px; color: var(--text-f);">FastAPI, Python, PostgreSQL</span>
              </div>
              <div style="background: rgba(69, 241, 195, 0.1); border: 1px solid rgba(69, 241, 195, 0.2); padding: 12px; border-radius: var(--radius);">
                <strong style="color: var(--primary); display: block; margin-bottom: 4px;">Frontend</strong>
                <span style="font-size: 13px; color: var(--text-f);">HTML5, CSS3, JavaScript vanilla</span>
              </div>
              <div style="background: rgba(69, 241, 195, 0.1); border: 1px solid rgba(69, 241, 195, 0.2); padding: 12px; border-radius: var(--radius);">
                <strong style="color: var(--primary); display: block; margin-bottom: 4px;">QR Code & Scans</strong>
                <span style="font-size: 13px; color: var(--text-f);">QRCode.js, Html5-QRCode (Scanner caméra), jsPDF, ReportLab</span>
              </div>
              <div style="background: rgba(69, 241, 195, 0.1); border: 1px solid rgba(69, 241, 195, 0.2); padding: 12px; border-radius: var(--radius);">
                <strong style="color: var(--primary); display: block; margin-bottom: 4px;">ETL & Pipelines</strong>
                <span style="font-size: 13px; color: var(--text-f);">Extraction de données hospitalières, Transformations automatisées, Chargement (Load) SQL</span>
              </div>
              <div style="background: rgba(69, 241, 195, 0.1); border: 1px solid rgba(69, 241, 195, 0.2); padding: 12px; border-radius: var(--radius);">
                <strong style="color: var(--primary); display: block; margin-bottom: 4px;">Gestion des Données</strong>
                <span style="font-size: 13px; color: var(--text-f);">Pandas, OpenPyXL, SQLAlchemy</span>
              </div>
              <div style="background: rgba(69, 241, 195, 0.1); border: 1px solid rgba(69, 241, 195, 0.2); padding: 12px; border-radius: var(--radius);">
                <strong style="color: var(--primary); display: block; margin-bottom: 4px;">Sécurité</strong>
                <span style="font-size: 13px; color: var(--text-f);">JWT, bcrypt, CORS, HTTPS</span>
              </div>
              <div style="background: rgba(69, 241, 195, 0.1); border: 1px solid rgba(69, 241, 195, 0.2); padding: 12px; border-radius: var(--radius);">
                <strong style="color: var(--primary); display: block; margin-bottom: 4px;">ML & Analytics</strong>
                <span style="font-size: 13px; color: var(--text-f);">Scikit-learn, Feature Engineering</span>
              </div>
            </div>
          </section>

          <section style="margin-bottom: 32px;">
            <h3 style="color: var(--primary); margin-bottom: 12px;">Notre Formation</h3>
            <p style="line-height: 1.6; color: var(--text-m); margin: 0;">
              Ce projet s'inscrit dans le cadre de notre formation en <strong>Licence Analytique des Données</strong> au sein du Service Informatique de la <strong>Faculté des Sciences et Techniques (FST) de Tanger</strong>. Ce cursus nous spécialise dans la conception de solutions intelligentes pour le traitement, l'ingénierie (ETL) et la valorisation statistique des données complexes.
            </p>
          </section>

          <section style="border-top: 1px solid var(--border); padding-top: 24px;">
            <h3 style="color: var(--primary); margin-bottom: 12px;">Support</h3>
            <p style="line-height: 1.6; color: var(--text-m); margin: 0;">
              Pour toute question ou problème technique concernant cette plateforme, 
              contactez l'équipe DFRI du GST-TTA.
            </p>
          </section>

        </div>
      </div>`;
  }


