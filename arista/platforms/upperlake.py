from ..core.fixed import FixedSystem
from ..core.platform import registerPlatform
from ..core.port import PortLayout
from ..core.psu import PsuSlot
from ..core.types import PciAddr
from ..core.utils import incrange

from ..components.asic.xgs.tomahawk import Tomahawk
from ..components.cpu.crow import KoiCpldRegisters
from ..components.dpm.ucd import Ucd90120A, UcdGpi
from ..components.max6697 import Max6697
from ..components.psu.delta import DPS495CB, DPS750AB
from ..components.psu.artesyn import DS495SPE
from ..components.scd import Scd

from ..descs.gpio import GpioDesc
from ..descs.reset import ResetDesc
from ..descs.sensor import Position, SensorDesc

from .cpu.crow import CrowCpu

@registerPlatform()
class Upperlake(FixedSystem):

   SID = ['Upperlake', 'UpperlakeES', 'UpperlakeSsd']
   SKU = ['DCS-7060CX-32S', 'DCS-7060CX-32S-ES', 'DCS-7060CX-32S-SSD']

   PORTS = PortLayout(
      qsfps=incrange(1, 32),
      sfps=incrange(33, 34),
   )

   def __init__(self):
      super(Upperlake, self).__init__()

      self.newComponent(Tomahawk, PciAddr(bus=0x01))

      scd = self.newComponent(Scd, PciAddr(bus=0x02))

      cpu = self.newComponent(CrowCpu, scd, hwmonBus=1, registerCls=KoiCpldRegisters)
      self.cpu = cpu
      self.syscpld = cpu.syscpld

      scd.createWatchdog()

      scd.newComponent(Max6697, addr=scd.i2cAddr(0, 0x1a), sensors=[
         SensorDesc(diode=0, name='Board sensor',
                    position=Position.OTHER, target=55, overheat=65, critical=75),
         SensorDesc(diode=1, name='Switch chip left sensor',
                    position=Position.OTHER, target=55, overheat=95, critical=105),
         SensorDesc(diode=5, name='Switch chip right sensor',
                    position=Position.OTHER, target=55, overheat=95, critical=105),
         SensorDesc(diode=6, name='Front-panel temp sensor',
                    position=Position.INLET, target=55, overheat=65, critical=75),
      ])

      scd.newComponent(Ucd90120A, scd.i2cAddr(1, 0x4e, t=3))
      scd.newComponent(Ucd90120A, scd.i2cAddr(5, 0x4e, t=3), causes={
         'reboot': UcdGpi(1),
         'watchdog': UcdGpi(2),
         'overtemp': UcdGpi(4),
         'powerloss': UcdGpi(5),
      })

      scd.addSmbusMasterRange(0x8000, 5, 0x80)

      scd.addLeds([
         (0x6050, 'status'),
         (0x6060, 'fan_status'),
         (0x6070, 'psu1'),
         (0x6080, 'psu2'),
         (0x6090, 'beacon'),
      ])

      scd.addResets([
         ResetDesc('switch_chip_reset', addr=0x4000, bit=1),
         ResetDesc('switch_chip_pcie_reset', addr=0x4000, bit=2)
      ])

      scd.addGpios([
         GpioDesc("psu1_present", 0x5000, 0, ro=True),
         GpioDesc("psu2_present", 0x5000, 1, ro=True),
      ])

      self.syscpld.addGpios([
         ('psu1DcOk', 'psu1_status'),
         ('psu2DcOk', 'psu2_status'),
         ('psu1AcOk', 'psu1_ac_status'),
         ('psu2AcOk', 'psu2_ac_status'),
      ])

      for psuId, bus in [(1, 4), (2, 3)]:
         addrFunc=lambda addr, bus=bus: \
                  scd.i2cAddr(bus, addr, t=3, datr=2, datw=3)
         name = "psu%d" % psuId
         scd.newComponent(
            PsuSlot,
            slotId=psuId,
            addrFunc=addrFunc,
            presentGpio=scd.inventory.getGpio("%s_present" % name),
            inputOkGpio=self.syscpld.inventory.getGpio("%s_ac_status" % name),
            outputOkGpio=self.syscpld.inventory.getGpio("%s_status" % name),
            led=scd.inventory.getLed(name),
            psus=[
               DPS495CB,
               DPS750AB,
               DS495SPE,
            ],
         )

      intrRegs = [
         scd.createInterrupt(addr=0x3000, num=0),
         scd.createInterrupt(addr=0x3030, num=1),
      ]

      scd.addSfpSlotBlock(sfpRange=self.PORTS.sfpRange, addr=0x5010, bus=8, ledAddr=0x6100)

      scd.addQsfpSlotBlock(
         qsfpRange=self.PORTS.qsfpRange,
         addr=0x5050,
         bus=16,
         ledAddr=0x6140,
         ledLanes=4,
         intrRegs=intrRegs,
         intrRegIdxFn=lambda xcvrId: 1,
         intrBitFn=lambda xcvrId: xcvrId - 1,
         isHwLpModeAvail=False
      )

@registerPlatform()
class UpperlakePlus(Upperlake):
   SID = ['UpperlakePlus']
   SKU = ['DCS-7060CX2-32S']
