# -*- coding: utf-8 -*-
"""
Minimal, dependency-free Ethereum signer for ArcFlow.

Why this exists: the publisher has to sign and broadcast a real EIP-1559
transaction, and we did not want to add web3.py / eth-account as a dependency
for a single call. This module implements only what is needed:

    * keccak-256
    * secp256k1 ECDSA signing with RFC 6979 deterministic nonces
    * RLP encoding
    * EIP-1559 (type 0x02) transaction assembly and signing

Everything here is standard-library only.

The implementation is verified byte-for-byte against ethers.js v6 for the same
inputs (see scripts/verify-signer.py) — if the two disagree, this code is wrong.

This is intentionally minimal and auditable. It signs; it does not manage keys,
hold state, or talk to the network.
"""

import hashlib
import hmac

# ─────────────────────────────────────────────────────────────────────────────
# keccak-256
# ─────────────────────────────────────────────────────────────────────────────

_MASK64 = (1 << 64) - 1

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]

# Rotation offsets r[x][y] from the Keccak reference specification.
_ROT = [
    [0, 36, 3, 41, 18],    # x = 0
    [1, 44, 10, 45, 2],    # x = 1
    [62, 6, 43, 15, 61],   # x = 2
    [28, 55, 25, 21, 56],  # x = 3
    [27, 20, 39, 8, 14],   # x = 4
]


def _rol(x, n):
    n %= 64
    if n == 0:
        return x & _MASK64
    return ((x << n) | (x >> (64 - n))) & _MASK64


def _keccak_f1600(a):
    for rnd in range(24):
        # theta
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x][y] ^= d[x]

        # rho + pi:  B[y][(2x + 3y) mod 5] = ROT(A[x][y], r[x][y])
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], _ROT[x][y])

        # chi
        for x in range(5):
            for y in range(5):
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y] & _MASK64) & b[(x + 2) % 5][y])

        # iota
        a[0][0] ^= _RC[rnd]
    return a


