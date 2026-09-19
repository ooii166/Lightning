# -*- coding: utf-8 -*-
"""
Self-check for arcflow_signer.py.

The signer is hand-written to avoid pulling in web3.py / eth-account, so it needs
proof that it produces exactly the right bytes. Every vector below was generated
with ethers.js v6 and is asserted byte-for-byte.

Run:  python agent/verify_signer.py
Exits non-zero on any mismatch, so CI fails loudly if the signer ever regresses.

Standard library only.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arcflow_signer import (  # noqa: E402
    encode_record_calldata,
    keccak256,
    private_key_to_address,
    sign_eip1559_tx,
)

CONTRACT = '0xf004c40f0b8204c21991309A808dA2ee4895B9Eb'
PRIV = int('11' * 32, 16)
PRIV_ADDR = '0x19e7e376e7c213b7e7e7e46cc70a5dd086daff2a'

failures = []


def check(label, got, expected):
    ok = got == expected
    print('  %s %s' % ('PASS' if ok else 'FAIL', label))
    if not ok:
        failures.append(label)
        print('       got      %s' % got)
        print('       expected %s' % expected)


print('keccak-256 known vectors')
check('keccak("")', keccak256(b'').hex(),
      'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470')
check('keccak("abc")', keccak256(b'abc').hex(),
      '4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45')
check('keccak(fox)', keccak256(b'The quick brown fox jumps over the lazy dog').hex(),
      '4d741b6f1eb29cb2a9b9911c82f56fa8d73b04959d3d9d222895df6c0b28aa15')

print()
print('function selector')
check('record(uint16,uint16,int16)', keccak256(b'record(uint16,uint16,int16)')[:4].hex(),
      'a3934429')
check('latestPair(uint16,uint16)', keccak256(b'latestPair(uint16,uint16)')[:4].hex(),
      '25f18eb6')

print()
print('address derivation (secp256k1)')
check('address(0x11..11)', private_key_to_address(PRIV), PRIV_ADDR)

print()
print('calldata encoding')
check('record(5042,1,-7)',
      encode_record_calldata(5042, 1, -7).hex(),
      'a3934429'
      '00000000000000000000000000000000000000000000000000000000000013b2'
      '0000000000000000000000000000000000000000000000000000000000000001'
      'fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff9')

print()
print('EIP-1559 signing — byte-for-byte against ethers.js v6')
# case 1: chain 5042, nonce 1, record(5042, 1, -7), gas 120000,
#         maxFee 30 Gwei, priority 2 Gwei
check('signed tx (nonce 1)',
      '0x' + sign_eip1559_tx(
          PRIV, 5042, 1, CONTRACT,
          encode_record_calldata(5042, 1, -7),
          120000, 30000000000, 2000000000).hex(),
      '0x02f8d38213b20184773594008506fc23ac008301d4c094f004c40f0b8204c21991309a808da2ee4895b9eb'
      '80b864a393442900000000000000000000000000000000000000000000000000000000000013b2'
      '0000000000000000000000000000000000000000000000000000000000000001'
      'fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff9'
      'c080a04854bb5395d8be4464c0fe9e11a6affdb5d585b477907856629749736f794a29'
      'a04759167252c8804275f6cded41d9cc0764a156247e663d26bfcae882c911c318')

# case 2: chain 5042, nonce 9, record(5042, 137, 42), gas 95000,
#         maxFee 20.48 Gwei, priority 1 Gwei
check('signed tx (nonce 9)',
      '0x' + sign_eip1559_tx(
          PRIV, 5042, 9, CONTRACT,
          encode_record_calldata(5042, 137, 42),
          95000, 20480000000, 1000000000).hex(),
      '0x02f8d38213b209843b9aca008504c4b400008301731894f004c40f0b8204c21991309a808da2ee4895b9eb'
      '80b864a393442900000000000000000000000000000000000000000000000000000000000013b2'
      '0000000000000000000000000000000000000000000000000000000000000089'
      '000000000000000000000000000000000000000000000000000000000000002a'
      'c080a062806be3715b982d333ff7ad8dd5177d52dcf0165625863133b8e99f6eca97ea'
      'a07abbb5a9e196f7d7d6b302f035ebd2c99c543dabf51123f8c84a0042c464c4b9')

print()
if failures:
    print('FAILED: %d check(s) — %s' % (len(failures), ', '.join(failures)))
    sys.exit(1)
print('All signer checks passed.')
