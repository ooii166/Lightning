# -*- coding: utf-8 -*-
import json, sys, websocket, urllib.request

CDP = 'http://127.0.0.1:9223'
DEPLOY_URL = 'http://127.0.0.1:8899/deploy/deploy.html'


def ws_connect(url):
    return websocket.create_connection(url, header=['Origin: ' + CDP], timeout=40, max_size=200 * 1024 * 1024)


def call(s, method, params=None):
    s.send(json.dumps({'id': 1, 'method': method, 'params': params or {}}))
    while True:
        msg = json.loads(s.recv())
        if msg.get('id') == 1:
            return msg


def enable_and_drain(s):
    s.send(json.dumps({'id': 1, 'method': 'Runtime.enable'}))
    while True:
        msg = json.loads(s.recv())
        if msg.get('id') == 1:
            break


def check_ethereum(ws_url):
    s = ws_connect(ws_url)
    enable_and_drain(s)
    r = call(s, 'Runtime.evaluate', {'expression':
        'JSON.stringify({eth: !!window.ethereum, mm: !!(window.ethereum && window.ethereum.isMetaMask), '
        'chain: window.ethereum ? window.ethereum.chainId : null})', 'returnByValue': True})
    s.close()
    return r.get('result', {}).get('result', {}).get('value')


def main():
    ts = json.load(urllib.request.urlopen(CDP + '/json'))
    pages = [t for t in ts if t.get('type') == 'page']
    print('=== existing page tabs: MetaMask probe ===')
    for t in pages[:8]:
        try:
            print(t.get('url', '')[:70], '->', check_ethereum(t['webSocketDebuggerUrl']))
        except Exception as e:
            print(t.get('url', '')[:70], '-> ERR', e)

    # Try browser-level Target.createTarget with url directly
    print('\n=== Target.createTarget with url ===')
    ver = json.load(urllib.request.urlopen(CDP + '/json/version'))
    bw = ws_connect(ver['webSocketDebuggerUrl'])
    r = call(bw, 'Target.createTarget', {'url': DEPLOY_URL, 'newWindow': False})
    tid = r.get('result', {}).get('targetId')
    print('created targetId:', tid)
    time.sleep(2)
    # find the new target's ws
    ts2 = json.load(urllib.request.urlopen(CDP + '/json'))
    nt = [t for t in ts2 if t.get('id') == tid or t.get('targetId') == tid]
    if nt:
        print('new tab ethereum:', check_ethereum(nt[0]['webSocketDebuggerUrl']))
    bw.close()


import time
main()
