// RideSync Frontend UX Helpers (No database or auth logic)

document.addEventListener("DOMContentLoaded", () => {
  // Mobile navigation toggle
  const navToggle = document.getElementById("navToggle");
  const navLinks = document.getElementById("navLinks");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      const isOpen = navLinks.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  // Dismiss alert banners
  document.querySelectorAll(".alert-close").forEach((btn) => {
    btn.addEventListener("click", () => {
      const alertEl = btn.closest(".alert");
      if (alertEl) {
        alertEl.remove();
      }
    });
  });

  // Confirmation prompts for destructive or state-changing actions
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const msg = form.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // Live fare calculator on ride details / request form
  const seatsInput = document.getElementById("seats_requested");
  const farePreview = document.getElementById("farePreview");
  if (seatsInput && farePreview) {
    const unitPrice = parseFloat(farePreview.dataset.unitPrice || "0");
    const updateFare = () => {
      const qty = parseInt(seatsInput.value || "1", 10);
      if (!Number.isNaN(qty) && qty > 0) {
        farePreview.textContent = "Rs. " + (unitPrice * qty).toFixed(2);
      }
    };
    seatsInput.addEventListener("input", updateFare);
    updateFare();
  }

  // Toggle "New Location" fields in Offer Ride / Update Ride forms
  document.querySelectorAll("[data-location-select]").forEach((selectEl) => {
    const targetId = selectEl.getAttribute("data-location-select");
    const panel = document.getElementById(targetId);
    if (!panel) return;

    const togglePanel = () => {
      const isNew = selectEl.value === "__new__";
      panel.style.display = isNew ? "block" : "none";
      panel.querySelectorAll("[data-required-when-new]").forEach((input) => {
        input.required = isNew;
      });
    };

    selectEl.addEventListener("change", togglePanel);
    togglePanel();
  });

  // Open native calendar picker when clicking anywhere on date inputs
  document.querySelectorAll('input[type="date"]').forEach((pickerInput) => {
    pickerInput.addEventListener("click", () => {
      if (typeof pickerInput.showPicker === "function") {
        try {
          pickerInput.showPicker();
        } catch (_err) {
          // Ignore browsers that restrict showPicker() on certain interactions
        }
      }
    });
  });

  // Custom 24-hour Analog Clock Picker
  const clockInputs = document.querySelectorAll("input[data-clock-picker]");
  if (clockInputs.length > 0) {
    const backdrop = document.createElement("div");
    backdrop.className = "clock-modal-backdrop";
    backdrop.setAttribute("role", "dialog");
    backdrop.setAttribute("aria-modal", "true");
    backdrop.setAttribute("aria-label", "24-Hour Analog Clock Picker");
    backdrop.innerHTML = `
      <div class="clock-modal">
        <div class="clock-modal-header">
          <div class="clock-mode-label" id="clockModeLabel">Select Hour (24h)</div>
          <div class="clock-readout">
            <button type="button" class="clock-seg-btn active" id="clockHourBtn">09</button>
            <span>:</span>
            <button type="button" class="clock-seg-btn" id="clockMinuteBtn">00</button>
          </div>
        </div>
        <div class="clock-face" id="clockFace">
          <div class="clock-center-dot"></div>
          <div class="clock-hand" id="clockHand"></div>
          <div id="clockNumbers"></div>
        </div>
        <div class="clock-modal-actions">
          <button type="button" class="btn outline btn-sm" id="clockCancelBtn">Cancel</button>
          <button type="button" class="btn primary btn-sm" id="clockConfirmBtn">Confirm</button>
        </div>
      </div>
    `;
    document.body.appendChild(backdrop);

    const modeLabel = document.getElementById("clockModeLabel");
    const hourBtn = document.getElementById("clockHourBtn");
    const minuteBtn = document.getElementById("clockMinuteBtn");
    const clockFace = document.getElementById("clockFace");
    const clockHand = document.getElementById("clockHand");
    const clockNumbers = document.getElementById("clockNumbers");
    const cancelBtn = document.getElementById("clockCancelBtn");
    const confirmBtn = document.getElementById("clockConfirmBtn");

    let activeInput = null;
    let mode = "hour"; // "hour" | "minute"
    let selectedHour = 9;
    let selectedMinute = 0;

    const pad2 = (n) => String(n).padStart(2, "0");

    const updateReadout = () => {
      hourBtn.textContent = pad2(selectedHour);
      minuteBtn.textContent = pad2(selectedMinute);
      hourBtn.classList.toggle("active", mode === "hour");
      minuteBtn.classList.toggle("active", mode === "minute");
      modeLabel.textContent = mode === "hour" ? "Select Hour (24h)" : "Select Minute";
    };

    const renderFace = () => {
      clockNumbers.innerHTML = "";
      const cx = 132;
      const cy = 132;

      if (mode === "hour") {
        // Material 24h dial: Outer ring 12, 1..11; Inner ring 00, 13..23
        for (let i = 0; i < 12; i++) {
          const angleDeg = i * 30;
          const angleRad = ((angleDeg - 90) * Math.PI) / 180;

          const outerVal = i === 0 ? 12 : i;
          const outerEl = document.createElement("div");
          outerEl.className = "clock-num" + (selectedHour === outerVal ? " selected" : "");
          outerEl.textContent = String(outerVal);
          outerEl.style.left = `${cx + 102 * Math.cos(angleRad)}px`;
          outerEl.style.top = `${cy + 102 * Math.sin(angleRad)}px`;
          outerEl.dataset.val = String(outerVal);
          clockNumbers.appendChild(outerEl);

          const innerVal = i === 0 ? 0 : i + 12;
          const innerEl = document.createElement("div");
          innerEl.className = "clock-num inner" + (selectedHour === innerVal ? " selected" : "");
          innerEl.textContent = innerVal === 0 ? "00" : String(innerVal);
          innerEl.style.left = `${cx + 66 * Math.cos(angleRad)}px`;
          innerEl.style.top = `${cy + 66 * Math.sin(angleRad)}px`;
          innerEl.dataset.val = String(innerVal);
          clockNumbers.appendChild(innerEl);
        }

        const handAngle = (selectedHour % 12) * 30;
        const isInner = selectedHour === 0 || selectedHour >= 13;
        clockHand.style.height = isInner ? "66px" : "102px";
        clockHand.style.transform = `translateX(-50%) rotate(${handAngle}deg)`;
      } else {
        // Minute ring: 00, 05, 10 .. 55
        for (let i = 0; i < 12; i++) {
          const val = i * 5;
          const angleDeg = i * 30;
          const angleRad = ((angleDeg - 90) * Math.PI) / 180;
          const el = document.createElement("div");
          el.className = "clock-num" + (selectedMinute === val ? " selected" : "");
          el.textContent = pad2(val);
          el.style.left = `${cx + 102 * Math.cos(angleRad)}px`;
          el.style.top = `${cy + 102 * Math.sin(angleRad)}px`;
          el.dataset.val = String(val);
          clockNumbers.appendChild(el);
        }

        const handAngle = selectedMinute * 6;
        clockHand.style.height = "102px";
        clockHand.style.transform = `translateX(-50%) rotate(${handAngle}deg)`;
      }

      updateReadout();
    };

    const pickFromPointer = (clientX, clientY, autoAdvance) => {
      const rect = clockFace.getBoundingClientRect();
      const dx = clientX - (rect.left + rect.width / 2);
      const dy = clientY - (rect.top + rect.height / 2);
      const dist = Math.hypot(dx, dy);
      let deg = (Math.atan2(dy, dx) * 180) / Math.PI + 90;
      if (deg < 0) deg += 360;

      if (mode === "hour") {
        const sector = Math.round(deg / 30) % 12;
        const isInner = dist < 84;
        if (isInner) {
          selectedHour = sector === 0 ? 0 : sector + 12;
        } else {
          selectedHour = sector === 0 ? 12 : sector;
        }
        renderFace();
        if (autoAdvance) {
          mode = "minute";
          renderFace();
        }
      } else {
        selectedMinute = Math.round(deg / 6) % 60;
        renderFace();
      }
    };

    let isDragging = false;
    clockFace.addEventListener("pointerdown", (e) => {
      isDragging = true;
      clockFace.setPointerCapture(e.pointerId);
      const numEl = e.target.closest(".clock-num");
      if (numEl && numEl.dataset.val !== undefined) {
        const val = parseInt(numEl.dataset.val, 10);
        if (mode === "hour") {
          selectedHour = val;
          renderFace();
        } else {
          selectedMinute = val;
          renderFace();
        }
      } else {
        pickFromPointer(e.clientX, e.clientY, false);
      }
    });

    clockFace.addEventListener("pointermove", (e) => {
      if (!isDragging) return;
      pickFromPointer(e.clientX, e.clientY, false);
    });

    clockFace.addEventListener("pointerup", (e) => {
      if (!isDragging) return;
      isDragging = false;
      if (mode === "hour") {
        mode = "minute";
        renderFace();
      }
    });

    hourBtn.addEventListener("click", () => {
      mode = "hour";
      renderFace();
    });

    minuteBtn.addEventListener("click", () => {
      mode = "minute";
      renderFace();
    });

    const openClockFor = (inputEl) => {
      activeInput = inputEl;
      const val = (inputEl.value || "").trim();
      const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(val);
      if (match) {
        selectedHour = parseInt(match[1], 10);
        selectedMinute = parseInt(match[2], 10);
      } else {
        const now = new Date();
        selectedHour = now.getHours();
        selectedMinute = now.getMinutes();
      }
      mode = "hour";
      renderFace();
      backdrop.classList.add("open");
    };

    const closeClock = () => {
      backdrop.classList.remove("open");
      activeInput = null;
    };

    cancelBtn.addEventListener("click", closeClock);
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) closeClock();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && backdrop.classList.contains("open")) {
        closeClock();
      }
    });

    confirmBtn.addEventListener("click", () => {
      if (activeInput) {
        activeInput.value = `${pad2(selectedHour)}:${pad2(selectedMinute)}`;
        activeInput.dispatchEvent(new Event("input", { bubbles: true }));
        activeInput.dispatchEvent(new Event("change", { bubbles: true }));
      }
      closeClock();
    });

    clockInputs.forEach((inputEl) => {
      inputEl.addEventListener("click", () => openClockFor(inputEl));
      inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openClockFor(inputEl);
        }
      });
    });

    document.querySelectorAll("[data-clock-for]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = document.getElementById(btn.getAttribute("data-clock-for"));
        if (target) openClockFor(target);
      });
    });
  }
});
