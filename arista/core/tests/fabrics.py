
from __future__ import absolute_import, division, print_function

from ...tests.testing import unittest
from ...tests.logging import getLogger

from ...components.denali.card import DenaliFabricSlot
from ...components.denali.fabric import DenaliFabric
from ...components.scd import Scd
from ...core.fabric import Fabric

from ..card import CardSlot
from ..component import Priority
from ..platform import getPlatformSkus
from ..types import PciAddr

from ... import platforms as _

class FabricTest(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
      cls.logger = getLogger(cls.__name__)

   def createFabric(self, cls):
      if issubclass(cls, DenaliFabric):
         pci = PciAddr(bus=0x01)
         scd = Scd(PciAddr(bus=0x02))
         bus = scd.getSmbus(0x03)
         slotId = DenaliFabric.ABSOLUTE_CARD_OFFSET
         slot = DenaliFabricSlot(None, slotId, pci, bus)
      else:
         slot = CardSlot(None, 0)
      return cls(slot=slot)

   def testSetup(self):
      for name, fabricCls in getPlatformSkus().items():
         if not issubclass(fabricCls, Fabric):
            continue
         self.logger.info('Testing setup for fabric %s', name)
         fabric = self.createFabric(fabricCls)
         assert fabric
         for f in [None, Priority.defaultFilter, Priority.backgroundFilter]:
            fabric.setup(filters=f)
         assert fabric

   def testClean(self):
      for name, fabricCls in getPlatformSkus().items():
         if not issubclass(fabricCls, Fabric):
            continue
         self.logger.info('Testing clean for fabric %s', name)
         fabric = self.createFabric(fabricCls)
         assert fabric
         fabric.clean()
         assert fabric

if __name__ == '__main__':
   unittest.main()
