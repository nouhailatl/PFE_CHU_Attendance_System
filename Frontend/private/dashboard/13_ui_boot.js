      // ── MODAL ─────────────────────────────────────────────────────────────────
      function openModal(title, desc, actionsHTML) {
        document.getElementById("modal-title").textContent = title;
        document.getElementById("modal-desc").innerHTML = desc;
        document.getElementById("modal-actions").innerHTML = actionsHTML;
        document.getElementById("modal-body").innerHTML = "";
        document.getElementById("modal-overlay").classList.add("open");
      }
      function closeModal() {
        document.getElementById("modal-overlay").classList.remove("open");
      }
      document
        .getElementById("modal-overlay")
        .addEventListener("click", (e) => {
          if (e.target === document.getElementById("modal-overlay"))
            closeModal();
        });

      // ── TOAST ─────────────────────────────────────────────────────────────────
      function showToast(msg, type = "success") {
        const t = document.createElement("div");
        t.className = `toast toast-${type}`;
        const icon = type === "success" ? "check_circle" : "error";
        t.innerHTML = `<span class="material-symbols-outlined">${icon}</span>${msg}`;
        document.getElementById("toast-container").appendChild(t);
        setTimeout(() => {
          t.style.opacity = "0";
          t.style.transform = "translateX(20px)";
          t.style.transition = "all .3s";
          setTimeout(() => t.remove(), 300);
        }, 3500);
      }

      // ── UTIL ──────────────────────────────────────────────────────────────────
      function nextTick(fn) {
        requestAnimationFrame(() => requestAnimationFrame(fn));
      }

      // ── BOOT ──────────────────────────────────────────────────────────────────
      (function boot() {
        AUTH = window.CHU_AUTH || null;
        if (!AUTH || !AUTH.access_token) {
          window.location.href = "/login";
          return;
        }
        initApp();
      })();
