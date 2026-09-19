# -*- coding: utf-8 -*-
"""主网部署编排 v2：
连钱包 → 加 Arc 主网(读日志确认) → 切主网(轮询等链切换+刷新后重连) → 触发部署。
MM 的「添加网络/切换网络」弹窗需用户手动 Approve（配置类，不动钱）；
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
      s2:((document.getElementById('s2')||{}).innerText||''),
      d2cls:((document.getElementById('d2')||{}).className||'')};
      if(window.ethereum){try{o.chainId=await window.ethereum.request({method:'eth_chainId'});}catch(e){}
        try{o.accounts=await window.ethereum.request({method:'eth_accounts'});}catch(e){}}
      const b=document.getElementById('btnDeploy');o.deployDisabled=b?b.disabled:true; return o;})()""")
    s.close()
    return st

def wait_chain(target, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        tab = find_deploy_tab()
        if tab:
            st = status(tab)
            if st and st.get('chainId') == target:
                return tab, st
        time.sleep(2)
    return None, None

def main():
    print('== 关闭旧 deploy 标签 ==')
    print('closed:', close_deploy_tabs()); time.sleep(1)
    print('== 开新 deploy 标签 ==')
    open_deploy(); time.sleep(3)
    tab = find_deploy_tab()
    print('tab:', tab['id'] if tab else None)
    print('initial:', json.dumps(status(tab), ensure_ascii=False))

    print('== ① 连接钱包 ==')
    click_btn(tab, 'btnConnect'); time.sleep(6)
    print('after connect:', json.dumps(status(tab), ensure_ascii=False))

    # ② 添加主网
    print('== ② 添加 Arc 主网（MM 弹窗请点 Approve）==')
    click_btn(tab, 'btnAddNet'); time.sleep(18)
    st = status(tab)
    logtxt = (st or {}).get('log', '')
    added = ('网络添加成功' in logtxt) or '已添加' in logtxt or ((st or {}).get('d2cls','').endswith('ok'))
    print('add result -> added=%s | d2=%s' % (added, (st or {}).get('d2cls')))
    print('log tail:', logtxt[-300:])

    # ③ 切主网（若已添加则切，否则重试添加）
    for i in range(2):
        st = status(tab)
        if (st or {}).get('chainId') == MAINNET:
            print('已在主网'); break
        if not added:
            print('  重新点 ② 添加主网（MM 请 Approve）'); click_btn(tab, 'btnAddNet'); time.sleep(15)
            st = status(tab); logtxt=(st or {}).get('log','')
            added = ('网络添加成功' in logtxt) or ((st or {}).get('d2cls','').endswith('ok'))
            print('  re-add -> added=%s' % added)
        print('  点 ③ 切到主网（MM 弹窗请点 Approve）'); click_btn(tab, 'btnSwitch')
        tab2, st2 = wait_chain(MAINNET, 35)
        if st2:
            tab = tab2; print('切链成功(含刷新):', json.dumps(st2, ensure_ascii=False)); break
        tab = find_deploy_tab(); print('  仍未主网，重试')

    # 链切换后页面会刷新，需重连
    st = status(tab)
    if (st or {}).get('chainId') == MAINNET and not (st or {}).get('accounts'):
        print('== 链切换后页面已刷新，重连钱包 ==')
        click_btn(tab, 'btnConnect'); time.sleep(6)
        st = status(tab); print('after reconnect:', json.dumps(st, ensure_ascii=False))

    st = status(tab)
    print('READY:', json.dumps(st, ensure_ascii=False))
    if (st or {}).get('chainId') == MAINNET and (st or {}).get('accounts') and not (st or {}).get('deployDisabled'):
        print('== ⑤ 触发部署（MM 将弹出真实交易确认）==')
        click_btn(tab, 'btnDeploy')
        print('>>> 部署交易已提交 MetaMask，请亲手签名（真实 ~0.016 USDC）。轮询结果中…')
        t0 = time.time()
        while time.time() - t0 < 110:
            tab = find_deploy_tab()
            r = status(tab)
            if r and r.get('deployResult'):
                print('DEPLOY_RESULT:', json.dumps(r['deployResult'], ensure_ascii=False))
                return
            time.sleep(3)
        print('部署交易已发起但未在窗口内确认；请检查 MetaMask 是否签名、页面是否出结果。')
    else:
        print('未就绪：chainId=%s accounts=%s deployDisabled=%s' % ((st or {}).get('chainId'), bool((st or {}).get('accounts')), (st or {}).get('deployDisabled')))

if __name__ == '__main__':
    main()
