let activeInput = null;

// Lösung und Snippet-ID aus dem DOM auslesen
const snipDataEl = document.getElementById("snippet-data");
const SOLUTION = JSON.parse(snipDataEl.dataset.solution || "[]");
const SNIP_ID = snipDataEl.dataset.snipId;

document.addEventListener("click", e => {
  // Aktives Input-Feld merken
  if (e.target.matches("input.field")) {
    activeInput = e.target;
  }

  // Lösung einblenden
  if (e.target.matches("#revealBtn")) {
    document.querySelectorAll("input.field").forEach((inp, idx) => inp.value = SOLUTION[idx] ?? "");
  }

  // Baustein in Feld einfügen
  if (e.target.matches(".chip")) {
    let targetInput = activeInput;

    // Wenn kein aktives Feld, erstes Feld auswählen
    if (!targetInput) {
      targetInput = document.querySelector("input.field");
    }

    if (targetInput) {
      let val = e.target.dataset.val;
      try {
        val = JSON.parse(val);
      } catch (err) {
        // val bleibt unverändert
      }
      targetInput.value = val;
      targetInput.focus();
      activeInput = targetInput; // jetzt ist das erste Feld aktiv
    }
  }

  // Antworten prüfen
  if (e.target.matches("#checkBtn")) {
    e.preventDefault();
    const answers = [...document.querySelectorAll("input.field")]
      .sort((a, b) => parseInt(a.dataset.index) - parseInt(b.dataset.index))
      .map(inp => inp.value);

    fetch(`/check/${SNIP_ID}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({answers})
    })
    .then(r => r.json())
    .then(res => {
      const fb = document.getElementById("feedback");
      fb.innerHTML = "";
      fb.style.visibility = "visible";

      if (res.ok) {
        fb.innerHTML = `<div class="badge-ok">Alles korrekt 🎉</div>`;
        const nextBtn = document.getElementById("next-task-btn");
        if (nextBtn) nextBtn.style.display = "inline-block";
      } else {
        const list = res.results.map(r =>
          `<div>Feld ${r.index}: ${r.correct ? 
            '<span class="badge-ok">OK</span>' : 
            `<span class="badge-no">Falsch</span> (erwartet z.B. <code>${escapeHtml(r.expected)}</code>)`}</div>`
        ).join("");
        fb.innerHTML = `<div class="space-y-1">${list}</div>`;
      }
    });
  }

  // Nächste Aufgabe Button klick
  if (e.target.matches("#next-task-btn")) {
    const url = e.target.dataset.url;
    if (url) window.location.href = url;
  }
});

function escapeHtml(s) {
  return (s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}
