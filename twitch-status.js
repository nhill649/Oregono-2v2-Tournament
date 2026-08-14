// Twitch live-status connector for the R6 tournament tracker.
// Required environment variables: TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, FIREBASE_SERVICE_ACCOUNT_JSON
// This connector handles Twitch presence only. R6 HUD/stat extraction requires a separate video-processing worker.
const { initializeApp, cert } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');

const streams = [
  { slot: 1, player: 'Thunderpants324', channel: 'nhill_3' },
  { slot: 2, player: 'Prestochango884', channel: '' },
  { slot: 3, player: 'XaJoPaSa', channel: '' },
  { slot: 4, player: 'Nitro lox', channel: '' },
  { slot: 5, player: 'Muffinman', channel: '' },
  { slot: 6, player: 'Restoredcamp884', channel: '' },
  { slot: 7, player: 'PatentHorse2227', channel: '' },
  { slot: 8, player: 'EZ Vxvid', channel: '' }
].filter(x => x.channel);

async function getAppToken() {
  const body = new URLSearchParams({
    client_id: process.env.TWITCH_CLIENT_ID,
    client_secret: process.env.TWITCH_CLIENT_SECRET,
    grant_type: 'client_credentials'
  });
  const r = await fetch('https://id.twitch.tv/oauth2/token', { method: 'POST', body });
  if (!r.ok) throw new Error(`Twitch token request failed: ${r.status}`);
  return (await r.json()).access_token;
}

async function main() {
  if (!process.env.TWITCH_CLIENT_ID || !process.env.TWITCH_CLIENT_SECRET || !process.env.FIREBASE_SERVICE_ACCOUNT_JSON) {
    throw new Error('Missing TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, or FIREBASE_SERVICE_ACCOUNT_JSON.');
  }
  const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT_JSON);
  initializeApp({ credential: cert(serviceAccount) });
  const db = getFirestore();
  const token = await getAppToken();
  const headers = { 'Client-Id': process.env.TWITCH_CLIENT_ID, Authorization: `Bearer ${token}` };

  const users = await Promise.all(streams.map(async s => {
    const r = await fetch(`https://api.twitch.tv/helix/users?login=${encodeURIComponent(s.channel)}`, { headers });
    if (!r.ok) throw new Error(`Twitch user lookup failed for ${s.channel}: ${r.status}`);
    const data = await r.json();
    return { ...s, user: data.data?.[0] || null };
  }));

  const ids = users.filter(x => x.user).map(x => x.user.id);
  const liveById = new Map();
  if (ids.length) {
    const r = await fetch(`https://api.twitch.tv/helix/streams?${ids.map(id => `user_id=${encodeURIComponent(id)}`).join('&')}`, { headers });
    if (!r.ok) throw new Error(`Twitch stream lookup failed: ${r.status}`);
    for (const stream of (await r.json()).data || []) liveById.set(stream.user_id, stream);
  }

  const status = users.map(s => ({
    slot: s.slot,
    player: s.player,
    channel: s.channel,
    twitchUserId: s.user?.id || null,
    live: !!(s.user && liveById.has(s.user.id)),
    streamId: s.user ? liveById.get(s.user.id)?.id || null : null,
    startedAt: s.user ? liveById.get(s.user.id)?.started_at || null : null,
    checkedAt: new Date().toISOString()
  }));

  await db.doc('tournaments/oregano-stats').set({ twitchStatus: status, twitchStatusCheckedAt: new Date().toISOString() }, { merge: true });
  console.log(JSON.stringify(status, null, 2));
}

main().catch(err => { console.error(err); process.exit(1); });
