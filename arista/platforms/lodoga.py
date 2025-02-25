from ..core.fixed import FixedSystem
from ..core.platform import registerPlatform
from ..core.port import PortLayout
from ..core.psu import PsuSlot
from ..core.types import PciAddr
from ..core.utils import incrange

from ..components.asic.xgs.trident3 import Trident3
from ..components.dpm.ucd import Ucd90120A, UcdGpi
from ..components.max6658 import Max6658
from ..components.psu.delta import DPS495CB
from ..components.psu.artesyn import DS495SPE
from ..components.scd import Scd

from ..descs.gpio import GpioDesc
from ..descs.reset import ResetDesc
from ..descs.sensor import Position, SensorDesc

from .cpu.crow import CrowCpu

@registerPlatform()
class Lodoga(FixedSystem):

   SID = ['Lodoga', 'LodogaSsd']
   SKU = ['DCS-7050CX3-32S', 'DCS-7050CX3-32S-SSD']

   PORTS = PortLayout(
      qsfps=incrange(1, 32),
      sfps=incrange(33, 34),
   )

   def __init__(self):
      super(Lodoga, self).__init__()

      self.newComponent(Trident3, PciAddr(bus=0x01))

      scd = self.newComponent(Scd, PciAddr(bus=0x02))

      cpu = self.newComponent(CrowCpu, scd)
      self.cpu = cpu
      self.syscpld = cpu.syscpld

      scd.createWatchdog()

      scd.newComponent(Ucd90120A, scd.i2cAddr(0, 0x4e, t=3))

      scd.newComponent(Max6658, scd.i2cAddr(9, 0x4c), sensors=[
         SensorDesc(diode=0, name='Board temp sensor',
                    position=Position.OTHER, target=65, overheat=75, critical=85),
         SensorDesc(diode=1, name='Front-panel temp sensor',
                    position=Position.INLET, target=50, overheat=60, critical=65),
      ])

      scd.addSmbusMasterRange(0x8000, 6, 0x80)

      scd.addLeds([
         (0x6050, 'status'),
         (0x6060, 'fan_status'),
         (0x6070, 'psu1'),
         (0x6080, 'psu2'),
         (0x6090, 'beacon'),
      ])

      scd.newComponent(Ucd90120A, scd.i2cAddr(13, 0x4e, t=3), causes={
         'reboot': UcdGpi(1),
         'watchdog': UcdGpi(2),
         'overtemp': UcdGpi(4),
         'powerloss': UcdGpi(5),
         'systempowerloss': UcdGpi(6),
      })

      scd.addResets([
         ResetDesc('switch_chip_reset', addr=0x4000, bit=1),
         ResetDesc('switch_chip_pcie_reset', addr=0x4000, bit=2)
      ])

      scd.addGpios([
         GpioDesc("psu1_present", 0x5000, 1, ro=True),
         GpioDesc("psu2_present", 0x5000, 0, ro=True),
         GpioDesc("psu1_status", 0x5000, 9, ro=True),
         GpioDesc("psu2_status", 0x5000, 8, ro=True),
         GpioDesc("psu1_ac_status", 0x5000, 11, ro=True),
         GpioDesc("psu2_ac_status", 0x5000, 10, ro=True),
      ])

      for psuId in incrange(1, 2):
         addrFunc=lambda addr, i=psuId: \
                  scd.i2cAddr(10 + i, addr, t=3, datr=2, datw=3)
         name = "psu%d" % psuId
         scd.newComponent(
            PsuSlot,
            slotId=psuId,
            addrFunc=addrFunc,
            presentGpio=scd.inventory.getGpio("%s_present" % name),
            inputOkGpio=scd.inventory.getGpio("%s_ac_status" % name),
            outputOkGpio=scd.inventory.getGpio("%s_status" % name),
            led=scd.inventory.getLed(name),
            psus=[
               DPS495CB,
               DS495SPE,
            ],
         )

      intrRegs = [
         scd.createInterrupt(addr=0x3000, num=0),
         scd.createInterrupt(addr=0x3030, num=1),
      ]

      scd.addSfpSlotBlock(
         sfpRange=self.PORTS.sfpRange,
         addr=0xA010,
         bus=16,
         ledAddr=0x6120,
         intrRegs=intrRegs,
         intrRegIdxFn=lambda xcvrId: 0,
         intrBitFn=lambda xcvrId: 28 + xcvrId - 33
      )

      scd.addQsfpSlotBlock(
         qsfpRange=self.PORTS.qsfpRange,
         addr=0xA050,
         bus=24,
         ledAddr=0x6140,
         ledLanes=4,
         intrRegs=intrRegs,
         intrRegIdxFn=lambda xcvrId: 1,
         intrBitFn=lambda xcvrId: xcvrId - 1,
         isHwLpModeAvail=False
      )
