# -*- coding: utf-8 -*-
"""Minimal CDP controller for the ArcFlow deploy page on the controlled Edge (9223).
Subcommands:
  open    create a new tab at the local deploy page, wait for load, print status
  status  print current page status (artifact/ethereum/chain/accounts/balance/deploy state)
  click   click the Deploy button (MetaMask connect + confirm still require the human)
  address read window.ARCFLOW_DEPLOYED if the tx already confirmed
  shot    screenshot to deploy/shot.png
Target id is persisted in deploy/.cdp_target.json.
"""
import sys, json, time, base64, urllib.request, urllib.parse
import websocket

CDP = 'http://127.0.0.1:9223'
DEPLOY_URL = 'http://127.0.0.1:8899/deploy/deploy.html'
STATE = 'C:/Users/DELL/WorkBuddy/X推特/microgrants/ArcFlow/deploy/.cdp_target.json'


def targets():
    return json.load(urllib.request.urlopen(CDP + '/json'))


def save_target(t):
    json.dump({'targetId': t['id'], 'ws': t['webSocketDebuggerUrl'], 'url': t.get('url')},
              open(STATE, 'w'))


def load_target():
    return json.load(open(STATE))


def new_tab():
    req = urllib.request.Request(CDP + '/json/new', method='PUT',
                                 data=b'', headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))


class Session:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, header=['Origin: ' + CDP],
                                              timeout=40, max_size=200 * 1024 * 1024)
        self.i = 0

    def call(self, method, params=None):
        self.i += 1
        self.ws.send(json.dumps({'id': self.i, 'method': method, 'params': params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get('id') == self.i:
                return msg

    def eval(self, expr):
        r = self.call('Runtime.evaluate',
                      {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        res = r.get('result', {})
        if 'exceptionDetails' in res:
            return {'__error__': str(res['exceptionDetails'].get('exception', {}).get('description', res['exceptionDetails']))}
        return res.get('result', {}).get('value')

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


STATUS_EXPR = """
(async () => {
  const g = (id) => (document.getElementById(id) || {}).textContent || '';
  let info = { artifactLoaded: !!window.ARCFLOW, hasEthereum: !!window.ethereum,
               chainId: null, accounts: [], deployDisabled: true,
               deployed: window.ARCFLOW_DEPLOYED || null,
               bal: g('bal'), wallet: g('wallet'), net: g('net'), size: g('size'),
               log: (document.getElementById('log')||{}).innerText || '' };
  if (window.ethereum) {
    try { info.chainId = await window.ethereum.request({method:'eth_chainId'}); } catch(e){}
    try { info.accounts = await window.ethereum.request({method:'eth_accounts'}); } catch(e){}
  }
  const btn = document.getElementById('btnDeploy');
  info.deployDisabled = btn ? btn.disabled : true;
  return info;
})()
"""


def cmd_open():
    t = new_tab()
    save_target(t)
    s = Session(t['webSocketDebuggerUrl'])
    s.call('Page.enable'); s.call('Runtime.enable')
    s.call('Page.navigate', {'url': DEPLOY_URL})
    # wait for load
    for _ in range(20):
        rs = s.eval('document.readyState')
        if rs == 'complete':
            break
        time.sleep(0.5)
    time.sleep(1.5)
    print(json.dumps(s.eval(STATUS_EXPR), ensure_ascii=False, indent=2))
    s.close()


def cmd_status():
    t = load_target()
    s = Session(t['ws'])
    s.call('Page.enable'); s.call('Runtime.enable')
    print(json.dumps(s.eval(STATUS_EXPR), ensure_ascii=False, indent=2))
    s.close()


def cmd_click():
    t = load_target()
    s = Session(t['ws'])
    s.call('Runtime.enable')
    r = s.eval("document.getElementById('btnDeploy').click(); 'clicked'")
    print(r)
    s.close()


def cmd_address():
    t = load_target()
    s = Session(t['ws'])
    s.call('Runtime.enable')
    print(s.eval("window.ARCFLOW_DEPLOYED || null"))
    s.close()


def cmd_shot():
    t = load_target()
    s = Session(t['ws'])
    s.call('Page.enable'); s.call('Page.bringToFront')
    time.sleep(1)
    r = s.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
    out = 'C:/Users/DELL/WorkBuddy/X推特/microgrants/ArcFlow/deploy/shot.png'
    open(out, 'wb').write(base64.b64decode(r['result']['data']))
    print('saved', out)
    s.close()


def cmd_close():
    # close the saved deploy tab (cleanup)
    t = load_target()
    req = urllib.request.Request(CDP + '/json/close/' + t['targetId'], method='PUT',
                                 data=b'', headers={'Content-Type': 'application/json'})
    try:
        print(urllib.request.urlopen(req).read().decode())
    except Exception as e:
        print('close err', e)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'open'
    {'open': cmd_open, 'status': cmd_status, 'click': cmd_click,
     'address': cmd_address, 'shot': cmd_shot, 'close': cmd_close}[cmd]()
