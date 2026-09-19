# -*- coding: utf-8 -*-
"""ArcFlow 主网部署完整编排（单一脚本）：
连钱包 → 加 Arc 主网 → 切主网(不再重载页面) → 触发部署。
MM 的「连接/添加网络/切换网络」弹窗需用户手动 Approve（配置类，不动钱）；
最后的部署交易(~0.016 USDC)由用户亲手签名。脚本推到「等签名」并读回结果。
"""
import sys, json, time, urllib.request, urllib.parse
sys.path.insert(0, r'C:\Users\DELL\WorkBuddy\X推特')
from cdp_tool import Session, targets

CDP = 'http://127.0.0.1:9223'
DEPLOY_URL = 'http://127.0.0.1:8765/deploy.html'
MAINNET = '0x13b2'

def evaluate(s, expr):
    r = s.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    res = r.get('result', {})
    if 'exceptionDetails' in res:
        return {'error': str(res.get('exceptionDetails'))}
    return res.get('result', {}).get('value')

def http_put(path):
    try:
        return urllib.request.urlopen(urllib.request.Request(CDP + path, method='PUT'), timeout=5).read()
    except Exception:
        return None

def open_deploy():
    req = urllib.request.Request(CDP + '/json/new?' + urllib.parse.quote(DEPLOY_URL, safe=''), method='PUT')
    return json.load(urllib.request.urlopen(req))

def close_deploy_tabs():
    n = 0
    for t in targets():
        if t.get('type') == 'page' and 'deploy.html' in (t.get('url') or ''):
            http_put('/json/close/' + t['id']); n += 1
    return n

def find_deploy_tab():
    for t in targets():
        if t.get('type') == 'page' and 'deploy.html' in (t.get('url') or ''):
            return t
    return None

def click_btn(tab, btn_id):
    if not tab:
        return
    s = Session(tab); s.call('Runtime.enable')
    evaluate(s, "document.getElementById('%s').click(); 'ok'" % btn_id)
    s.close()

def status(tab):
    if not tab:
        return None
    s = Session(tab); s.call('Runtime.enable')
    st = evaluate(s, """(async()=>{let o={chainId:null,accounts:[],deployDisabled:true,deployResult:window.__DEPLOY_RESULT||null,
      log:((document.getElementById('log')||{}).innerText||'').slice(-700),
      d2cls:((document.getElementById('d2')||{}).className||'')};
      if(window.ethereum){try{o.chainId=await window.ethereum.request({method:'eth_chainId'});}catch(e){}
        try{o.accounts=await window.ethereum.request({method:'eth_accounts'});}catch(e){}}
      const b=document.getElementById('btnDeploy');o.deployDisabled=b?b.disabled:true; return o;})()""")
    s.close()
    return st

def wait_chain(target, timeout=45):
    t0 = time.time()
    while time.time() - t0 < timeout:
        tab = find_deploy_tab()
        if tab:
            st = status(tab)
            if st and st.get('chainId') == target:
                return tab, st
        time.sleep(2)
    return None, None

def wait_accounts(tab, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = status(tab)
        if st and st.get('accounts'):
            return st
        time.sleep(2)
    return None

def main():
    print('== 关旧标签 + 开新 deploy 页 ==')
    print('closed:', close_deploy_tabs()); time.sleep(1)
    open_deploy(); time.sleep(4)
    tab = find_deploy_tab()
    print('tab:', tab['id'] if tab else None)

    # ① 连接（轮询等用户 Approve 连接）
    print('== ① 连接钱包（MM 弹「连接」请点确认）==')
    for i in range(4):
        st = wait_accounts(tab, 15)
        if st and st.get('accounts'):
            print('已连接:', st.get('accounts')); break
        print('  重点连接 %d' % (i+1)); click_btn(tab, 'btnConnect'); time.sleep(2)
    st = status(tab)
    if not (st and st.get('accounts')):
        print('!! 未连接——请先在 MetaMask 批准「连接」本站点，再重跑'); return
    print('after connect:', json.dumps(st, ensure_ascii=False))

    # ②+③ 确保在主网
    for attempt in range(3):
        st = status(tab)
        if st.get('chainId') == MAINNET:
            print('已在主网'); break
        print('--- 加主网 + 切主网 (attempt %d) ---' % (attempt+1))
        click_btn(tab, 'btnAddNet'); print('  点②添加主网（MM 请 Approve）'); time.sleep(15)
        st = status(tab)
        added = ('网络添加成功' in (st or {}).get('log','')) or ((st or {}).get('d2cls','').endswith('ok'))
        print('  add -> added=%s' % added)
        click_btn(tab, 'btnSwitch'); print('  点③切主网（MM 请 Approve）')
        tab2, st2 = wait_chain(MAINNET, 40)
        if st2:
            tab = tab2; print('切到主网:', json.dumps(st2, ensure_ascii=False)); break
        tab = find_deploy_tab(); print('  仍未主网，重试')

    st = status(tab)
    print('READY:', json.dumps(st, ensure_ascii=False))
    if st.get('chainId') != MAINNET:
        print('!! 仍非主网，请手动在 MM 选 Arc Mainnet(5042) 后重跑'); return
    if st.get('deployDisabled'):
        print('!! 部署按钮禁用，可能余额不足；log:', st.get('log')); return

    # ④ 部署（用户签名）
    print('== ④ 触发部署（MM 弹真实交易，请签名）==')
    click_btn(tab, 'btnDeploy')
    print('>>> 已提交 MetaMask，请亲手签名（真实 ~0.016 USDC，剩余 USDC 不动）。轮询结果…')
    t0 = time.time()
    while time.time() - t0 < 110:
        r = status(find_deploy_tab())
        if r and r.get('deployResult'):
            print('DEPLOY_RESULT:', json.dumps(r['deployResult'], ensure_ascii=False))
            return
        time.sleep(3)
    print('部署交易已发起但未在窗口内确认；请检查 MetaMask 是否签名、页面是否出结果。')

if __name__ == '__main__':
    main()
