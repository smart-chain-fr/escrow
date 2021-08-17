from unittest import TestCase
from contextlib import contextmanager
from copy import deepcopy
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError
from hashlib import blake2b

alice = 'tz1hNVs94TTjZh6BZ1PM5HL83A7aiZXkQ8ur'
admin = 'tz1fABJ97CJMSP2DKrQx2HAFazh6GgahQ7ZK'
bob = 'tz1c6PPijJnZYjKiSQND4pMtGMg6csGeAiiF'
oscar = 'tz1Phy92c2n817D17dUGzxNgw1qCkNSTWZY2'
fox = 'tz1XH5UyhRCUmCdUUbqD4tZaaqRTgGaFXt7q'
initial_storage = ContractInterface.from_file("Escrow.tz").storage.dummy()
initial_storage["admin"] = admin

empty_comment = {}

only_admin = "Only admin"
access_denied = "Access denied"
too_early = "Too early to release payment"
no_proof = "A proof is needed to validate the escrow"
already_exists = "Escrow already exists"
doesnt_exist = "Escrow not found"
not_right_amount = "The amount sent doesn't correspond to the price"
bad_address = "Bad address"
already_finished = "Escrow already finished"
already_canceled = "Cancel already requested"
not_cancelable = "Escrow can not be canceled"

state_initialized = "Initialized"
state_buyer_canceled = "Buyer canceled"
state_seller_canceled = "Seller canceled"
state_canceled = "Canceled"
state_validated = "Validated"

