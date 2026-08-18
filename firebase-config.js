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

  // Show selected bracket maps directly inside the existing bracket match boxes.
  // This works before Pool Play is locked and before the bracket object is created.
  import('https://www.gstatic.com/firebasejs/12.1.0/firebase-app.js').then(async ({ initializeApp, getApps }) => {
    const [{ getFirestore, doc, onSnapshot }] = await Promise.all([
      import('https://www.gstatic.com/firebasejs/12.1.0/firebase-firestore.js')
    ]);
    const app = getApps().find(a => a.name === 'viewer-map-overlay') || initializeApp(firebaseConfig, 'viewer-map-overlay');
    const db = getFirestore(app);
    const ref = doc(db, 'tournaments', 'oregano-2v2');
    const keys = ['wb1','wb2','wbf','lb1','lb2','fp1','fp2'];
    const positions = [[65,278],[65,523],[65,843],[480,403],[480,843],[885,478],[1235,478]];
    let latest = {};
    const drawMaps = () => {
      const svg = document.querySelector('#bracket');
      if (!svg) return;
      svg.querySelector('#viewerBracketMapLabels')?.remove();
      const bracket = latest?.bracket || {};
      const pending = Array.isArray(latest?.pendingBracketMaps) ? latest.pendingBracketMaps : [];
      const maps = keys.map((key, i) => bracket?.[key]?.map || pending[i] || null);
      if (!maps.some(Boolean)) return;
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('id','viewerBracketMapLabels');
      g.setAttribute('pointer-events','none');
      maps.forEach((map,i)=>{
        if(!map)return;
        const [x,y]=positions[i];
        const rect=document.createElementNS('http://www.w3.org/2000/svg','rect');
        rect.setAttribute('x',x-5);rect.setAttribute('y',y-17);rect.setAttribute('width',Math.max(100,String(map).length*8+32));rect.setAttribute('height',24);rect.setAttribute('rx',5);rect.setAttribute('fill','#17232e');rect.setAttribute('stroke','#55d6c2');
        const text=document.createElementNS('http://www.w3.org/2000/svg','text');
        text.setAttribute('x',x+8);text.setAttribute('y',y);text.setAttribute('font-family','Arial');text.setAttribute('font-size','13');text.setAttribute('font-weight','800');text.setAttribute('fill','#55d6c2');text.textContent=`MAP: ${String(map)}`;
        g.appendChild(rect);g.appendChild(text);
      });
      svg.appendChild(g);
    };
    onSnapshot(ref,snapshot=>{latest=snapshot.exists()?snapshot.data():{};drawMaps();});
    new MutationObserver(()=>drawMaps()).observe(document.body,{childList:true,subtree:true});
    window.addEventListener('resize',drawMaps);
  }).catch(()=>{});
}
