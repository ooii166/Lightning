# -*- coding: utf-8 -*-
"""
Offline regression tests for the ArcFlow publisher's write path.

Run:  python agent/test_publisher.py

Two failure modes are covered that a live run cannot be relied on to reproduce
on demand:

  * an earlier run left a transaction in the mempool holding a nonce, so the
    node rejects the next write with "replacement transaction underpriced".
    The retry has to raise the fee enough to actually replace it, because nodes
    require a threshold bump (10% by default) rather than any increase.
  * the node accepts a transaction and returns a hash, but the transaction is
    never included in a block. Treating that hash as a completed write would
    overstate the ledger while the run reports success.

No network access and no private key are needed: the broadcast and receipt calls
are replaced with fakes, so this is safe to run in CI on every push.
"""

import contextlib
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Belt and braces: importing the module must never be able to send anything.
os.environ['ARCFLOW_DRY_RUN'] = '1'

_spec = importlib.util.spec_from_file_location(
    'arcflow_publisher', os.path.join(HERE, 'arcflow_publisher.py'))
pub = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pub)

FAKE_PRIV = 0x1234567890abcdef
FAKE_TX = '0x' + 'ab' * 32

# The exact rejection observed in production.
CONFLICT = ("eth_sendRawTransaction -> {'code': -32000, "
            "'message': 'replacement transaction underpriced'}")


def drive(send_impl, receipt_impl):
    """
    Run `publish_one` against fake transport.

    Returns (result, stderr_text, calls) where `calls` records the fee and nonce
    of every broadcast attempt.
    """
    orig_send, orig_receipt, orig_rpc = pub.send_record, pub.wait_for_receipt, pub.rpc
    calls = []

    def fake_send(priv, f_id, t_id, bps, gas, max_fee, priority, nonce):
        calls.append({'max_fee': max_fee, 'nonce': nonce})
        return send_impl(len(calls))

    pub.send_record = fake_send
    pub.wait_for_receipt = receipt_impl
    # eth_getTransactionCount -> the account's next free nonce.
    pub.rpc = lambda method, params=None: '0x1'
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            result = pub.publish_one(FAKE_PRIV, 'arc -> base', 5042, 8453, 5,
                                     120000, 43 * 10 ** 9, 10 ** 9)
    finally:
        pub.send_record, pub.wait_for_receipt, pub.rpc = orig_send, orig_receipt, orig_rpc
    return result, err.getvalue(), calls


def test_conflict_retries_with_a_much_higher_fee():
    def send(n):
        if n == 1:
            raise RuntimeError(CONFLICT)
        return FAKE_TX

    result, err, calls = drive(send, lambda h: 'mined')
    assert result == FAKE_TX, result
    assert len(calls) == 2, calls
    # A 10% bump is the minimum a node accepts for a replacement; nudging the fee
    # by less would just produce the same rejection again.
    assert calls[1]['max_fee'] >= calls[0]['max_fee'] * 1.1, calls
    assert calls[1]['nonce'] == calls[0]['nonce'] == 1, calls
    assert 'higher fee' in err, err


def test_accepted_but_unmined_is_not_counted_as_a_write():
    result, err, calls = drive(lambda n: FAKE_TX, lambda h: 'pending')
    assert result is None, result
    assert len(calls) == 2, calls
    # The retry must reuse the nonce: bumping to the next one would leave a gap if
    # the first transaction is merely slow rather than dropped.
    assert calls[1]['nonce'] == calls[0]['nonce'], calls
    assert calls[1]['max_fee'] > calls[0]['max_fee'], calls
    assert 'not included' in err, err


def test_slow_transaction_that_lands_on_retry_is_a_write():
    seen = []

    def receipt(h):
        seen.append(h)
        return 'pending' if len(seen) == 1 else 'mined'

    result, err, calls = drive(lambda n: FAKE_TX, receipt)
    assert result == FAKE_TX, result
    assert len(calls) == 2, calls
    assert 'retrying with a higher fee' in err, err


def test_reverted_transaction_is_a_failure():
    result, err, calls = drive(lambda n: FAKE_TX, lambda h: 'reverted')
    assert result is None, result
    # A revert spends the nonce, so retrying could only burn more gas.
    assert len(calls) == 1, calls
    assert 'reverted' in err, err


def test_genuine_error_is_not_retried():
    def send(n):
        raise RuntimeError('insufficient funds for gas * price + value')

    result, err, calls = drive(send, lambda h: 'mined')
    assert result is None, result
    assert len(calls) == 1, calls
    assert 'insufficient funds' in err, err


def test_conflict_markers():
    assert pub._is_nonce_conflict(RuntimeError(CONFLICT))
    assert pub._is_nonce_conflict(RuntimeError('nonce too low'))
    assert pub._is_nonce_conflict(RuntimeError('already known'))
    assert not pub._is_nonce_conflict(RuntimeError('insufficient funds'))
    assert not pub._is_nonce_conflict(RuntimeError('execution reverted'))


def main():
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith('test_')]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print('  ok   %s' % name)
        except AssertionError as e:
            failures += 1
            print('  FAIL %s: %s' % (name, e))
        except Exception as e:  # a crash is a failure too
            failures += 1
            print('  FAIL %s: unexpected %s: %s' % (name, type(e).__name__, e))
    print()
    if failures:
        print('%d of %d publisher tests failed' % (failures, len(tests)))
        return 1
    print('All %d publisher tests passed.' % len(tests))
    return 0


if __name__ == '__main__':
    sys.exit(main())
