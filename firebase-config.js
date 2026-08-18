export const firebaseConfig = {
  apiKey: "AIzaSyBEuP98gu00m1X2JxKSGqYsVYG8oU_ek-I",
  authDomain: "oregano-2v2-tournament.firebaseapp.com",
  projectId: "oregano-2v2-tournament",
  storageBucket: "oregano-2v2-tournament.firebasestorage.app",
  messagingSenderId: "921367151742",
  appId: "1:921367151742:web:d658598249ee300feb042f"
};

// Live-page-only layout adjustment: place Tournament History beside the live-format description.
if (typeof window !== 'undefined' && (window.location.pathname === '/' || window.location.pathname.endsWith('/index.html') || window.location.pathname.endsWith('/Oregono-2v2-Tournament/'))) {
  const style = document.createElement('style');
  style.textContent = `
    .site-header > p + .previous-winner + .history-link {
      position:absolute;
      right:0;
      top:108px;
      margin-top:0;
      white-space:nowrap;
    }
    @media(max-width:800px){
      .site-header > p + .previous-winner + .history-link {
        position:static;
        display:inline-block;
        margin-top:8px;
      }
    }
  `;
  document.head.appendChild(style);

  // Show the already-selected bracket maps on the public viewer even before
  // Pool Play is locked or the bracket object has been created.
  import('https://www.gstatic.com/firebasejs/12.1.0/firebase-app.js').then(async ({ initializeApp, getApps }) => {
    const [{ getFirestore, doc, onSnapshot }] = await Promise.all([
      import('https://www.gstatic.com/firebasejs/12.1.0/firebase-firestore.js')
    ]);
    const app = getApps().find(a => a.name === 'viewer-map-preview') || initializeApp(firebaseConfig, 'viewer-map-preview');
    const db = getFirestore(app);
    const ref = doc(db, 'tournaments', 'oregano-2v2');
    const labels = [
      'Winners Semi-Final 1',
      'Winners Semi-Final 2',
      'Winners Final',
      'Losers Semi-Final',
      'Losers Final',
      'First Place Match 1',
      'First Place Match 2'
    ];
    const escapeHtml = value => String(value ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
    const render = state => {
      const maps = Array.isArray(state?.pendingBracketMaps) ? state.pendingBracketMaps : [];
      const bracket = state?.bracket || {};
      const keys = ['wb1','wb2','wbf','lb1','lb2','fp1','fp2'];
      const selected = keys.map((key, i) => bracket?.[key]?.map || maps[i] || null);
      const any = selected.some(Boolean);
      let panel = document.querySelector('#preBracketMaps');
      if (!any) {
        if (panel) panel.style.display = 'none';
        return;
      }
      if (!panel) {
        panel = document.createElement('section');
        panel.id = 'preBracketMaps';
        panel.className = 'panel';
        const bracketPanel = document.querySelector('#bracket-panel');
        bracketPanel?.parentNode?.insertBefore(panel, bracketPanel);
      }
      panel.style.display = 'block';
      panel.innerHTML = `<h2>Bracket Maps</h2><div class="small">Maps selected by the admin are shown here even before Pool Play is locked and before the bracket is created.</div><div class="pre-bracket-map-grid">${labels.map((label,i) => `<div class="pre-bracket-map-card"><b>${label}</b><span>${selected[i] ? `Map: ${escapeHtml(selected[i])}` : 'Map not assigned yet'}</span></div>`).join('')}</div>`;
    };
    onSnapshot(ref, snapshot => render(snapshot.exists() ? snapshot.data() : {}));
  }).catch(() => {});

  const mapStyle = document.createElement('style');
  mapStyle.textContent = `
    .pre-bracket-map-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:14px}
    .pre-bracket-map-card{background:#0d151e;border:1px solid #293a4a;border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:6px}
    .pre-bracket-map-card span{color:#55d6c2;font-weight:800}
    @media(max-width:700px){.pre-bracket-map-grid{grid-template-columns:1fr}}
  `;
  document.head.appendChild(mapStyle);
}
