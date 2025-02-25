from ...core.platform import registerPlatform

from ...components.max31790 import Max31790
from ...components.tmp464 import Tmp464

from ...descs.sensor import SensorDesc, Position

from .eldridge import Eldridge

@registerPlatform()
class Brooks(Eldridge):
   SID = ['Brooks']
   SKU = ['DCS-7804-FM']

   ASIC_PLX_DOWNSTREAM_PORTS = {
      0 : 1,
      1 : 3,
   }

   def createStandbyFans(self):
      chip = self.pca.newComponent(Max31790, self.pca.i2cAddr(0x2d),
                                   name='amax31790_4u')
      self.createStandbyFansForChip(chip, 1, 4)

   def createStandbySensors(self):
      self.pca.newComponent(Tmp464, self.pca.i2cAddr(0x48), sensors=[
         SensorDesc(diode=0, name='Board sensor 1',
                    position=Position.OTHER, target=75, overheat=85, critical=95),
         SensorDesc(diode=1, name='Ramon 0 PCB',
                    position=Position.OTHER, target=70, overheat=80, critical=90),
         SensorDesc(diode=2, name='Ramon 1 PCB',
                    position=Position.OTHER, target=70, overheat=80, critical=90),
         SensorDesc(diode=3, name='Outlet',
                    position=Position.OUTLET, target=75, overheat=85, critical=95),
         SensorDesc(diode=4, name='Inlet',
                    position=Position.INLET, target=75, overheat=85, critical=95),
      ])
      self.pca.newComponent(Tmp464, self.pca.i2cAddr(0x49), sensors=[
         SensorDesc(diode=0, name='Board sensor 2',
                    position=Position.OTHER, target=75, overheat=85, critical=95),
         SensorDesc(diode=2, name='Ramon 0 Core (secondary)',
                    position=Position.OTHER, target=75, overheat=85, critical=95),
         SensorDesc(diode=3, name='Ramon 1 Core (secondary)',
                    position=Position.OTHER, target=75, overheat=85, critical=95),
      ])
