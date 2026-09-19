# -*- coding: utf-8 -*-
"""单次 CDP 会话完成 连钱包 + 部署：在页面内 await connect() 再 await deploy()，
中间不重查标签（规避「标签在两个工具调用间消失」的老问题）。
MetaMask 的签名弹窗由用户亲手点；脚本 await 到部署回执返回。
真实花费 ~0.016 USDC，其余余额不动。"""
import sys, json, time, urllib.request, urllib.parse
sys.path.insert(0, r'C:\Users\DELL\WorkBuddy\X推特')
from cdp_tool import Session

CDP = 'http://127.0.0.1:9223'
DEPLOY_URL = 'http://127.0.0.1:8765/deploy.html'
MAINNET = '0x13b2'

def open_deploy():
    req = urllib.request.Request(CDP + '/json/new?' + urllib.parse.quote(DEPLOY_URL, safe=''), method='PUT')
    return json.load(urllib.request.urlopen(req))

def main():
    info = open_deploy()
    tab_id = info.get('id')
    print('opened tab:', tab_id)
    time.sleep(5)

    s = Session(info)
    s.ws.settimeout(200)   # 等用户签名/链上回执，socket 默认 30s 太短
    s.call('Runtime.enable')
    # 单次 evaluate：连钱包 → 部署，await 到回执；返回部署结果或错误
    expr = r"""
    (async () => {
      try {
        if (!window.ethereum) return {error:'no ethereum'};
        const cid = await window.ethereum.request({method:'eth_chainId'});
        if (cid !== '0x13b2') return {error:'not mainnet: '+cid};
        await connect();
        if (!signer) return {error:'connect failed (no signer)'};
        // 等余额刷新（connect 内 refreshBal 异步）
        await new Promise(r => setTimeout(r, 1500));
        await deploy();
        return window.__DEPLOY_RESULT || window.__DEPLOY_ERROR || {pending:true, log:(document.getElementById('log')||{}).innerText};
      } catch (e) {
        return {error: (e && e.message) ? e.message : String(e), log:(document.getElementById('log')||{}).innerText};
      }
    })()
    """
    print('>>> 调用 connect + deploy（await 签名）…')
    r = s.call('Runtime.evaluate', {
        'expression': expr,
        'returnByValue': True,
        'awaitPromise': True,
        'timeout': 170000,
    })
    s.close()
    res = r.get('result', {})
    if 'exceptionDetails' in res:
        print('EXCEPTION:', res.get('exceptionDetails'))
        return
    val = res.get('result', {}).get('value')
    print('RESULT:', json.dumps(val, ensure_ascii=False))

if __name__ == '__main__':
    main()
