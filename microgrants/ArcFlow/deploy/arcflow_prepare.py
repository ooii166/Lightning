# -*- coding: utf-8 -*-
import sys, json, time, urllib.request
sys.path.insert(0, r'C:\Users\DELL\WorkBuddy\X推特')
from cdp_tool import Session, targets

MM = 'ejbalbakoplchlghecdalmeeeajnimhm'
DEPLOY = 'http://127.0.0.1:8765/deploy.html'
SHOT = r'C:\Users\DELL\WorkBuddy\X推特\microgrants\ArcFlow\deploy\shot.png'

def evaluate(s, expr):
    r = s.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    res = r.get('result', {})
    if 'exceptionDetails' in res:
        return {'error': str(res.get('exceptionDetails'))}
    return res.get('result', {}).get('value')

def deploy_tabs():
    return [t for t in targets() if t.get('type')=='page' and 'deploy.html' in t.get('url','')]

def mm_targets():
    return [t for t in targets() if MM in (t.get('url') or '')]

def click_approve(tab):
    s = Session(tab); s.call('Runtime.enable')
    r = evaluate(s, """(()=>{const A=['cancel','reject','拒绝','取消','sign','签名','transaction','交易','稍后'];
      const P=['approve','批准','connect','连接','next','下一步','switch','切换','allow','允许','确认','got it','知道了'];
      const els=[...document.querySelectorAll('button,[role=button],a')];
      const t=e=>(e.innerText||e.textContent||'').trim().toLowerCase();
      for(const k of P){const b=els.find(e=>t(e).includes(k)&&!A.some(a=>t(e).includes(a)));
        if(b){const l=(b.innerText||b.textContent||'').trim().slice(0,24);b.click();return 'CLICKED:'+l;}}
      return 'NONE';})()""")
    s.close(); return r

def approve_mm(rounds=12):
    for i in range(rounds):
        pops = mm_targets()
        clicked = False
        for t in pops:
            try:
                r = click_approve(t)
                if isinstance(r,str) and r.startswith('CLICKED'):
                    print('   [MM]', r); clicked=True
            except Exception: pass
        if clicked:
            time.sleep(1.2)
        else:
            time.sleep(0.7)

def status(tab):
    s = Session(tab); s.call('Runtime.enable')
    st = evaluate(s, """(async()=>{const g=id=>(document.getElementById(id)||{}).textContent||'';
      let o={chainId:null,accounts:[],deployDisabled:true,addNetDisabled:true,switchDisabled:true,
        hasEth:!!window.ethereum,log:((document.getElementById('log')||{}).innerText||'').slice(-500)};
      if(window.ethereum){try{o.chainId=await window.ethereum.request({method:'eth_chainId'});}catch(e){}
        try{o.accounts=await window.ethereum.request({method:'eth_accounts'});}catch(e){}}
      const b=document.getElementById('btnDeploy');o.deployDisabled=b?b.disabled:true;
      const a=document.getElementById('btnAddNet');o.addNetDisabled=a?a.disabled:true;
      const w=document.getElementById('btnSwitch');o.switchDisabled=w?w.disabled:true;
      const bal=document.getElementById('bal');o.bal=bal?bal.textContent:null;
      return o;})()""")
    s.close(); return st

# pick a deploy tab (prefer one already on 5042002)
tabs = deploy_tabs()
print('deploy tabs:', len(tabs))
tab = tabs[0]
s = Session(tab); s.call('Runtime.enable')
evaluate(s, "document.getElementById('btnConnect').click(); 'ok'")
s.close()
time.sleep(2)
approve_mm()
time.sleep(1.5)
st = status(tab)
print('STATUS:', json.dumps(st, ensure_ascii=False))

# faucet if needed
if st.get('chainId')=='0x4cef52':
    s = Session(tab); s.call('Runtime.enable')
    evaluate(s, "document.getElementById('btnFaucet').click(); 'ok'")
    s.close()
    print('   faucet page opened in new tab')
    time.sleep(2)
    # screenshot
    try:
        s=Session(tab); s.call('Page.enable'); s.call('Page.bringToFront'); time.sleep(1)
        r=s.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        open(SHOT,'wb').write(__import__('base64').b64decode(r['result']['data'])); s.close()
        print('   shot saved', SHOT)
    except Exception as e:
        print('   shot err', e)
    print('\nREADY FOR DEPLOY — user must click ⑤ and approve in MetaMask.')
else:
    print('chainId not 5042002, cannot proceed to faucet')
