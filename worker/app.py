import os, json, time, threading, subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, Header, HTTPException
import firebase_admin
from firebase_admin import credentials, firestore

from processor.r6_detector import detect

app = FastAPI(title='R6 Custom Game Stats Worker')
TOKEN = os.getenv('WORKER_TOKEN', 'change-me')
SERVICE_JSON = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON', '')
if not firebase_admin._apps:
    if SERVICE_JSON:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(SERVICE_JSON)))
    else:
        firebase_admin.initialize_app()
db = firestore.client()
stop_event = threading.Event()
worker_thread = None

# MVP is impact-first. Reinforcements are tracked for completeness but NEVER contribute to MVP.
MVP_WEIGHTS = {'kills':1.00,'assists':0.45,'deaths':-0.55,'headshots':0.15,'plants':1.25,'defusals':1.50,'entryKills':0.75,'entryDeaths':-0.35,'clutches':2.00,'impact':1.00}

def auth(authorization):
    if authorization != f'Bearer {TOKEN}': raise HTTPException(401, 'Unauthorized')

def mvp_score(p: dict) -> float:
    score=sum(float(p.get(k,0) or 0)*w for k,w in MVP_WEIGHTS.items())
    rounds=max(int(p.get('rounds',0) or 0),1)
    score += max(0.0,(rounds-int(p.get('deaths',0) or 0))/rounds)*2.0
    return round(score,2)

def roster_from(data: dict) -> list[str]:
    names=[x.get('name') for x in data.get('playerList',[]) if x.get('name')]
    return names or ['Thunderpants324','Prestochango884','XaJoPaSa','Nitro lox','Muffinman','Restoredcamp884','PatentHorse2227','EZ Vxvid']

def merge_observations(data: dict, observations: list[dict], stream_url: str):
    players=data.setdefault('players',{})
    for obs in observations:
        name=obs['player']
        p=players.setdefault(name,{'name':name,'team':'','kills':0,'deaths':0,'assists':0,'headshots':0,'plants':0,'defusals':0,'entryKills':0,'entryDeaths':0,'clutches':0,'impact':0,'reinforcements':0,'rounds':0,'matches':0,'mvpScore':0})
        for key in ('kills','deaths','assists','headshots','plants','defusals','reinforcements'):
            if key in obs: p[key]=max(int(p.get(key,0) or 0),int(obs[key]))
        p['mvpScore']=mvp_score(p)
    leaders=sorted(players.values(),key=lambda x:x.get('mvpScore',0),reverse=True)
    data['currentMVP']=leaders[0] if leaders else None
    data['mvpHistory']=data.get('mvpHistory',[]); data['workerLastEventAt']=time.time(); data['workerStatus']='processing'
    for stream in data.setdefault('streams',[]):
        if stream.get('url')==stream_url:
            stream['live']=True; stream['status']='R6 video processor connected'; stream['lastFrameAt']=time.time()
    return data

def frame_stream(stream: dict):
    url=stream.get('url','').strip()
    if not url: return
    proc=subprocess.Popen(['streamlink','--stdout',url,'best'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    ff=subprocess.Popen(['ffmpeg','-loglevel','error','-i','pipe:0','-f','image2pipe','-vcodec','mjpeg','-vf','fps=1','-'],stdin=proc.stdout,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    buf=b''; started=time.time(); ref=db.collection('tournaments').document('oregano-stats')
    try:
        while not stop_event.is_set():
            chunk=ff.stdout.read(65536)
            if not chunk: break
            buf+=chunk; a=buf.find(b'\xff\xd8'); b=buf.find(b'\xff\xd9',a+2)
            if a<0 or b<0:
                if len(buf)>2000000: buf=buf[-500000:]
                continue
            jpg=buf[a:b+2]; buf=buf[b+2:]; frame=cv2.imdecode(np.frombuffer(jpg,np.uint8),cv2.IMREAD_COLOR)
            if frame is None: continue
            snap=ref.get(); data=snap.to_dict() or {}; observations=detect(frame,roster_from(data),time.time()-started)
            if observations: ref.set(merge_observations(data,observations,url))
    finally:
        for p in (ff,proc):
            try:p.kill()
            except Exception:pass

def worker_loop():
    while not stop_event.is_set():
        try:
            data=db.collection('tournaments').document('oregano-stats').get().to_dict() or {}
            streams=[s for s in data.get('streams',[]) if s.get('enabled',True) and s.get('url')]
            if not streams: time.sleep(5); continue
            with ThreadPoolExecutor(max_workers=min(8,len(streams))) as pool:
                futures=[pool.submit(frame_stream,s) for s in streams]
                while not stop_event.is_set() and any(not f.done() for f in futures): time.sleep(1)
        except Exception as exc:
            db.collection('tournaments').document('oregano-stats').set({'workerError':str(exc),'workerStatus':'error'},merge=True)
        time.sleep(2)

@app.get('/health')
def health(): return {'ok':True,'running':bool(worker_thread and worker_thread.is_alive())}

@app.get('/start')
def start(authorization: str|None=Header(default=None)):
    global worker_thread
    auth(authorization)
    if worker_thread is None or not worker_thread.is_alive():
        stop_event.clear(); worker_thread=threading.Thread(target=worker_loop,daemon=True); worker_thread.start()
    return {'ok':True,'running':True,'maxStreams':8}

@app.get('/stop')
def stop(authorization: str|None=Header(default=None)):
    auth(authorization); stop_event.set(); return {'ok':True,'running':False}
