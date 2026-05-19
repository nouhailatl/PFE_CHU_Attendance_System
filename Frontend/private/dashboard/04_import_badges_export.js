      // ── ★ IMPORT EXCEL STAGIAIRES ──────────────────────────────────────────
      function renderAdminImport() {
        if (!isDFRI()) {
          document.getElementById("admin-view-container").innerHTML = `
            <div class="empty-state">
              <span class="material-symbols-outlined">block</span>
              <p>Accès restreint. Seul le Directeur IT (DFRI) peut importer des stagiaires.</p>
            </div>`;
          return;
        }

        document.getElementById("admin-view-container").innerHTML = `
          <div class="card" style="margin-top: 16px;">
            <div class="card-header">
              <div>
                <h3>Importation des Stagiaires par Fichier</h3>
                <p>Ajoutez massivement des stagiaires via un fichier Excel (.xlsx, .xls) ou un fichier CSV.</p>
              </div>
            </div>
            <div class="card-body" style="display: flex; flex-direction: column; gap: 20px;">
              
              <div style="background: var(--surface2); padding: 16px; border-radius: var(--radius); display: flex; align-items: center; justify-content: space-between; border: 1px dashed var(--border);">
                <div>
                  <strong style="color: #fff; display: block; margin-bottom: 4px;">Fichier Modèle Officiel</strong>
                  <span style="font-size: 12px; color: var(--text-f);">Téléchargez le canevas pré-formaté pour structurer correctement vos données.</span>
                </div>
                <button class="btn btn-primary" onclick="downloadImportTemplate()" id="btn-download-template">
                  <span class="material-symbols-outlined">download</span>
                  <span>Télécharger le template Excel</span>
                </button>
              </div>

              <div id="import-dropzone" class="import-dropzone" 
                   style="border: 2px dashed var(--border); padding: 40px 20px; border-radius: var(--radius); text-align: center; background: var(--surface); cursor: pointer; transition: all 0.2s;"
                   ondragover="event.preventDefault(); this.style.borderColor='var(--primary)'; this.style.background='rgba(69,241,195,0.04)';"
                   ondragleave="this.style.borderColor='var(--border)'; this.style.background='var(--surface)';"
                   ondrop="handleImportDrop(event)">
                <span class="material-symbols-outlined" style="font-size: 48px; color: var(--text-f); margin-bottom: 12px; display: block;">cloud_upload</span>
                <p style="margin: 0; font-size: 14px; color: #fff;">
                  Glissez-déposez votre fichier ici, ou <span style="color: var(--primary); text-decoration: underline;">parcourez vos fichiers</span>
                </p>
                <span style="font-size: 11px; color: var(--text-f); display: block; margin-top: 6px;">Formats acceptés : .xlsx, .xls, .csv</span>
                <input type="file" id="import-file-input" accept=".xlsx, .xls, .csv" style="display: none;" onchange="handleImportFileSelect(event)">
              </div>

              <div id="import-preview-zone" class="hidden"></div>
              
              <div id="import-progress-zone" class="hidden" style="background: var(--surface2); padding: 20px; border-radius: var(--radius);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
                  <span id="import-progress-status" style="color: #fff;">Traitement du fichier et création des comptes...</span>
                  <span id="import-progress-percent" style="font-family: 'DM Mono', monospace; color: var(--primary);">0%</span>
                </div>
                <div style="width: 100%; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden;">
                  <div id="import-progress-bar" style="width: 0%; height: 100%; background: var(--primary); transition: width 0.1s linear;"></div>
                </div>
              </div>

            </div>
          </div>`;

        // Rendre la zone cliquable pour ouvrir l'explorateur de fichiers
        const zone = document.getElementById("import-dropzone");
        if (zone) {
          zone.addEventListener("click", () => document.getElementById("import-file-input").click());
        }
      }

      // ── TÉLÉCHARGEMENT DU TEMPLATE ──────────────────────────────────────────
      async function downloadImportTemplate() {
        const btn = document.getElementById("btn-download-template");
        btn.disabled = true;
        try {
          const res = await apiFetch("/interns/import/template");
          if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "Template_Import_Stagiaires.xlsx";
            a.click();
            URL.revokeObjectURL(url);
            showToast("Template téléchargé depuis le serveur", "success");
          } else {
            throw new Error("Template non configuré sur le backend");
          }
        } catch (e) {
          // Fallback client-side : Génération automatique d'un CSV structurel
          const csvContent = "data:text/csv;charset=utf-8,prenom,nom,service\nJean,Dupont,Urgences\nMarie,Curie,Pédiatrie\n";
          const encodedUri = encodeURI(csvContent);
          const a = document.createElement("a");
          a.href = encodedUri;
          a.download = "Template_Import_Stagiaires.csv";
          a.click();
          showToast("Template CSV généré automatiquement côté client 💡", "success");
        } finally {
          btn.disabled = false;
        }
      }

      // ── GESTION DES FICHIERS DÉPOSÉS ────────────────────────────────────────
      function handleImportDrop(e) {
        e.preventDefault();
        const zone = document.getElementById("import-dropzone");
        zone.style.borderColor = "var(--border)";
        zone.style.background = "var(--surface)";
        
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          processImportFile(e.dataTransfer.files[0]);
        }
      }

      function handleImportFileSelect(e) {
        if (e.target.files && e.target.files.length > 0) {
          processImportFile(e.target.files[0]);
        }
      }

      // ── ANALYSE ET VALIDATION DU FICHIER ─────────────────────────────────────
      let CURRENT_IMPORT_FILE = null; // Mémoire tampon globale pour le fichier validé
      let CLIENT_SIDE_PARSED_ROWS = null; // Mémoire tampon pour le fallback JS

      async function processImportFile(file) {
        CURRENT_IMPORT_FILE = file;
        CLIENT_SIDE_PARSED_ROWS = null;

        const previewZone = document.getElementById("import-preview-zone");
        previewZone.innerHTML = `
          <div style="text-align:center; padding: 20px;">
            <span class="spinner" style="width: 24px; height: 24px; margin-bottom: 8px;"></span>
            <p style="font-size: 13px; color: var(--text-f);">Analyse syntaxique et validation des lignes en cours...</p>
          </div>`;
        previewZone.classList.remove("hidden");

        const formData = new FormData();
        formData.append("file", file);

        try {
          // Appel à l'endpoint de validation officiel
          const res = await fetch(`${API}/interns/import/validate`, {
            method: "POST",
            headers: { 'Authorization': `Bearer ${AUTH.access_token}` },
            body: formData
          });

          if (res.status === 401) { doLogout(); return; }

          if (res.ok) {
            const result = await res.json();
            renderValidationReport(result.valid_count, result.errors_count, result.errors_details, result.preview_rows);
          } else {
            throw new Error("Validation backend indisponible");
          }
        } catch (e) {
          // Fallback complet côté client : Traitement par parsing si le backend est partiel
          parseFileClientSide(file);
        }
      }

      // Parsing local pour les fichiers (notamment CSV ou détection textuelle) en cas de fallback backend
      function parseFileClientSide(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
          const text = e.target.result;
          const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
          
          if(lines.length <= 1) {
            renderValidationReport(0, 1, [{ row: 1, message: "Le fichier ne contient aucune donnée ou est vide." }], []);
            return;
          }

          const headers = lines[0].toLowerCase().split(/[;,]/).map(h => h.trim());
          const idxPrenom = headers.indexOf("prenom");
          const idxNom = headers.indexOf("nom");
          const idxDept = headers.indexOf("service") >= 0 ? headers.indexOf("service") : headers.indexOf("departement");

          if (idxPrenom === -1 || idxNom === -1 || idxDept === -1) {
            renderValidationReport(0, 1, [{ row: 1, message: "Colonnes obligatoires manquantes. Attendu : 'prenom', 'nom', 'service'." }], []);
            return;
          }

          let validRows = [];
          let errorRows = [];
          const existingDepts = (DATA.departments || []).map(d => d.name.toLowerCase());

          for (let i = 1; i < lines.length; i++) {
            const columns = lines[i].split(/[;,]/).map(c => c.trim().replace(/^["']|["']$/g, ''));
            if (columns.length < 3) continue;

            const pValue = columns[idxPrenom];
            const nValue = columns[idxNom];
            const dValue = columns[idxDept];
            let errors = [];

            if (!pValue) errors.push("Prénom vide");
            if (!nValue) errors.push("Nom de famille vide");
            if (!dValue) {
              errors.push("Service vide");
            } else if (!existingDepts.includes(dValue.toLowerCase())) {
              errors.push(`Le service '${dValue}' n'existe pas dans le référentiel hospitalier`);
            }

            if (errors.length > 0) {
              errorRows.push({ row: i + 1, message: errors.join(", ") });
            } else {
              // Récupération de l'ID réel du service pour le futur import unitaire
              const foundDept = (DATA.departments || []).find(d => d.name.toLowerCase() === dValue.toLowerCase());
              validRows.push({
                first_name: pValue,
                last_name: nValue,
                department_id: foundDept ? foundDept.id : null,
                department_name: dValue
              });
            }
          }

          CLIENT_SIDE_PARSED_ROWS = validRows;
          const preview = validRows.slice(0, 5);
          renderValidationReport(validRows.length, errorRows.length, errorRows, preview);
        };
        reader.readAsText(file);
      }

      // ── CONSTITUTION DU RAPPORT DE VALIDATION BI-COLEUR ─────────────────────
      function renderValidationReport(validCount, errorCount, errors, preview) {
        const previewZone = document.getElementById("import-preview-zone");
        
        let errorSection = "";
        if (errorCount > 0) {
          errorSection = `
            <div style="border: 1px solid rgba(255,180,171,0.2); background: rgba(255,180,171,0.02); border-radius: var(--radius); padding: 12px; margin-top: 10px;">
              <h4 style="color: #ffb4ab; font-size: 13px; margin: 0 0 8px 0; display:flex; align-items:center; gap:6px;">
                <span class="material-symbols-outlined" style="font-size:16px;">error</span> Liste détaillée des anomalies rencontrées
              </h4>
              <div style="max-height: 150px; overflow-y: auto; font-family: 'DM Mono', monospace; font-size: 11px;">
                <table style="width: 100%; border-collapse: collapse;">
                  <thead>
                    <tr style="color: var(--text-f); text-align: left; border-bottom: 1px solid var(--border);">
                      <th style="padding: 4px;">Ligne</th>
                      <th style="padding: 4px;">Description du problème</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${errors.map(e => `
                      <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <td style="padding: 4px; color: #ffb4ab; font-weight: bold; width: 60px;">#${e.row}</td>
                        <td style="padding: 4px; color: var(--text-f);">${e.message}</td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>
            </div>`;
        }

        let previewSection = "";
        if (validCount > 0 && preview.length > 0) {
          previewSection = `
            <div style="border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; margin-top: 12px;">
              <h4 style="color: #fff; font-size: 13px; margin: 0 0 8px 0;">Aperçu des 5 premières lignes valides prêtes à l'import</h4>
              <table class="data-table" style="font-size: 12px; width: 100%;">
                <thead>
                  <tr>
                    <th>Prénom</th>
                    <th>Nom</th>
                    <th>Service assigné</th>
                  </tr>
                </thead>
                <tbody>
                  ${preview.map(p => `
                    <tr>
                      <td>${p.first_name || p.prenom}</td>
                      <td>${p.last_name || p.nom}</td>
                      <td><span class="badge badge-grey">${p.department_name || p.departement || 'Assigné'}</span></td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>`;
        }

        previewZone.innerHTML = `
          <div style="background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px;">
            <div style="font-family: 'Syne', sans-serif; font-size: 15px; font-weight: bold; color: #fff; margin-bottom: 12px; display:flex; justify-content: space-between; align-items:center;">
              <span>Rapport d'analyse de validation syntaxique</span>
              <span style="font-size:12px; color:var(--text-f); font-weight:normal;">Fichier sélectionné : ${CURRENT_IMPORT_FILE.name}</span>
            </div>
            
            <div style="display: flex; gap: 16px; margin-bottom: 12px;">
              <div style="flex: 1; background: rgba(69,241,195,0.06); border: 1px solid rgba(69,241,195,0.2); border-radius: var(--radius); padding: 10px; text-align: center;">
                <div style="font-size: 20px; font-weight: 800; color: #45f1c3;">${validCount}</div>
                <div style="font-size: 11px; color: var(--text-f); text-transform: uppercase; font-weight:500;">Lignes valides</div>
              </div>
              <div style="flex: 1; background: rgba(255,180,171,0.06); border: 1px solid rgba(255,180,171,0.2); border-radius: var(--radius); padding: 10px; text-align: center;">
                <div style="font-size: 20px; font-weight: 800; color: #ffb4ab;">${errorCount}</div>
                <div style="font-size: 11px; color: var(--text-f); text-transform: uppercase; font-weight:500;">Lignes avec erreurs</div>
              </div>
            </div>

            ${errorSection}
            ${previewSection}

            <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px; border-top: 1px solid var(--border); padding-top: 12px;">
              <button class="btn btn-grey" onclick="cancelImport()">Annuler</button>
              <button class="btn btn-primary" id="btn-confirm-import" ${validCount === 0 ? 'disabled style="opacity:0.5; cursor:not-allowed;"' : ''} onclick="executeFinalImport()">
                <span class="material-symbols-outlined">check_circle</span>
                <span>Confirmer l'import (${validCount})</span>
              </button>
            </div>
          </div>`;
      }

      // ── ANNULATION DE L'IMPORTATION ─────────────────────────────────────────
      function cancelImport() {
        CURRENT_IMPORT_FILE = null;
        CLIENT_SIDE_PARSED_ROWS = null;
        document.getElementById("import-file-input").value = "";
        document.getElementById("import-preview-zone").classList.add("hidden");
        showToast("Importation annulée par l'administrateur", "info");
      }

      // ── EXÉCUTION DE L'IMPORTATION FINALE ET ENVOI PAR LOTS ──────────────────
      async function executeFinalImport() {
        const previewZone = document.getElementById("import-preview-zone");
        const progressZone = document.getElementById("import-progress-zone");
        const progressBar = document.getElementById("import-progress-bar");
        const progressPercent = document.getElementById("import-progress-percent");
        const progressStatus = document.getElementById("import-progress-status");

        previewZone.classList.add("hidden");
        progressZone.classList.remove("hidden");
        progressBar.style.width = "0%";
        progressPercent.textContent = "0%";

        // Formater les données pour le endpoint batch
        const formData = new FormData();
        formData.append("file", CURRENT_IMPORT_FILE);

        try {
          // Tentative d'intégration native via POST /interns/import
          progressStatus.textContent = "Transmission des données au serveur central (Batch)...";
          progressBar.style.width = "40%";
          progressPercent.textContent = "40%";

          const res = await fetch(`${API}/interns/import`, {
            method: "POST",
            headers: { 'Authorization': `Bearer ${AUTH.access_token}` },
            body: formData
          });

          if (res.status === 401) { doLogout(); return; }

          if (res.ok) {
            const result = await res.json();
            progressBar.style.width = "100%";
            progressPercent.textContent = "100%";
            progressStatus.textContent = "Importation réussie !";
            
            showToast(`Réussite : ${result.created_count || 'Stagiaires'} comptes créés avec succès`, "success");
            setTimeout(() => finishImportSession(), 1500);
          } else {
            throw new Error("Batch route indisponible, déclenchement du traitement par lot unitaire");
          }
        } catch (e) {
          // Fallback transactionnel : Envoi ligne par ligne vers POST /interns/add
          if (CLIENT_SIDE_PARSED_ROWS && CLIENT_SIDE_PARSED_ROWS.length > 0) {
            executeLigneParLigneFallback(CLIENT_SIDE_PARSED_ROWS);
          } else {
            // Si pas de parsing local préalable (cas où le backend a répondu OK à validate mais a échoué sur l'import)
            progressStatus.textContent = "Analyse locale secondaire pour traitement individuel...";
            const reader = new FileReader();
            reader.onload = function(event) {
              // Extraction simple pour reproduire les lignes
              parseFileClientSide(CURRENT_IMPORT_FILE);
              setTimeout(() => {
                if (CLIENT_SIDE_PARSED_ROWS && CLIENT_SIDE_PARSED_ROWS.length > 0) {
                  executeLigneParLigneFallback(CLIENT_SIDE_PARSED_ROWS);
                } else {
                  showToast("Impossible d'extraire les données pour le fallback unitaire.", "error");
                  finishImportSession();
                }
              }, 500);
            };
            reader.readAsText(CURRENT_IMPORT_FILE);
          }
        }
      }

      // Boucle d'insertion pas-à-pas pour assurer la synchronisation de la BDD et de la barre
      async function executeLigneParLigneFallback(rows) {
        const progressBar = document.getElementById("import-progress-bar");
        const progressPercent = document.getElementById("import-progress-percent");
        const progressStatus = document.getElementById("import-progress-status");
        
        let successCount = 0;
        const total = rows.length;

        for (let i = 0; i < total; i++) {
          const r = rows[i];
          progressStatus.textContent = `Insertion du stagiaire : ${r.first_name} ${r.last_name} (${i + 1}/${total})...`;
          
          try {
            const payload = {
              first_name: r.first_name,
              last_name: r.last_name,
              department_id: r.department_id
            };
            
            const res = await apiFetch("/interns/add", {
              method: "POST",
              body: JSON.stringify(payload)
            });

            if (res.ok) successCount++;
          } catch (err) {
            console.error("Échec d'insertion individuelle pour", r, err);
          }

          // Rapprochement progressif de la barre de progression
          const pct = Math.round(((i + 1) / total) * 100);
          progressBar.style.width = `${pct}%`;
          progressPercent.textContent = `${pct}%`;
        }

        progressStatus.textContent = `Opération terminée. ${successCount} stagiaires créés.`;
        showToast(`Importation unitaire terminée : ${successCount}/${total} stagiaires ajoutés ! 🎉`, "success");
        setTimeout(() => finishImportSession(), 1500);
      }

      function finishImportSession() {
        document.getElementById("import-progress-zone").classList.add("hidden");
        document.getElementById("import-file-input").value = "";
        CURRENT_IMPORT_FILE = null;
        CLIENT_SIDE_PARSED_ROWS = null;
        refreshData(); // Recharger le cache global data pour mettre à jour les listes et graphiques
      }
      
      // ── BADGES ──────────────────────────────────────────────────────────────
      function riskBadge(label) {
        if (!label) return '<span class="badge badge-grey">—</span>';
        const map = {
          Faible: "badge-green",
          Moyen: "badge-orange",
          "Élevé": "badge-red",
          on_time: "badge-green",
          late: "badge-orange",
          missed_checkin: "badge-red",
          absent: "badge-red",
          early_checkout: "badge-orange",
          completed: "badge-green",
          "Présent": "badge-green",
          Retard: "badge-orange",
        };
        return `<span class="badge ${map[label] || "badge-grey"}">${label.replace("_", " ")}</span>`;
      }
      function statusBadge(status, need_att) {
        if (need_att)
          return `<span class="badge badge-red">âš  ${status || "alerte"}</span>`;
        return riskBadge(status);
      }
      function fmtTime(iso) {
        if (!iso) return "—";
        try {
          return new Date(iso).toLocaleTimeString("fr-FR", {
            hour: "2-digit",
            minute: "2-digit",
          });
        } catch {
          return "—";
        }
      }
      function fmtDate(iso) {
        if (!iso) return "—";
        try {
          return new Date(iso).toLocaleDateString("fr-FR", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
          });
        } catch {
          return "—";
        }
      }
      function initials(first, last) {
        return ((first || "")[0] || "") + ((last || "")[0] || "");
      }

      // ── ★ BADGE PDF GENERATION ──────────────────────────────────────────────
      function generateBadgePDF(internId, fullName, serviceName) {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({
          orientation: "portrait",
          unit: "mm",
          format: [85, 120],
        });

        // Render QR code into hidden div
        const qrDiv = document.getElementById("qr-hidden");
        qrDiv.innerHTML = "";
        const qr = new QRCode(qrDiv, {
          text: internId,
          width: 256,
          height: 256,
          colorDark: "#0a0d12",
          colorLight: "#ffffff",
        });

        setTimeout(() => {
          const qrCanvas = qrDiv.querySelector("canvas");
          if (!qrCanvas) {
            showToast("Erreur génération QR code", "error");
            return;
          }
          const qrImage = qrCanvas.toDataURL("image/png");

          // Background
          doc.setFillColor(245, 247, 250);
          doc.rect(0, 0, 85, 120, "F");

          // Blue header band (top 25mm)
          doc.setFillColor(30, 136, 229);
          doc.rect(0, 0, 85, 25, "F");
          doc.setTextColor(255, 255, 255);
          doc.setFont("helvetica", "bold");
          doc.setFontSize(12);
          doc.text("CENTRE HOSPITALIER", 42.5, 12, { align: "center" });
          doc.setFontSize(8);
          doc.text("CARTE D'ACCÈS STAGIAIRE", 42.5, 18, { align: "center" });

          // Name — auto-shrink
          const nameText = fullName.toUpperCase();
          let fs = 16;
          doc.setFont("helvetica", "bold");
          while (
            (doc.getStringUnitWidth(nameText) * fs) / doc.internal.scaleFactor >
              77 &&
            fs > 8
          )
            fs--;
          doc.setFontSize(fs);
          doc.setTextColor(10, 13, 18);
          doc.text(nameText, 42.5, 45, { align: "center" });

          // Service — auto-shrink if name is long
          const serviceText = "SERVICE : " + serviceName.toUpperCase();
          let sfSize = 10;
          doc.setFont("helvetica", "normal");
          while (
            (doc.getStringUnitWidth(serviceText) * sfSize) /
              doc.internal.scaleFactor >
              77 &&
            sfSize > 7
          )
            sfSize--;
          doc.setFontSize(sfSize);
          doc.setTextColor(100, 100, 100);
          const serviceLines = doc.splitTextToSize(serviceText, 77);
          if (serviceLines.length === 1) {
            doc.text(serviceLines[0], 42.5, 53, { align: "center" });
          } else {
            doc.text(serviceLines[0], 42.5, 50, { align: "center" });
            doc.text(serviceLines[1], 42.5, 55, { align: "center" });
          }

          // QR frame
          doc.setDrawColor(200, 200, 200);
          doc.rect(20, 62, 45, 45);
          doc.addImage(qrImage, "PNG", 22.5, 64.5, 40, 40);

          // UUID footer
          doc.setFontSize(7);
          doc.setTextColor(150, 150, 150);
          doc.text("UUID: " + internId, 42.5, 114, { align: "center" });

          doc.save(`badge_${fullName.replace(/\s+/g, "_")}.pdf`);
          showToast(`Badge de ${fullName} téléchargé`, "success");
        }, 400);
      }

      // ── ★ EXCEL EXPORT ───────────────────────────────────────────────────────
      async function exportExcel() {
        const btn = document.getElementById("btn-excel-export");
        btn.disabled = true;
        btn.innerHTML =
          '<span class="spinner" style="width:12px;height:12px;border-width:2px"></span><span>Export…</span>';
        try {
          const res = await apiFetch("/export/excel");
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Erreur ${res.status}`);
          }
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "CHU_Pointages.xlsx";
          a.click();
          URL.revokeObjectURL(url);
          showToast("Fichier Excel téléchargé", "success");
        } catch (e) {
          showToast("Export Excel : " + e.message, "error");
        } finally {
          btn.disabled = false;
          btn.innerHTML =
            '<span class="material-symbols-outlined">table_view</span><span>Exporter Excel</span>';
        }
      }