escrow_key = blake2b("NFT de Charles".encode()).digest()
not_existing_escrow_key = blake2b("NFTTTTT de Charles".encode()).digest()
escrow_comment = {"id": 1, "idEscrow": escrow_key, "message": "I'm an important message"}
not_working_escrow_comment = {"id": 1, "idEscrow": not_existing_escrow_key, "message": "I'm an important message"}


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
        with self.raisesMichelsonError(only_admin):
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
        }).interpret(storage=init_storage, sender=alice, amount=1000)

        expected_escrows = {
            escrow_key:
                {
                    "buyer": alice,
                    "seller": bob,
                    "broker": None,
                    "product": "NFT de Charles",
                    "price": 1000,
                    "comment": empty_comment,
                    "state": state_initialized,
                    "time": None,
                    "proof": None
                }
        }
        print(res.storage["escrows"])
        print("------------------------------------------------------------------------------------")
        print(expected_escrows)
        self.assertDictEqual(res.storage["escrows"], expected_escrows)
        self.assertEqual(res.operations, [])

        #############################################
        # User tries to overwrite an escrow (fails) #
        #############################################
        init_storage["escrows"] = expected_escrows
        with self.raisesMichelsonError("Escrow already exists"):
            self.escrow.initialize_escrow({
                "seller": bob,
                "broker": None,
                "product": "NFT de Charles",
                "price": 1000,
                "id": escrow_key
            }).interpret(storage=init_storage, sender=alice, amount=1000)

        ################################################################
        # User tries to initialize an escrow with too much XTZ (fails) #
        ################################################################
        with self.raisesMichelsonError(not_right_amount):
            self.escrow.initialize_escrow({
                "seller": bob,
                "broker": None,
                "product": "NFT de Charles",
                "price": 1001,
                "id": "a".encode()
            }).interpret(storage=init_storage, sender=alice, amount=1000)

        ###############################################################
        # User tries to initialize an escrow with too few XTZ (fails) #
        ###############################################################
        with self.raisesMichelsonError(not_right_amount):
            self.escrow.initialize_escrow({
                "seller": bob,
                "broker": None,
                "product": "NFT de Charles",
                "price": 999,
                "id": "a".encode()
            }).interpret(storage=init_storage, sender=alice, amount=1000)

    def test_agree(self):
        init_storage = deepcopy(initial_storage)

        ######################################################################
        # User declares that he received the product the payment is released #
        ######################################################################
        init_storage["escrows"] = {
            escrow_key:
                {
                    "buyer": alice,
                    "seller": bob,
                    "broker": None,
                    "product": "NFT de Charles",
                    "price": 1000,
                    "comment": empty_comment,
                    "state": state_initialized,
                    "time": None,
                    "proof": None
                }
        }
        expected_escrows = deepcopy(init_storage)["escrows"]
        expected_escrows[escrow_key]["state"] = state_validated
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

        res = self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=alice)
        self.assertDictEqual(res.storage["escrows"], expected_escrows)
        self.assertEqual(res.operations.pop(), operation)

        ##################################################################
        # The admin releases a payment for a user before the 24hr (fails #
        ##################################################################

        init_storage["escrows"][escrow_key]["time"] = 1
        init_storage["escrows"][escrow_key]["proof"] = "toto"
        with self.raisesMichelsonError(too_early):
            self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=admin, now=900)

            #######################################################################
        # The admin releases a payment for a user (24hr have passed it works) #
        #######################################################################
        expected_escrows[escrow_key]["time"] = 1
        expected_escrows[escrow_key]["proof"] = "toto"
        res2 = self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=admin, now=100000)
        self.assertDictEqual(res2.storage["escrows"], expected_escrows)
        self.assertEqual(res2.operations.pop(), operation)

        ####################################################################
        # Random user tries to validate an escrow for someone else (fails) #
        ####################################################################
        with self.raisesMichelsonError(access_denied):
            self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=oscar, now=500)

        ###############################################################
        # Seller tries to validate an escrow for someone else (fails) #
        ###############################################################
        with self.raisesMichelsonError(access_denied):
            self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=bob, now=500)
        ###############################################################
        # User tries to validate an escrow that doesn't exist (fails) #
        ###############################################################
        with self.raisesMichelsonError(doesnt_exist):
            self.escrow.agree(blake2b("N".encode()).digest()).interpret(storage=init_storage, sender=alice, now=500)

        ######################################################################
        # User tries to validate an escrow that is already validated (fails) #
        ######################################################################
        init_storage["escrows"][escrow_key]["state"] = state_validated
        with self.raisesMichelsonError(already_finished):
            self.escrow.agree(escrow_key).interpret(storage=init_storage, sender=alice, now=500)

    def test_cancel_escrow(self):
        init_storage = deepcopy(initial_storage)

        ##################################################################
        # Random user tries to cancel an escrow for someone else (fails) #
        ##################################################################
        init_storage["escrows"] = {
            escrow_key:
                {
                    "buyer": alice,
                    "seller": bob,
                    "broker": None,
                    "product": "NFT de Charles",
                    "price": 1000,
                    "comment": empty_comment,
                    "state": state_initialized,
                    "time": None,
                    "proof": None
                }
        }
        with self.raisesMichelsonError(access_denied):
            self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=admin)

        #########################################################
        # Buyer tries to create a cancellation request  (works) #
        #########################################################
        res = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=alice)
        self.assertEqual(res.storage["escrows"][escrow_key]["state"], state_buyer_canceled)
        self.assertEqual(res.operations, [])

        #########################################################
        # Seller tries to create a cancellation request (works) #
        #########################################################
        res2 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=bob)
        self.assertEqual(res2.storage["escrows"][escrow_key]["state"], state_seller_canceled)
        self.assertEqual(res2.operations, [])

        ##########################################################################
        # Seller tries to cancel 1 more time  (works but doesn't change anything) #
        ##########################################################################
        init_storage["escrows"][escrow_key]["state"] = state_seller_canceled
        with self.raisesMichelsonError(already_canceled):
            self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=bob)

        ##########################################################################
        # Buyer tries to cancel 1 more time  (works but doesn't change anything) #
        ##########################################################################
        init_storage["escrows"][escrow_key]["state"] = state_buyer_canceled
        with self.raisesMichelsonError(already_canceled):
            self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=alice)

        ##############################################################################
        # seller accepts the cancellation request, the XTZ is sent back to the buyer #
        ##############################################################################
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

        res5 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=bob)
        print(res5.storage)
        self.assertEqual(res5.storage["escrows"][escrow_key]["state"], state_canceled)
        self.assertEqual(res5.operations.pop(), operation)

        ##############################################################################
        # buyer accepts the cancellation request, the XTZ is sent back to the buyer #
        ##############################################################################
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
        init_storage["escrows"][escrow_key]["state"] = state_seller_canceled
        res6 = self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=alice)
        self.assertEqual(res6.storage["escrows"][escrow_key]["state"], state_canceled)
        self.assertEqual(res6.operations.pop(), operation)

        #####################################################################################
        # Buyer tries to create a cancellation request but the escrow doesn't exist (works) #
        #####################################################################################
        with self.raisesMichelsonError(doesnt_exist):
            self.escrow.cancel_escrow("e".encode()).interpret(storage=init_storage, sender=alice)

        ###############################################################
        # Random user tries to create a cancellation request  (fails) #
        ###############################################################
        with self.raisesMichelsonError(access_denied):
            self.escrow.cancel_escrow(escrow_key).interpret(storage=init_storage, sender=admin)

    def test_add_comment(self):
        init_storage = deepcopy(initial_storage)

        #####################################################################################
        #                      Initializes an escrow in the storage                         #
        #####################################################################################
        expected_escrows = {
            escrow_key:
                {
                    "buyer": alice,
                    "seller": bob,
                    "broker": fox,
                    "product": "NFT de Charles",
                    "price": 1000,
                    "comment": empty_comment,
                    "state": state_initialized,
                    "time": None,
                    "proof": None
                }
        }

        init_storage["escrows"] = expected_escrows

        #####################################################################################
        #                        Simulates the addComment function                          #
        #####################################################################################

        comment_broker = self.escrow.addComment(escrow_comment).interpret(storage=init_storage, sender=fox, now=200)
        comment_seller = self.escrow.addComment(escrow_comment).interpret(storage=init_storage, sender=bob, now=200)
        comment_buyer = self.escrow.addComment(escrow_comment).interpret(storage=init_storage, sender=alice, now=200)
        comment_admin = self.escrow.addComment(escrow_comment).interpret(storage=init_storage, sender=admin, now=200)

        print(comment_broker.storage["escrows"][escrow_key]["comment"])
        print(comment_seller.storage["escrows"][escrow_key]["comment"])
        print(comment_buyer.storage["escrows"][escrow_key]["comment"])
        print(comment_admin.storage["escrows"][escrow_key]["comment"])

        ##########################################################################################################
        #       Check equality between storage and escrow comment, the tuple second key is defined by :          #
        #               // 0 = Smartlink(admin) ; 1 = Buyer ; 2 = Seller ; 3 = Broker                            #
        ##########################################################################################################

        self.assertEqual(comment_broker.storage["escrows"][escrow_key]["comment"],
                         {(200, 3): escrow_comment["message"]})
        self.assertEqual(comment_seller.storage["escrows"][escrow_key]["comment"],
                         {(200, 2): escrow_comment["message"]})
        self.assertEqual(comment_buyer.storage["escrows"][escrow_key]["comment"], {(200, 1): escrow_comment["message"]})
        self.assertEqual(comment_admin.storage["escrows"][escrow_key]["comment"], {(200, 0): escrow_comment["message"]})

        ###############################################################################
        # Random user tries to add a comment to an escrow he doesn't belong in(fails) #
        ###############################################################################
        with self.raisesMichelsonError(access_denied):
            self.escrow.addComment(escrow_comment).interpret(storage=init_storage, sender=oscar, now=500)

        #################################################################################
        # Random user tries to add a comment to an escrow that doesn't exists in(fails) #
        #################################################################################
        with self.raisesMichelsonError(doesnt_exist):
            self.escrow.addComment(not_working_escrow_comment).interpret(storage=init_storage, sender=alice, now=500)