def keccak256(data: bytes) -> bytes:
    """Keccak-256 (NOT SHA3-256 — different padding byte)."""
    rate = 136  # 1088 bits
    # pad: 0x01 ... 0x80  (keccak padding, not sha3's 0x06)
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate != 0:
        padded.append(0x00)
    padded[-1] ^= 0x80

    state = [[0] * 5 for _ in range(5)]
    for off in range(0, len(padded), rate):
        block = padded[off:off + rate]
        for i in range(rate // 8):
            lane = int.from_bytes(block[i * 8:i * 8 + 8], 'little')
            state[i % 5][i // 5] ^= lane
        state = _keccak_f1600(state)

    out = bytearray()
    for i in range(4):  # 32 bytes = 4 lanes
        out += state[i % 5][i // 5].to_bytes(8, 'little')
    return bytes(out[:32])


# ─────────────────────────────────────────────────────────────────────────────
# secp256k1
# ─────────────────────────────────────────────────────────────────────────────

_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def _inv(a, m):
    return pow(a, m - 2, m)


def _jacobian_double(pt):
    x, y, z = pt
    if y == 0:
        return (0, 0, 0)
    ysq = (y * y) % _P
    s = (4 * x * ysq) % _P
    m = (3 * x * x) % _P
    nx = (m * m - 2 * s) % _P
    ny = (m * (s - nx) - 8 * ysq * ysq) % _P
    nz = (2 * y * z) % _P
    return (nx, ny, nz)


def _jacobian_add(p1, p2):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    if z1 == 0:
        return p2
    if z2 == 0:
        return p1
    z1sq = (z1 * z1) % _P
    z2sq = (z2 * z2) % _P
    u1 = (x1 * z2sq) % _P
    u2 = (x2 * z1sq) % _P
    s1 = (y1 * z2sq * z2) % _P
    s2 = (y2 * z1sq * z1) % _P
    if u1 == u2:
        if s1 != s2:
            return (0, 0, 0)
        return _jacobian_double(p1)
    h = (u2 - u1) % _P
    r = (s2 - s1) % _P
    h2 = (h * h) % _P
    h3 = (h2 * h) % _P
    u1h2 = (u1 * h2) % _P
    nx = (r * r - h3 - 2 * u1h2) % _P
    ny = (r * (u1h2 - nx) - s1 * h3) % _P
    nz = (h * z1 * z2) % _P
    return (nx, ny, nz)


def _jacobian_mul(pt, k):
    result = (0, 0, 0)
    addend = pt
    while k:
        if k & 1:
            result = _jacobian_add(result, addend)
        addend = _jacobian_double(addend)
        k >>= 1
    return result


def _to_affine(pt):
    x, y, z = pt
    if z == 0:
        return None
    zinv = _inv(z, _P)
    zinv2 = (zinv * zinv) % _P
    return ((x * zinv2) % _P, (y * zinv2 * zinv) % _P)


def _pubkey_from_priv(priv: int):
    return _to_affine(_jacobian_mul((_GX, _GY, 1), priv))


def _rfc6979_k(priv: int, msg_hash: bytes) -> int:
    """Deterministic nonce per RFC 6979 (HMAC-SHA256), as Ethereum uses."""
    v = b'\x01' * 32
    k = b'\x00' * 32
    x = priv.to_bytes(32, 'big')
    h1 = msg_hash
    k = hmac.new(k, v + b'\x00' + x + h1, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b'\x01' + x + h1, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        cand = int.from_bytes(v, 'big')
        if 1 <= cand < _N:
            return cand
        k = hmac.new(k, v + b'\x00', hashlib.sha256).digest()
        v = hmac.new(k, v, hashlib.sha256).digest()


def sign_hash(msg_hash: bytes, priv: int):
    """Return (r, s, y_parity) for a 32-byte digest."""
    z = int.from_bytes(msg_hash, 'big')
    while True:
        k = _rfc6979_k(priv, msg_hash)
        pt = _to_affine(_jacobian_mul((_GX, _GY, 1), k))
        if pt is None:
            continue
        rx, ry = pt
        r = rx % _N
        if r == 0:
            continue
        s = (_inv(k, _N) * (z + r * priv)) % _N
        if s == 0:
            continue
        # EIP-2: enforce low-s
        if s > _N // 2:
            s = _N - s
            y_parity = 0 if ry % 2 == 1 else 1
        else:
            y_parity = 1 if ry % 2 == 1 else 0
        return r, s, y_parity


def private_key_to_address(priv: int) -> str:
    pub = _pubkey_from_priv(priv)
    pub_bytes = pub[0].to_bytes(32, 'big') + pub[1].to_bytes(32, 'big')
    return '0x' + keccak256(pub_bytes)[-20:].hex()


# ─────────────────────────────────────────────────────────────────────────────
# RLP + EIP-1559
# ─────────────────────────────────────────────────────────────────────────────


def rlp_encode(item) -> bytes:
    if isinstance(item, int):
        if item == 0:
            return b'\x80'
        return rlp_encode(item.to_bytes((item.bit_length() + 7) // 8, 'big'))
    if isinstance(item, (bytes, bytearray)):
        item = bytes(item)
        if len(item) == 1 and item[0] < 0x80:
            return item
        return _rlp_length(len(item), 0x80) + item
    if isinstance(item, (list, tuple)):
        payload = b''.join(rlp_encode(x) for x in item)
        return _rlp_length(len(payload), 0xC0) + payload
    raise TypeError('cannot rlp-encode %r' % (type(item),))


def _rlp_length(length: int, offset: int) -> bytes:
    if length < 56:
        return bytes([offset + length])
    enc = length.to_bytes((length.bit_length() + 7) // 8, 'big')
    return bytes([offset + 55 + len(enc)]) + enc


def encode_record_calldata(from_chain: int, to_chain: int, spread_bps: int) -> bytes:
    """Calldata for record(uint16,uint16,int16)."""
    selector = keccak256(b'record(uint16,uint16,int16)')[:4]
    return selector + _enc_u16(from_chain) + _enc_u16(to_chain) + _enc_i16(spread_bps)


def _enc_u16(v: int) -> bytes:
    return int(v).to_bytes(32, 'big')


def _enc_i16(v: int) -> bytes:
    return (int(v) % (1 << 256)).to_bytes(32, 'big')


def sign_eip1559_tx(priv: int, chain_id: int, nonce: int, to: str,
                    data: bytes, gas: int, max_fee_per_gas: int,
                    max_priority_fee_per_gas: int, value: int = 0) -> bytes:
    """Return the raw (signed) type-0x02 transaction bytes."""
    to_bytes = bytes.fromhex(to[2:] if to.startswith('0x') else to)

    unsigned = [
        chain_id,
        nonce,
        max_priority_fee_per_gas,
        max_fee_per_gas,
        gas,
        to_bytes,
        value,
        data,
        [],  # access list
    ]
    signing_hash = keccak256(b'\x02' + rlp_encode(unsigned))
    r, s, y_parity = sign_hash(signing_hash, priv)

    signed = unsigned + [y_parity, r, s]
    return b'\x02' + rlp_encode(signed)
