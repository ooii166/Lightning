# -*- coding: utf-8 -*-
"""仅部署（假设钱包已在 Arc 主网 5042，且站点已授权连接）：
连钱包(若需) → 触发部署 → 读回结果。只让用户在最后签名一次。
页面若未在主网会直接提示，不触发任何添加/切换网络。"""
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

def open_deploy():
    req = urllib.request.Request(CDP + '/json/new?' + urllib.parse.quote(DEPLOY_URL, safe=''), method='PUT')
    return json.load(urllib.request.urlopen(req))

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

def main():
    open_deploy(); time.sleep(4)
    tab = find_deploy_tab()
    if not tab:
        print('无法打开 deploy 标签（本地 8765 服务是否在跑？）'); return
    print('tab:', tab['id'])

    st = status(tab)
    print('status(pre-connect):', json.dumps(st, ensure_ascii=False))
    if not st:
        print('读不到状态'); return
    if st.get('chainId') != MAINNET:
        print('!! 当前不是主网(%s)。请先在 MetaMask 选 Arc Mainnet(5042)，再重跑。' % st.get('chainId')); return

    # 无论 eth_accounts 是否返回，都点一次连接按钮：初始化页面的 provider/signer 并触发余额刷新
    print('== 初始化连接（已授权不会弹窗）==')
    click_btn(tab, 'btnConnect'); time.sleep(14)
    tab = find_deploy_tab()
    st = status(tab)
    print('status(after-connect):', json.dumps(st, ensure_ascii=False))
    if not (st and st.get('accounts')):
        print('!! 未连接或余额未刷新，log:', st.get('log')); return

    if st.get('deployDisabled'):
        print('!! 部署按钮禁用（余额可能不足或链不对）；log:', st.get('log')); return

    print('== 触发部署（MM 弹真实交易，请签名）==')
    click_btn(tab, 'btnDeploy')
    print('>>> 已提交 MetaMask，请亲手签名（真实 ~0.016 USDC）。轮询结果…')
    t0 = time.time()
    while time.time() - t0 < 150:
        r = status(find_deploy_tab())
        if r and r.get('deployResult'):
            print('DEPLOY_RESULT:', json.dumps(r['deployResult'], ensure_ascii=False))
            return
        time.sleep(3)
    print('部署交易已发起但未在窗口内确认；请检查 MetaMask 是否签名、页面是否出结果。')

if __name__ == '__main__':
    main()
