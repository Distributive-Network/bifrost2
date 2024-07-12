import unittest
import asyncio
import pythonmonkey as pm
import dcp
dcp.init()

class TestWallet(unittest.TestCase):

    def test_smoke_keystore_address(self):
        ks = dcp.wallet.get()
        self.assertTrue(isinstance(ks, dcp.wallet.Keystore))

        address = ks.address
        self.assertTrue(isinstance(address, dcp.wallet.Address))
        self.assertTrue(address.eq(address.address))

    def test_smoke_async_get(self):
        ks1 = dcp.wallet.get()
        ks2 = asyncio.run(dcp.wallet.aio.get())

        # TODO: we can't pass the address in since ks2.address is python... need to fix.
        self.assertTrue(ks1.address.eq(ks2.address.address))
        

if __name__ == '__main__':
    unittest.main()

