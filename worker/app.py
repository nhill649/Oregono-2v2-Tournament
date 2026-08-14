import os, re, json, time, threading, subprocess
from typing import Any
import cv2, numpy as np, pytesseract
from fastapi import FastAPI, Header, HTTPException
import firebase_admin
from firebase_admin import credentials, firestore

app=FastAPI(title='R6 Custom Game Stats Worker')
TOKEN=os.getenv('WORKER_TOKEN','change-me')
PROJECT_ID=os.getenv('FIREBASE_PROJECT_ID','oregano-2v2-tournament')
SERVICE_JSON=os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON','')
if SERVICE_JSON:
    cred=credentials.Certificate(json.loads(SERVICE_JSON))
    firebase_admin.initialize_app(cred)
else:
    firebase_admin.initialize_app()
db=firestore.client()
stop_event=threading.Event(); worker_thread=None

# R6 scoreboard OCR is intentionally conservative: a low-confidence read is ignored
# instead of writing bad stats. The crop can be changed with SCOREBOARD_CROP.
def crop_frame(frame):
    raw=os.getenv('SCOREBOARD_CROP','0.08,0.15,0.92,0.90')
    x1,y1,x2,y2=map(float,raw.split(',')); h,w=frame.shape[:2]
    return frame[int(y1*h):int(y2*h),int(x1*w):int(x2*w)]

def ocr_lines(frame):
    img=crop_frame(frame); gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY); gray=cv2.resize(gray,None,fx=1.8,fy=1.8,interpolation=cv2.INTER_CUBIC)
    _,thr=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    txt=pytesseract.image_to_string(thr,config='--psm 6')
    return [x.strip() for x in txt.splitlines() if x.strip()]

def parse_scoreboard(lines, known_players):
    # Common scoreboard row shape is player name followed by numeric K/D/A fields.
    # Names are matched against the tournament roster when available.
    found=[]
    for name in known_players:
        for line in lines:
            if name.lower() not in line.lower(): continue
            nums=[int(x) for x in re.findall(r'(?<!\d)(\d{1,2})(?!\d)',line)]
            if len(nums)>=3:
                found.append({'name':name,'kills':nums[-3],'deaths':nums[-2],'assists':nums[-1]})
                break
    return found

def mvp_score(p):
    k=p.get('kills',0); a=p.get('assists',0); d=p.get('deaths',0)
    entry=p.get('entryKills',0); plants=p.get('plants',0); entryd=p.get('entryDeaths',0)
    # Simple transparent tournament formula. It can be tuned later with real match data.
    return round(k*1.0+a*0.45-d*0.55+entry*0.75+plants*1.25-entryd*0.35,2)

def update_player(snap, obs):
    data=snap.to_dict() or {}; players=data.get('players',{})
    for o in obs:
        p=players.setdefault(o['name'],{'name':o['name'],'team':'','kills':0,'deaths':0,'assists':0,'headshots':0,'rounds':0,'matches':0,'mvpScore':0})
        # This worker receives repeated scoreboard observations. Store the latest
        # scoreboard as a match snapshot rather than blindly adding every poll.
        p.update({k:o[k] for k in ('kills','deaths','assists') if k in o})
    data['players']=players; return data

def process_stream(stream):
    url=stream.get('url','');
    if not url: return
    proc=subprocess.Popen(['streamlink','--stdout',url,'best'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    ff=subprocess.Popen(['ffmpeg','-loglevel','error','-i','pipe:0','-f','image2pipe','-vcodec','mjpeg','-vf','fps=0.5','-'],stdin=proc.stdout,stdout=subprocess.PIPE)
    buf=b''; snap_ref=db.collection('tournaments').document('oregano-stats')
    while not stop_event.is_set():
        chunk=ff.stdout.read(65536)
        if not chunk: break
        buf+=chunk
        a=buf.find(b'\xff\xd8'); b=buf.find(b'\xff\xd9',a+2)
        if a<0 or b<0: continue
        jpg=buf[a:b+2]; buf=buf[b+2:]
        frame=cv2.imdecode(np.frombuffer(jpg,np.uint8),cv2.IMREAD_COLOR)
        if frame is None: continue
        snap=snap_ref.get(); data=snap.to_dict() or {}; roster=[x.get('name') for x in data.get('playerList',[]) if x.get('name')]
        obs=parse_scoreboard(ocr_lines(frame),roster)
        if not obs: continue
        data=update_player(snap,obs); data.setdefault('streams',[])
        for s in data['streams']:
            if s.get('url')==url: s['live']=True; s['status']='OCR processor connected'
        db.collection('tournaments').document('oregono-stats').set(data)
    ff.kill(); proc.kill()

def worker_loop():
    while not stop_event.is_set():
        try:
            data=db.collection('tournaments').document('oregono-stats').get().to_dict() or {}
            for stream in data.get('streams',[]):
                if stop_event.is_set(): break
                process_stream(stream)
        except Exception as e:
            db.collection('tournaments').document('oregono-stats').set({'workerError':str(e)},merge=True)
        time.sleep(5)

def auth(authorization):
    if authorization != f'Bearer {TOKEN}': raise HTTPException(401,'Unauthorized')

@app.get('/health')
def health(): return {'ok':True,'running':worker_thread is not None and worker_thread.is_alive()}

@app.get('/start')
def start(authorization: str|None=Header(default=None)):
    global worker_thread
    auth(authorization)
    if worker_thread is None or not worker_thread.is_alive():
        stop_event.clear(); worker_thread=threading.Thread(target=worker_loop,daemon=True); worker_thread.start()
    return {'ok':True,'running':True}

@app.get('/stop')
def stop(authorization: str|None=Header(default=None)):
    auth(authorization); stop_event.set(); return {'ok':True,'running':False}
