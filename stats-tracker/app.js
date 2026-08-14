const $=id=>document.getElementById(id);
const state={match:{id:'',map:'',platform:'PC',teamA:'Team A',teamB:'Team B',targetRounds:5},players:[],events:[],rounds:[],currentRound:0};
let nextId=1;
function save(){localStorage.setItem('r6StatsTracker',JSON.stringify(state));render()}
function load(){try{const x=JSON.parse(localStorage.getItem('r6StatsTracker'));if(x){Object.assign(state,x);nextId=Math.max(0,...state.players.map(p=>p.id||0))+1}}catch(e){}}
function addPlayer(name='',team='A'){state.players.push({id:nextId++,name:name||`Player ${state.players.length+1}`,team,k:0,d:0,a:0,hs:0,plants:0,disables:0})}
function player(id){return state.players.find(p=>p.id===Number(id))}
function selectOptions(selected=''){return state.players.map(p=>`<option value="${p.id}" ${String(p.id)===String(selected)?'selected':''}>${escapeHtml(p.name)}</option>`).join('')}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function renderPlayers(){
  $('players').innerHTML=state.players.length?state.players.map(p=>`<div class="player"><input data-id="${p.id}" class="pname" value="${escapeHtml(p.name)}"><select data-id="${p.id}" class="pteam"><option value="A" ${p.team==='A'?'selected':''}>${escapeHtml(state.match.teamA||'Team A')}</option><option value="B" ${p.team==='B'?'selected':''}>${escapeHtml(state.match.teamB||'Team B')}</option></select><button class="danger remove" data-id="${p.id}">Remove</button></div>`).join(''):'<div class="muted">Add the players before starting the match.</div>';
  document.querySelectorAll('.pname').forEach(x=>x.oninput=()=>{const p=player(x.dataset.id);if(p)p.name=x.value;save()});
  document.querySelectorAll('.pteam').forEach(x=>x.onchange=()=>{const p=player(x.dataset.id);if(p)p.team=x.value;save()});
  document.querySelectorAll('.remove').forEach(x=>x.onclick=()=>{state.players=state.players.filter(p=>p.id!==Number(x.dataset.id));save()});
}
function renderSelectors(){['killer','victim','objectivePlayer'].forEach(id=>$(id).innerHTML=selectOptions());}
function renderLeaderboard(){const rows=[...state.players].sort((a,b)=>(b.k-b.d)-(a.k-a.d)||b.k-a.k);$('leaderboard').innerHTML=rows.map(p=>`<tr><td>${escapeHtml(p.name)}</td><td>${p.team==='A'?escapeHtml(state.match.teamA):escapeHtml(state.match.teamB)}</td><td>${p.k}</td><td>${p.d}</td><td>${p.a}</td><td>${p.hs}</td><td>${p.plants}</td><td>${p.disables}</td><td>${p.d?(p.k/p.d).toFixed(2):p.k.toFixed(2)}</td></tr>`).join('')||'<tr><td colspan="9" class="muted">No players yet.</td></tr>'}
function renderEvents(){$('events').innerHTML=state.events.slice().reverse().map(e=>`<div class="event">${escapeHtml(e.text)}</div>`).join('')||'<div class="muted">No events recorded.</div>'}
function render(){
  $('matchId').value=state.match.id;$('map').value=state.match.map;$('platform').value=state.match.platform;$('teamA').value=state.match.teamA;$('teamB').value=state.match.teamB;$('targetRounds').value=state.match.targetRounds;
  $('roundLabel').textContent=`Round ${state.currentRound} • Score ${state.rounds.filter(r=>r.winner==='A').length}-${state.rounds.filter(r=>r.winner==='B').length}`;
  renderPlayers();renderSelectors();renderLeaderboard();renderEvents();
}
function setup(){state.match={id:$('matchId').value.trim(),map:$('map').value.trim(),platform:$('platform').value,teamA:$('teamA').value.trim()||'Team A',teamB:$('teamB').value.trim()||'Team B',targetRounds:Number($('targetRounds').value)||5}}
$('newMatch').onclick=()=>{if(!confirm('Reset the current match and all player totals?'))return;setup();state.players=[];state.events=[];state.rounds=[];state.currentRound=0;save()};
['matchId','map','platform','teamA','teamB','targetRounds'].forEach(id=>$(id).addEventListener('change',()=>{setup();save()}));
$('addPlayer').onclick=()=>{addPlayer();save()};
function recordRound(winner){state.currentRound++;state.rounds.push({round:state.currentRound,winner});state.events.push({text:`Round ${state.currentRound}: ${winner==='A'?state.match.teamA:state.match.teamB} wins`});save()}
$('roundA').onclick=()=>recordRound('A');$('roundB').onclick=()=>recordRound('B');
$('undoRound').onclick=()=>{if(!state.rounds.length)return;state.rounds.pop();state.currentRound=Math.max(0,state.currentRound-1);state.events.push({text:'Last round result undone'});save()};
$('addKill').onclick=()=>{const k=player($('killer').value),v=player($('victim').value);if(!k||!v||k.id===v.id)return alert('Choose two different players.');k.k++;v.d++;if($('hs').checked)k.hs++;state.events.push({text:`${k.name} eliminated ${v.name}${$('hs').checked?' (HS)':''}`});$('hs').checked=false;save()};
$('plant').onclick=()=>{const p=player($('objectivePlayer').value);if(!p)return;p.plants++;state.events.push({text:`${p.name} planted the defuser`});save()};
$('disable').onclick=()=>{const p=player($('objectivePlayer').value);if(!p)return;p.disables++;state.events.push({text:`${p.name} disabled the defuser`});save()};
$('export').onclick=()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`r6-${state.match.id||'match'}.json`;a.click();URL.revokeObjectURL(a.href)};
$('import').onchange=e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();r.onload=()=>{try{const x=JSON.parse(r.result);if(!x.players||!x.match)throw Error();Object.assign(state,x);nextId=Math.max(0,...state.players.map(p=>p.id||0))+1;save()}catch(_){alert('That file is not a valid R6 tracker export.')}};r.readAsText(f)};
load();render();
