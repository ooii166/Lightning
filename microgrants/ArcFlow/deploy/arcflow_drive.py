# -*- coding: utf-8 -*-
"""CDP 驱动：打开 ArcFlow 部署页 → 连接 → 用 trailing-slash 技巧重新加入 Arc Testnet(5042002) →
自动点掉 MM 的「连接 / 添加网络」弹窗（仅配置类，不动私钥、不签交易）→ 截图回报状态。
真正的「部署合约」签名步骤留给用户手动确认，本脚本绝不触发。"""
import sys, os, json, time, urllib.request, urllib.parse
sys.path.insert(0, r'C:\Users\DELL\WorkBuddy\X推特')
from cdp_tool import Session, targets

CDP = 'http://127.0.0.1:9223'
DEPLOY_URL = 'http://127.0.0.1:8765/deploy.html'
SHOT = r'C:\Users\DELL\WorkBuddy\X推特\microgrants\ArcFlow\deploy\shot.png'

MM_EXT = 'ejbalbakoplchlghecdalmeeeajnimhm'


def evaluate(s, expr):
    r = s.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    res = r.get('result', {})
    if 'exceptionDetails' in res:
        return {'error': str(res.get('exceptionDetails', {}).get('exception', {}).get('description', res['exceptionDetails']))}
    return res.get('result', {}).get('value')


def open_deploy():
    q = urllib.parse.quote(DEPLOY_URL, safe='')
    req = urllib.request.Request(CDP + '/json/new?' + q, method='PUT')
    return json.load(urllib.request.urlopen(req))


def find_deploy_tab():
    for t in targets():
        if t.get('type') == 'page' and 'deploy.html' in (t.get('url') or ''):
            return t
    return None


def find_mm_popup():
    for t in targets():
        u = (t.get('url') or '')
        if t.get('type') == 'page' and ('notification.html' in u or 'popup.html' in u or MM_EXT in u) \
           and 'deploy.html' not in u:
            return t
    return None


CLICK_PRIMARY = """(() => {
  const btns = [...document.querySelectorAll('button, [role=button]')];
  const t = b => (b.innerText||b.textContent||'').trim().toLowerCase();
  const AVOID = ['cancel','reject','拒绝','取消','sign','签名','transaction','交易','not now','稍后','no thanks'];
  const PREF = ['approve','批准','connect','连接','add network','添加网络','add','添加','got it','知道了','next','下一步','switch','切换','allow','允许'];
  let found=null;
  for (const kw of PREF){
    const b = btns.find(x => t(x).includes(kw) && !AVOID.some(a=>t(x).includes(a)));
    if (b){ found=b; break; }
  }
  if(!found) return 'NO_POSITIVE_BTN';
  const label = t(found).slice(0,30);
  found.click();
  return 'CLICKED:'+label;
})()"""


def approve_mm(expected, rounds=10):
    clicked = []
    for i in range(rounds):
        pop = find_mm_popup()
        if not pop:
            time.sleep(0.6)
            continue
        try:
            s = Session(pop)
            s.call('Runtime.enable')
            res = evaluate(s, CLICK_PRIMARY)
            s.close()
            clicked.append(res)
            print('   [MM popup]', res)
        except Exception as e:
            print('   [MM err]', e)
        time.sleep(1.0)
    return clicked


def read_status(tab):
    s = Session(tab)
    s.call('Runtime.enable')
    expr = """(async()=>{ const g=id=>(document.getElementById(id)||{}).textContent||'';
      let info={chainId:null,accounts:[],deployDisabled:true,hasEth:!!window.ethereum,
        addNetDisabled:true,switchDisabled:true,deployResult:window.__DEPLOY_RESULT||null,
        log:((document.getElementById('log')||{}).innerText||'').slice(-700)};
      if(window.ethereum){ try{info.chainId=await window.ethereum.request({method:'eth_chainId'});}catch(e){}
        try{info.accounts=await window.ethereum.request({method:'eth_accounts'});}catch(e){} }
      const b=document.getElementById('btnDeploy'); info.deployDisabled=b?b.disabled:true;
      const a=document.getElementById('btnAddNet'); info.addNetDisabled=a?a.disabled:true;
      const w=document.getElementById('btnSwitch'); info.switchDisabled=w?w.disabled:true;
      return info; })()"""
    st = evaluate(s, expr)
    s.close()
    return st


def shot(tab):
    try:
        s = Session(tab)
        s.call('Page.enable'); s.call('Page.bringToFront')
        time.sleep(1)
        r = s.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
        open(SHOT, 'wb').write(__import__('base64').b64decode(r['result']['data']))
        s.close()
        print('   [shot] saved', SHOT)
    except Exception as e:
        print('   [shot err]', e)


def main():
    print('== open deploy tab ==')
    tab = open_deploy()
    time.sleep(3)
    for _ in range(20):
        tab = find_deploy_tab()
        if tab:
            st = read_status(tab)
            if st and 'hasEth' in st:
                break
        time.sleep(0.5)
    tab = find_deploy_tab()
    print('initial:', json.dumps(read_status(tab), ensure_ascii=False))

    print('== ① connect ==')
    s = Session(tab); s.call('Runtime.enable')
    evaluate(s, "document.getElementById('btnConnect').click(); 'ok'")
    s.close()
    time.sleep(2)
    approve_mm('connect')
    time.sleep(1.5)
    print('after connect:', json.dumps(read_status(tab), ensure_ascii=False))

    print('== ② addNet (trailing-slash trick) ==')
    s = Session(tab); s.call('Runtime.enable')
    evaluate(s, "document.getElementById('btnAddNet').click(); 'ok'")
    s.close()
    time.sleep(2)
    approve_mm('addnet')
    time.sleep(2)

    st = read_status(tab)
    # 若添加后未自动切链，尝试 ③ 切链（同样只是配置，安全）
    if st.get('chainId') != '0x4CEF52' and not st.get('switchDisabled'):
        print('== ③ switch to Arc Testnet ==')
        s = Session(tab); s.call('Runtime.enable')
        evaluate(s, "document.getElementById('btnSwitch').click(); 'ok'")
        s.close()
        time.sleep(2)
        approve_mm('switch')
        time.sleep(2)
        st = read_status(tab)

    print('FINAL:', json.dumps(read_status(tab), ensure_ascii=False))
    shot(tab)


if __name__ == '__main__':
    main()
