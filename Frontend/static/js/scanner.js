// ── SOUNDS ────────────────────────────────────────────────────────────────
      let audioCtx;
      function getAudioCtx() {
        if (!audioCtx)
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === "suspended") audioCtx.resume();
        return audioCtx;
      }
      function chime(freq, start, dur, type = "sine", gain = 0.32) {
        const ac = getAudioCtx();
        const osc = ac.createOscillator();
        const env = ac.createGain();
        osc.connect(env);
        env.connect(ac.destination);
        osc.type = type;
        osc.frequency.setValueAtTime(freq, ac.currentTime + start);
        env.gain.setValueAtTime(0, ac.currentTime + start);
        env.gain.linearRampToValueAtTime(gain, ac.currentTime + start + 0.02);
        env.gain.exponentialRampToValueAtTime(
          0.001,
          ac.currentTime + start + dur,
        );
        osc.start(ac.currentTime + start);
        osc.stop(ac.currentTime + start + dur);
      }
      function playSuccessSound() {
        chime(660, 0.0, 0.55, "sine", 0.32);
        chime(880, 0.18, 0.55, "sine", 0.3);
        chime(1100, 0.36, 0.7, "sine", 0.28);
      }
      function playErrorSound() {
        chime(370, 0.0, 0.3, "square", 0.18);
        chime(260, 0.25, 0.45, "square", 0.16);
      }
      function playWarningSound() {
        chime(550, 0.0, 0.45, "sine", 0.28);
        chime(490, 0.3, 0.55, "sine", 0.25);
      }

      const API_URL = window.location.origin + "/scan";
      const RESUME_DELAY = 10000;
      let qrCode = null;
      let scanLocked = false;
      let resumeTimer = null;
      let isRunning = false;
      let availableCameras = [];

      // ── AUDIO CONTEXT (lazy-init on first user gesture) ──────────────────────
      let _audioCtx = null;

      function getAudioCtx() {
        if (!_audioCtx) {
          _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        // Resume in case it was suspended (browser autoplay policy)
        if (_audioCtx.state === "suspended") {
          _audioCtx.resume();
        }
        return _audioCtx;
      }

      /**
       * playChime(type)
       *  "success" → two ascending tones (pleasant "ding-ding")
       *  "warning" → single mid tone (neutral beep)
       *  "error"   → short descending tone (low boop)
       *
       * All tones are generated purely with the Web Audio API —
       * no external files required.
       */
      function playChime(type = "success") {
        const ctx = getAudioCtx();
        const masterGain = ctx.createGain();
        masterGain.gain.setValueAtTime(0.18, ctx.currentTime); // gentle volume
        masterGain.connect(ctx.destination);

        const schedules = {
          // Two ascending sine tones: C5 (523 Hz) then E5 (659 Hz)
          success: [
            { freq: 523.25, start: 0, dur: 0.18, type: "sine" },
            { freq: 659.25, start: 0.16, dur: 0.28, type: "sine" },
          ],
          // Single mid tone: A4 (440 Hz)
          warning: [{ freq: 440, start: 0, dur: 0.25, type: "sine" }],
          // Short descending: E4 (330 Hz)
          error: [{ freq: 330, start: 0, dur: 0.22, type: "sine" }],
        };

        const notes = schedules[type] || schedules.success;

        notes.forEach(({ freq, start, dur, type: waveType }) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();

          osc.type = waveType;
          osc.frequency.setValueAtTime(freq, ctx.currentTime + start);

          // Smooth fade-in + fade-out to avoid clicks
          gain.gain.setValueAtTime(0, ctx.currentTime + start);
          gain.gain.linearRampToValueAtTime(1, ctx.currentTime + start + 0.04);
          gain.gain.setValueAtTime(1, ctx.currentTime + start + dur - 0.06);
          gain.gain.linearRampToValueAtTime(0, ctx.currentTime + start + dur);

          osc.connect(gain);
          gain.connect(masterGain);

          osc.start(ctx.currentTime + start);
          osc.stop(ctx.currentTime + start + dur + 0.01);
        });
      }

      // Warm up the AudioContext on first user interaction
      document.addEventListener("click", getAudioCtx, { once: true });

      // ── STATUS ─────────────────────────────────────────────────────────────────
      function setStatus(type, icon, label, msg) {
        document.getElementById("statusPanel").className =
          "status-panel " + (type || "");
        document.getElementById("statusIcon").textContent = icon;
        document.getElementById("statusLabel").textContent = label;
        document.getElementById("statusMsg").textContent = msg;
      }

      function setLoadingStatus() {
        document.getElementById("statusPanel").className = "status-panel";
        document.getElementById("statusIcon").innerHTML =
          '<div class="spinner"></div>';
        document.getElementById("statusLabel").textContent = "Envoi en cours";
        document.getElementById("statusMsg").textContent =
          "Communication avec le serveur…";
      }

      function setBtns(running) {
        document.getElementById("btnStart").disabled = running;
        document.getElementById("btnStop").disabled = !running;
      }

      // ── POPULATE CAMERA LIST ───────────────────────────────────────────────────
      async function populateCameraList() {
        try {
          const tmp = await navigator.mediaDevices.getUserMedia({
            video: true,
          });
          tmp.getTracks().forEach((t) => t.stop());

          availableCameras = await Html5Qrcode.getCameras();
          if (!availableCameras || availableCameras.length === 0) return;

          const sel = document.getElementById("camSelect");
          sel.innerHTML = "";
          availableCameras.forEach((cam, i) => {
            const opt = document.createElement("option");
            opt.value = cam.id;
            const label = cam.label || `Caméra ${i + 1}`;
            const isRear = /back|rear|environment|arrière/i.test(label);
            opt.textContent = isRear ? `📷 ${label} (arrière)` : `📷 ${label}`;
            opt.dataset.isRear = isRear;
            sel.appendChild(opt);
          });

          const rearOption = Array.from(sel.options).find(
            (o) => o.dataset.isRear === "true",
          );
          if (rearOption) rearOption.selected = true;

          if (availableCameras.length > 1) {
            document.getElementById("camSelectWrap").style.display = "flex";
          }
        } catch (e) {}
      }

      // ── START ──────────────────────────────────────────────────────────────────
      async function startScanner() {
        if (isRunning) return;
        clearResult();
        setBtns(true);

        setStatus("", "🔐", "Permission caméra", "Autorisation en cours…");
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: true,
          });
          stream.getTracks().forEach((t) => t.stop());
        } catch (err) {
          isRunning = false;
          setBtns(false);
          setStatus(
            "error",
            "🚫",
            "Accès refusé",
            "Autorisez l'accès à la caméra dans les paramètres du navigateur.",
          );
          return;
        }

        await populateCameraList();

        setStatus("", "⏳", "Initialisation", "Recherche des caméras…");
        qrCode = new Html5Qrcode("reader", { verbose: false });

        try {
          const devices = await Html5Qrcode.getCameras();
          if (!devices || devices.length === 0)
            throw new Error("Aucune caméra détectée.");

          const rearCamera = devices.find((d) => {
            const label = d.label.toLowerCase();
            return (
              label.includes("back") ||
              label.includes("rear") ||
              label.includes("environment") ||
              label.includes("arrière")
            );
          });

          const selectedCamera = rearCamera || devices[0];

          setStatus("", "⏳", "Démarrage", `Utilisation de caméra`);

          await qrCode.start(
            selectedCamera.id,
            { fps: 25, qrbox: { width: 250, height: 250 } },
            onScanSuccess,
            () => {},
          );

          isRunning = true;
          document.getElementById("camIdle").style.display = "none";
          document.getElementById("viewfinder").classList.add("active");
          setStatus("", "📷", "En attente", `Approchez un QR code`);
        } catch (err) {
          isRunning = false;
          setBtns(false);
          setStatus(
            "error",
            "⚠️",
            "Caméra inaccessible",
            err?.message || "Aucune caméra disponible ou accès refusé.",
          );
        }
      }

      // ── STOP ───────────────────────────────────────────────────────────────────
      async function stopScanner() {
        clearTimeout(resumeTimer);
        if (qrCode && isRunning) {
          try {
            await qrCode.stop();
          } catch (e) {}
          try {
            qrCode.clear();
          } catch (e) {}
          qrCode = null;
        }
        isRunning = false;
        scanLocked = false;
        setBtns(false);
        document.getElementById("camIdle").style.display = "flex";
        document.getElementById("viewfinder").classList.remove("active");
        clearResult();
        setStatus("", "💤", "Caméra", "Arrêtée — appuyez sur Démarrer");
      }

      // ── ON SCAN ────────────────────────────────────────────────────────────────
      async function onScanSuccess(decodedText) {
        if (scanLocked) return;
        scanLocked = true;

        if (navigator.vibrate) navigator.vibrate([80, 40, 80]);

        try {
          qrCode.pause(true);
        } catch (e) {}

        setLoadingStatus();

        try {
          const res = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ intern_id: decodedText }),
          });
          const data = await res.json();

          if (res.ok) {
            const msg = data.message || data.status || JSON.stringify(data);

            const isOutOfWindow =
              msg.includes("refusé") ||
              msg.includes("n'est ouvert") ||
              msg.includes("créneau");

            if (isOutOfWindow) {
              playWarningSound();
              setStatus("warning", "🕐", "Hors créneau", msg);
              showResult(
                "warn",
                "QR détecté — non enregistré",
                new Date().toLocaleTimeString("fr-FR"),
                msg,
                decodedText,
              );
            } else {
              playSuccessSound();
              setStatus("success", "✅", "Pointage validé", msg);
              showResult(
                "ok",
                "Pointage validé",
                new Date().toLocaleTimeString("fr-FR"),
                msg,
                decodedText,
              );
            }
          } else {
            const errMsg =
              data.detail || data.message || `Erreur ${res.status}`;
            playErrorSound();
            setStatus("error", "❌", "Erreur serveur", errMsg);
            showResult(
              "err",
              "Refusé",
              `Code ${res.status}`,
              errMsg,
              decodedText,
            );
          }
        } catch (err) {
          playErrorSound();
          setStatus(
            "error",
            "⚠️",
            "Erreur réseau",
            "Impossible de joindre le serveur. Vérifiez que FastAPI est lancé.",
          );
          showResult(
            "err",
            "Réseau indisponible",
            "Connexion échouée",
            "Impossible de joindre le serveur. FastAPI doit être lancé.",
            decodedText,
          );
        }

        clearTimeout(resumeTimer);
        resumeTimer = setTimeout(() => {
          clearResult();
          setStatus(
            "",
            "📷",
            "En attente",
            "Approchez un QR code de la caméra",
          );
          try {
            qrCode.resume();
          } catch (e) {}
          setTimeout(() => {
            scanLocked = false;
          }, 300);
        }, RESUME_DELAY);
      }

      // ── RESULT CARD ────────────────────────────────────────────────────────────
      function showResult(state, title, subtitle, detail, uuid) {
        const icons = { ok: "✅", warn: "🕐", err: "❌" };
        const card = document.getElementById("resultCard");
        card.className = "result-card visible";
        card.innerHTML = `
          <div class="result-header">
            <div class="result-icon ${state}">${icons[state]}</div>
            <div>
              <div class="result-title ${state}">${title}</div>
              <div class="result-subtitle">${subtitle}</div>
            </div>
          </div>
          ${uuid ? `<div class="result-detail"><strong>UUID scanné</strong>${uuid}</div>` : ""}
          ${detail ? `<div class="result-detail"><strong>Réponse serveur</strong>${detail}</div>` : ""}
          <div class="countdown-bar"><div class="countdown-fill ${state === "warn" ? "warn" : ""}" id="cdf"></div></div>
          <button class="btn-scan-next" onclick="skipToNext()">📷 Scanner un autre badge</button>
        `;
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            const f = document.getElementById("cdf");
            if (f)
              f.className = `countdown-fill ${state === "warn" ? "warn " : ""}running`;
          }),
        );
      }

      function skipToNext() {
        clearTimeout(resumeTimer);
        clearResult();
        setStatus("", "📷", "En attente", "Approchez un QR code de la caméra");
        try {
          qrCode.resume();
        } catch (e) {}
        setTimeout(() => {
          scanLocked = false;
        }, 300);
      }

      function clearResult() {
        const card = document.getElementById("resultCard");
        card.className = "result-card";
        card.innerHTML = "";
      }

