from unittest import TestCase
from contextlib import contextmanager
from copy import deepcopy
from pytezos import ContractInterface, pytezos, MichelsonRuntimeError

alice = 'tz1hNVs94TTjZh6BZ1PM5HL83A7aiZXkQ8ur'
admin = 'tz1fABJ97CJMSP2DKrQx2HAFazh6GgahQ7ZK'
bob = 'tz1c6PPijJnZYjKiSQND4pMtGMg6csGeAiiF'
initial_storage = ContractInterface.from_file("Escrow.tz").storage.dummy()
initial_storage["admin"] = admin

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
        with self.raisesMichelsonError("Only the admin can run this function"):
            self.escrow.setAdmin(bob).interpret(storage=init_storage, source=alice)
