export const firebaseConfig = {
  apiKey: "AIzaSyBEuP98gu00m1X2JxKSGqYsVYG8oU_ek-I",
  authDomain: "oregano-2v2-tournament.firebaseapp.com",
  projectId: "oregano-2v2-tournament",
  storageBucket: "oregano-2v2-tournament.firebasestorage.app",
  messagingSenderId: "921367151742",
  appId: "1:921367151742:web:d658598249ee300feb042f"
};

// Live-page-only layout adjustment: place Tournament History beside the live-format description.
if (typeof window !== 'undefined' && (window.location.pathname === '/' || window.location.pathname.endsWith('/index.html') || window.location.pathname.endsWith('/Oregono-2v2-Tournament/') || window.location.pathname.endsWith('/Oregono-2v2-Tournament'))) {
  const style = document.createElement('style');
  style.textContent = `
    .site-header > p + .previous-winner + .history-link { position:absolute; left:350px; top:82px; margin-top:0; white-space:nowrap; }
    @media(max-width:800px){
      .site-header > p + .previous-winner + .history-link { position:static; display:inline-block; margin-top:8px; }
    }
  `;
  document.head.appendChild(style);
}
