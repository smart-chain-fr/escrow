from unittest import TestCase
from contextlib import contextmanager
from copy import deepcopy
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from hashlib import blake2b

alice = 'tz1hNVs94TTjZh6BZ1PM5HL83A7aiZXkQ8ur'
admin = 'tz1fABJ97CJMSP2DKrQx2HAFazh6GgahQ7ZK'
bob = 'tz1c6PPijJnZYjKiSQND4pMtGMg6csGeAiiF'
initial_storage = ContractInterface.from_file("Escrow.tz").storage.dummy()
initial_storage["admin"] = admin
empty_comment = {
    "buyer": "",
    "seller": ""
}
state = "initialized"
escrow_key = blake2b("NFT de Charles".encode()).digest()


class EscrowContractTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.escrow = ContractInterface.from_file('Escrow.tz')
        cls.maxDiff = None

    @contextmanager
    def raisesMichelsonError(self, error_message):
        with self.assertRaises(MichelsonRuntimeError) as r:
            yield r

        error_msg = r.exception.format_stdout()
        if "FAILWITH" in error_msg:
            self.assertEqual(f"FAILWITH: '{error_message}'", r.exception.format_stdout())
        else:
            self.assertEqual(f"'{error_message}': ", r.exception.format_stdout())

    def test_setAdmin(self):
        init_storage = deepcopy(initial_storage)
        res = self.escrow.setAdmin(bob).interpret(storage=init_storage, sender=admin)
        self.assertEqual(bob, res.storage["admin"])
        self.assertEqual([], res.operations)
        with self.raisesMichelsonError("Only admin"):
            self.escrow.setAdmin(bob).interpret(storage=init_storage, source=alice)

    def test_initialize_escrow(self):
        init_storage = deepcopy(initial_storage)
        res = self.escrow.initialize_escrow({
            "seller": bob,
            "broker": None,
            "product": "NFT de Charles",
            "price": 1000,
            "id": escrow_key
        }).interpret(storage=init_storage, sender=alice, now=420, amount=1000)
        expected_escrows = {
            blake2b("NFT de Charles".encode()).digest():
                {
                    "buyer": alice,
                    "seller": bob,
                    "broker": None,
                    "product": "NFT de Charles",
                    "price": 1000,
                    "comment": empty_comment,
                    "state": state,
                    "time": 420
                }
        }
        self.assertDictEqual(res.storage["escrows"], expected_escrows)
        self.assertEqual(res.operations, [])

        init_storage["escrows"] = expected_escrows
        with self.raisesMichelsonError("Escrow already exists"):
            self.escrow.initialize_escrow({
                "seller": bob,
                "broker": None,
                "product": "NFT de Charles",
                "price": 1000,
                "id": escrow_key
            }).interpret(storage=init_storage, sender=alice, now=420, amount=1000)
        with self.raisesMichelsonError("The amount sent doesn't correspond to the price"):
            self.escrow.initialize_escrow({
                "seller": bob,
                "broker": None,
                "product": "NFT de Charles",
                "price": 1001,
                "id": "a".encode()
            }).interpret(storage=init_storage, sender=alice, now=420, amount=1000)
        with self.raisesMichelsonError("The amount sent doesn't correspond to the price"):
            self.escrow.initialize_escrow({
                "seller": bob,
                "broker": None,
                "product": "NFT de Charles",
                "price": 999,
                "id": "a".encode()
            }).interpret(storage=init_storage, sender=alice, now=420, amount=1000)

    def test_agree(self):
        init_storage = deepcopy(initial_storage)
        init_storage["escrows"] = {
            blake2b("NFT de Charles".encode()).digest():
                {
                    "buyer": alice,
                    "seller": bob,
                    "broker": None,
                    "product": "NFT de Charles",
                    "price": 1000,
                    "comment": empty_comment,
                    "state": state,
                    "time": 420
                }
        }
        expected_escrows = deepcopy(init_storage)["escrows"]
        expected_escrows[blake2b("NFT de Charles".encode()).digest()]["state"] = "Completed"
        operation = {
            'kind': 'transaction',
            'source': 'KT1BEqzn5Wx8uJrZNvuS9DVHmLvG9td3fDLi',
            'destination': bob,
            'amount': '1000',
            'parameters': {
                'entrypoint': 'default',
                'value': {
                    'prim': 'Unit'
                }
            }
        }
        res = self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=alice, now=500)
        self.assertDictEqual(res.storage["escrows"], expected_escrows)
        self.assertEqual(res.operations.pop(), operation)

        """res2 = self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=admin, now=100000)
        self.assertDictEqual(res2.storage["escrows"], expected_escrows)
        self.assertEqual(res2.operations.pop(), operation)"""
        with self.raisesMichelsonError("Access denied"):
            self.escrow.agree(blake2b("NFT de Charles".encode()).digest()).interpret(storage=init_storage,
                                                                                     sender=bob, now=500)
        with self.raisesMichelsonError("Escrow not found"):
            self.escrow.agree(blake2b("N".encode()).digest()).interpret(storage=init_storage, sender=alice, now=500)

    def test_cancel_escrow(self):
        init_storage = deepcopy(initial_storage)
        init_storage["escrows"] = {
            blake2b("NFT de Charles".encode()).digest():
                {
                    "buyer": alice,
                    "seller": bob,
                    "broker": None,
                    "product": "NFT de Charles",
                    "price": 1000,
                    "comment": empty_comment,
                    "state": state,
                    "time": 420
                }
        }
        expected_cancels = {
            escrow_key: {
                alice: True
            }
        }
        with self.raisesMichelsonError("Access denied"):
            self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=admin)

        res = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=alice)
        self.assertDictEqual(res.storage["cancels"], expected_cancels)
        self.assertEqual(res.operations, [])

        init_storage["cancels"] = deepcopy(expected_cancels)
        res2 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=alice)
        self.assertDictEqual(res2.storage, init_storage)
        self.assertEqual(res2.operations, [])
        expected_cancels[escrow_key][bob] = True
        operation = {
            'kind': 'transaction',
            'source': 'KT1BEqzn5Wx8uJrZNvuS9DVHmLvG9td3fDLi',
            'destination': alice,
            'amount': '1000',
            'parameters': {
                'entrypoint': 'default',
                'value': {
                    'prim': 'Unit'
                }
            }
        }

        res3 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=bob)
        self.assertDictEqual(res3.storage["cancels"], expected_cancels)
        self.assertEqual(res3.operations.pop(), operation)

        with self.raisesMichelsonError("Escrow not found"):
            self.escrow.cancel_escrow("e".encode()).interpret(storage=init_storage, sender=alice)

        with self.raisesMichelsonError("Access denied"):
            self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=admin)

