from unittest import TestCase
from contextlib import contextmanager
from copy import deepcopy
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from hashlib import blake2b

alice = 'tz1hNVs94TTjZh6BZ1PM5HL83A7aiZXkQ8ur'
admin = 'tz1fABJ97CJMSP2DKrQx2HAFazh6GgahQ7ZK'
bob = 'tz1c6PPijJnZYjKiSQND4pMtGMg6csGeAiiF'
oscar = 'tz1Phy92c2n817D17dUGzxNgw1qCkNSTWZY2'
initial_storage = ContractInterface.from_file("Escrow.tz").storage.dummy()
initial_storage["admin"] = admin
empty_comment = {
    "buyer": "",
    "seller": ""
}
state_initialized = "EX"
state_cancelling = "AN"
state_cancelled = "CA"
state_completed = "VA"
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
        ################################
        # Admin sets new admin (works) #
        ################################
        res = self.escrow.setAdmin(bob).interpret(storage=init_storage, sender=admin)
        self.assertEqual(bob, res.storage["admin"])
        self.assertEqual([], res.operations)

        ######################################
        # random user sets new admin (fails) #
        ######################################
        with self.raisesMichelsonError("Only admin"):
            self.escrow.setAdmin(bob).interpret(storage=init_storage, source=alice)

    def test_initialize_escrow(self):
        init_storage = deepcopy(initial_storage)
        ##################################################################
        # User initializes an escrow with the right amount of XTZ (works)#
        ##################################################################
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
                    "state": state_initialized,
                    "time": 420
                }
        }
        self.assertDictEqual(res.storage["escrows"], expected_escrows)
        self.assertEqual(res.operations, [])

        init_storage["escrows"] = expected_escrows
        #############################################
        # User tries to overwrite an escrow (fails) #
        #############################################
        with self.raisesMichelsonError("Escrow already exists"):
            self.escrow.initialize_escrow({
                "seller": bob,
                "broker": None,
                "product": "NFT de Charles",
                "price": 1000,
                "id": escrow_key
            }).interpret(storage=init_storage, sender=alice, now=420, amount=1000)

        ################################################################
        # User tries to initialize an escrow with too much XTZ (fails) #
        ################################################################
        with self.raisesMichelsonError("The amount sent doesn't correspond to the price"):
            self.escrow.initialize_escrow({
                "seller": bob,
                "broker": None,
                "product": "NFT de Charles",
                "price": 1001,
                "id": "a".encode()
            }).interpret(storage=init_storage, sender=alice, now=420, amount=1000)

        ###############################################################
        # User tries to initialize an escrow with too few XTZ (fails) #
        ###############################################################
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
                    "state": state_initialized,
                    "time": 420
                }
        }
        expected_escrows = deepcopy(init_storage)["escrows"]
        expected_escrows[blake2b("NFT de Charles".encode()).digest()]["state"] = state_completed
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

        ######################################################################
        # User declares that he received the product the payment is released #
        ######################################################################
        res = self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=alice, now=500)
        self.assertDictEqual(res.storage["escrows"], expected_escrows)
        self.assertEqual(res.operations.pop(), operation)

        ##################################################################
        # The admin releases a payment for a user before the 24hr (fails #
        ##################################################################
        with self.raisesMichelsonError("Too early to release payment"):
            self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=admin, now=900)

        #######################################################################
        # The admin releases a payment for a user (24hr have passed it works) #
        #######################################################################
        res2 = self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=admin, now=100000)
        self.assertDictEqual(res2.storage["escrows"], expected_escrows)
        self.assertEqual(res2.operations.pop(), operation)

        ####################################################################
        # Random user tries to validate an escrow for someone else (fails) #
        ####################################################################
        with self.raisesMichelsonError("Access denied"):
            self.escrow.agree(blake2b("NFT de Charles".encode()).digest()).interpret(storage=init_storage,
                                                                                     sender=oscar, now=500)

        ###############################################################
        # Seller tries to validate an escrow for someone else (fails) #
        ###############################################################
        with self.raisesMichelsonError("Access denied"):
            self.escrow.agree(blake2b("NFT de Charles".encode()).digest()).interpret(storage=init_storage,
                                                                                     sender=bob, now=500)
        ###############################################################
        # User tries to validate an escrow that doesn't exist (fails) #
        ###############################################################
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
                    "state": state_initialized,
                    "time": 420
                }
        }
        expected_cancels = {
            escrow_key: {
                alice: True
            }
        }
        ##################################################################
        # Random user tries to cancel an escrow for someone else (fails) #
        ##################################################################
        with self.raisesMichelsonError("Access denied"):
            self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=admin)

        #########################################################
        # Buyer tries to create a cancellation request  (works) #
        #########################################################
        res = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=alice)
        self.assertDictEqual(res.storage["cancels"], expected_cancels)
        self.assertEqual(res.storage["escrows"][escrow_key]["state"], state_cancelling)
        self.assertEqual(res.operations, [])

        expected_cancels = {
            escrow_key: {
                bob: True
            }
        }
        #########################################################
        # Seller tries to create a cancellation request  (works) #
        #########################################################
        res2 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=bob)
        self.assertDictEqual(res2.storage["cancels"], expected_cancels)
        self.assertEqual(res2.storage["escrows"][escrow_key]["state"], state_cancelling)
        self.assertEqual(res2.operations, [])

        init_storage["cancels"] = deepcopy(expected_cancels)
        init_storage["escrows"][escrow_key]["state"] = state_cancelling
        
        ##########################################################################
        # Seller tries to cancel 1 more time  (works but doesn't change anything) #
        ##########################################################################
        res3 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=bob)
        self.assertDictEqual(res3.storage, init_storage)
        self.assertEqual(res3.storage["escrows"][escrow_key]["state"], state_cancelling)
        self.assertEqual(res3.operations, [])

        expected_cancels = {
            escrow_key: {
                alice: True
            }
        }
        init_storage["cancels"] = deepcopy(expected_cancels)
        ##########################################################################
        # Buyer tries to cancel 1 more time  (works but doesn't change anything) #
        ##########################################################################
        res4 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=alice)
        self.assertDictEqual(res4.storage, init_storage)
        self.assertEqual(res4.storage["escrows"][escrow_key]["state"], state_cancelling)
        self.assertEqual(res4.operations, [])
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

        ##############################################################################
        # seller accepts the cancellation request, the XTZ is sent back to the buyer #
        ##############################################################################
        res5 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=bob)
        self.assertDictEqual(res5.storage["cancels"], expected_cancels)
        self.assertEqual(res5.storage["escrows"][escrow_key]["state"], state_cancelled)
        self.assertEqual(res5.operations.pop(), operation)

        expected_cancels[escrow_key][alice] = True
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
        ##############################################################################
        # buyer accepts the cancellation request, the XTZ is sent back to the buyer #
        ##############################################################################
        res6 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=bob)
        self.assertDictEqual(res6.storage["cancels"], expected_cancels)
        self.assertEqual(res6.storage["escrows"][escrow_key]["state"], state_cancelled)
        self.assertEqual(res6.operations.pop(), operation)

        #####################################################################################
        # Buyer tries to create a cancellation request but the escrow doesn't exist (works) #
        #####################################################################################
        with self.raisesMichelsonError("Escrow not found"):
            self.escrow.cancel_escrow("e".encode()).interpret(storage=init_storage, sender=alice)

        ###############################################################
        # Random user tries to create a cancellation request  (fails) #
        ###############################################################
        with self.raisesMichelsonError("Access denied"):
            self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=admin)

