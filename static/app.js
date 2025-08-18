let activeInput = null;

document.addEventListener("click", e => {
  if (e.target.matches("input.field")) {
    activeInput = e.target;
  }
  if (e.target.matches("#revealBtn")) {
    const sol = window.__SOLUTION__ || [];
    document.querySelectorAll("input.field").forEach((inp, idx) => inp.value = sol[idx] ?? "");
  }
  if (e.target.matches(".chip")) {
    if (activeInput) {
      const v = JSON.parse(e.target.dataset.val);
      activeInput.value = v;
      activeInput.focus();
    }
  }
  if (e.target.matches("#checkBtn")) {
    e.preventDefault();
    const answers = [...document.querySelectorAll("input.field")]
      .sort((a,b)=>parseInt(a.dataset.index)-parseInt(b.dataset.index))
      .map(inp => inp.value);
    fetch(`/check/${window.__SNIP_ID__}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({answers})
    })
    .then(r => r.json())
    .then(res => {
      const fb = document.getElementById("feedback");
      fb.innerHTML = "";
      if (res.ok) {
        fb.innerHTML = `<div class="badge-ok">Alles korrekt 🎉</div>`;
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
});

function escapeHtml(s) {
  return (s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}
