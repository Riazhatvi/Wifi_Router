import unittest
from unittest.mock import Mock, call
from mikrotik import Router, quota_bytes

class RouterTests(unittest.TestCase):
    def setUp(self):
        self.router = Router('https://router.example', 'admin', 'test-only')
        self.router.call = Mock()

    def test_create_enforced_quota(self):
        self.router.create('ali', 'customer-test', '10', 'monthly')
        self.router.call.assert_called_once_with('ip/hotspot/user', 'PUT', {
            'name': 'ali', 'password': 'customer-test', 'limit-bytes-total': '10000000000',
            'profile': 'monthly', 'disabled': 'false'})

    def test_disable_removes_active_sessions(self):
        self.router.call.side_effect = [None, [{'.id': '*1', 'name': 'ali'}],
                                        [{'.id': '*A', 'user': 'ali'}, {'.id': '*B', 'user': 'other'}], None]
        self.router.enable('*1', False)
        self.assertEqual(self.router.call.call_args_list[-1], call('ip/hotspot/active/%2AA', 'DELETE'))

    def test_renew_order_and_fail_closed(self):
        self.router.enable = Mock()
        self.router.renew('*1')
        self.assertEqual(self.router.enable.call_args_list, [call('*1', False), call('*1', True)])
        self.router.call.assert_called_once_with('ip/hotspot/user/reset-counters', 'POST', {'.id': '*1'})
        self.router.enable.reset_mock()
        self.router.call.side_effect = RuntimeError('failed reset')
        with self.assertRaises(RuntimeError):
            self.router.renew('*1')
        self.router.enable.assert_called_once_with('*1', False)

    def test_https_required(self):
        for address in ['http://router.example', 'https://user:pass@router.example', 'https://router.example/path']:
            with self.subTest(address=address), self.assertRaises(ValueError):
                Router(address, 'user', 'test')

    def test_bad_allowance(self):
        for value in ['NaN', 'Infinity', '-1', '0']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                quota_bytes(value)
        self.assertEqual(quota_bytes('0.1'), 100000000)
