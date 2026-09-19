# -*- coding: utf-8 -*-
"""聚焦脚本：确保连钱包(轮询等用户 Approve 连接) → 触发部署(用户签真实交易) → 读回结果。
假设钱包已在 Arc 主网(5042)；若不在主网会提示先切链。"""
import sys, json, time, urllib.request, urllib.parse
sys.path.insert(0, r'C:\Users\DELL\WorkBuddy\X推特')
from cdp_tool import Session, targets

CDP = 'http://127.0.0.1:9223'
MAINNET = '0x13b2'

def evaluate(s, expr):
    r = s.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
    res = r.get('result', {})
    if 'exceptionDetails' in res:
        return {'error': str(res.get('exceptionDetails'))}
    return res.get('result', {}).get('value')

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
      log:((document.getElementById('log')||{}).innerText||'').slice(-700)};
      if(window.ethereum){try{o.chainId=await window.ethereum.request({method:'eth_chainId'});}catch(e){}
        try{o.accounts=await window.ethereum.request({method:'eth_accounts'});}catch(e){}}
      const b=document.getElementById('btnDeploy');o.deployDisabled=b?b.disabled:true; return o;})()""")
    s.close()
    return st

def open_deploy():
    try:
        req = urllib.request.Request(CDP + '/json/new?' + urllib.parse.quote('http://127.0.0.1:8765/deploy.html', safe=''), method='PUT')
        return json.load(urllib.request.urlopen(req))
    except Exception as e:
        print('open_deploy err:', e); return None

def main():
    tab = find_deploy_tab()
    if not tab:
        print('未找到 deploy 标签，自动重开…')
        open_deploy(); time.sleep(4)
        tab = find_deploy_tab()
    print('tab:', tab['id'] if tab else None)
    st = status(tab); print('status:', json.dumps(st, ensure_ascii=False))
    if not st:
        print('找不到 deploy 标签页，请先在 Edge 打开 http://127.0.0.1:8765/deploy.html'); return

    if st.get('chainId') != MAINNET:
        print('!! 当前不是主网(%s)，请先在 MetaMask 切到 Arc Mainnet(5042)' % st.get('chainId')); return

    # 确保连钱包
    for i in range(5):
        st = status(tab)
        if st and st.get('accounts'):
            print('已连接:', st.get('accounts')); break
        print('[%d] 点连接（MetaMask 弹「连接」请点确认）' % (i+1))
        click_btn(tab, 'btnConnect'); time.sleep(14)
        tab = find_deploy_tab()
    st = status(tab)
    print('after connect:', json.dumps(st, ensure_ascii=False))
    if not (st and st.get('accounts')):
        print('!! 仍未连接——请在 MetaMask 批准「连接」本站点，然后重跑本脚本'); return
    if st.get('deployDisabled'):
        print('!! 部署按钮仍禁用，可能余额不足或链不对；log:', st.get('log')); return

    # 触发部署
    print('== 触发部署（MetaMask 弹真实交易，请签名）==')
    click_btn(tab, 'btnDeploy')
    print('>>> 已提交 MetaMask，请亲手签名（真实 ~0.016 USDC）。轮询结果…')
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
