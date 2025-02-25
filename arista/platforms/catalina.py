from ..core.fixed import FixedSystem
from ..core.platform import registerPlatform
from ..core.port import PortLayout
from ..core.psu import PsuSlot
from ..core.types import PciAddr
from ..core.utils import incrange

from ..components.asic.xgs.tomahawk4 import Tomahawk4
from ..components.dpm.ucd import Ucd90320, UcdGpi
from ..components.lm73 import Lm73
from ..components.max6581 import Max6581
from ..components.phy.babbagelp import BabbageLP
from ..components.psu.liteon import PS2242
from ..components.scd import Scd

from ..descs.gpio import GpioDesc
from ..descs.reset import ResetDesc
from ..descs.sensor import Position, SensorDesc

from .chassis.tuba import Tuba

from .cpu.lorikeet import LorikeetCpu

@registerPlatform()
class CatalinaP(FixedSystem):

   SID = ['CatalinaP']
   SKU = ['DCS-7060PX5-64S']

   CHASSIS = Tuba

   PHY = BabbageLP

   PORTS = PortLayout(
      osfps=incrange(1, 64),
      sfps=incrange(65, 66),
   )

   def __init__(self):
      super(CatalinaP, self).__init__()

      self.cpu = self.newComponent(LorikeetCpu)
      self.cpu.addCpuDpm()
      self.cpu.cpld.newComponent(Ucd90320, addr=self.cpu.switchDpmAddr(0x11),
                                 causes={
         'overtemp': UcdGpi(1),
         'powerloss': UcdGpi(3),
         'watchdog': UcdGpi(5),
         'reboot': UcdGpi(6),
      })
      # TODO sys cpld
      #self.syscpld = self.cpu.syscpld

      self.newComponent(Tomahawk4, addr=PciAddr(bus=0x04))

      scd = self.newComponent(Scd, addr=PciAddr(bus=0x01))
      self.scd = scd

      scd.createWatchdog()

      scd.newComponent(Max6581, addr=scd.i2cAddr(8, 0x4d), sensors=[
         SensorDesc(diode=0, name='Board sensor',
                    position=Position.OTHER, target=85, overheat=95, critical=105),
         SensorDesc(diode=1, name='Switch board middle sensor',
                    position=Position.OTHER, target=85, overheat=95, critical=105),
         SensorDesc(diode=2, name='Switch board left sensor',
                    position=Position.OTHER, target=85, overheat=95, critical=105),
         SensorDesc(diode=3, name='Front-panel temp sensor',
                    position=Position.INLET, target=85, overheat=95, critical=105),
         SensorDesc(diode=6, name='Switch chip diode 1 sensor',
                    position=Position.OTHER, target=85, overheat=95, critical=105),
         SensorDesc(diode=7, name='Switch chip diode 2 sensor',
                    position=Position.OTHER, target=85, overheat=95, critical=105),
      ])

      scd.newComponent(Lm73, self.scd.i2cAddr(13, 0x48), sensors=[
         SensorDesc(diode=0, name='Front-panel temp sensor',
                    position=Position.OTHER, target=65, overheat=75, critical=85),
      ])

      scd.addSmbusMasterRange(0x8000, 11, 0x80)

      scd.addLeds([
         (0x6050, 'status'),
         (0x6060, 'fan_status'),
         (0x6070, 'psu1'),
         (0x6080, 'psu2'),
         (0x6090, 'beacon'),
      ])

      scd.addResets([
         ResetDesc('phy3_reset', addr=0x4000, bit=7),
         ResetDesc('phy2_reset', addr=0x4000, bit=6),
         ResetDesc('phy1_reset', addr=0x4000, bit=5),
         ResetDesc('phy0_reset', addr=0x4000, bit=4),
         ResetDesc('switch_chip_pcie_reset', addr=0x4000, bit=3),
         ResetDesc('switch_chip_reset', addr=0x4000, bit=2),
      ])

      scd.addGpios([
         GpioDesc("psu1_present", 0x5000, 0, ro=True),
         GpioDesc("psu2_present", 0x5000, 1, ro=True),
         GpioDesc("psu1_status", 0x5000, 8, ro=True),
         GpioDesc("psu2_status", 0x5000, 9, ro=True),
         GpioDesc("psu1_ac_status", 0x5000, 10, ro=True),
         GpioDesc("psu2_ac_status", 0x5000, 11, ro=True),
      ])

      intrRegs = [
         scd.createInterrupt(addr=0x3000, num=0),
         scd.createInterrupt(addr=0x3030, num=1),
         scd.createInterrupt(addr=0x3060, num=2),
         scd.createInterrupt(addr=0x3090, num=3),
      ]

      scd.addOsfpSlotBlock(
         osfpRange=self.PORTS.osfpRange,
         addr=0xA000,
         bus=24,
         ledAddr=0x6100,
         ledAddrOffsetFn=lambda x: 0x10,
         intrRegs=intrRegs,
         intrRegIdxFn=lambda xcvrId: xcvrId // 33 + 1,
         intrBitFn=lambda xcvrId: (xcvrId - 1) % 32
      )

      scd.addSfpSlotBlock(
         sfpRange=self.PORTS.sfpRange,
         addr=0xA900,
         bus=88,
         ledAddr=0x6900,
         ledAddrOffsetFn=lambda x: 0x40
      )

      # PSU
      for psuId, bus in [(1, 12), (2, 11)]:
         addrFunc=lambda addr, bus=bus: \
                  scd.i2cAddr(bus, addr, t=3, datr=2, datw=3)
         name = "psu%d" % psuId
         scd.newComponent(
            PsuSlot,
            slotId=psuId,
            addrFunc=addrFunc,
            presentGpio=scd.inventory.getGpio("%s_present" % name),
            inputOkGpio=scd.inventory.getGpio("%s_ac_status" % name),
            outputOkGpio=scd.inventory.getGpio("%s_status" % name),
            led=scd.inventory.getLed('%s' % name),
            psus=[
               PS2242,
            ],
         )

      scd.addMdioMasterRange(0x9000, 4)

      for i in range(0, 4):
         phyId = i + 1
         reset = scd.inventory.getReset('phy%d_reset' % (i // 2))
         mdios = [scd.addMdio(i, 0), scd.addMdio(i, 1)]
         phy = self.PHY(phyId, mdios, reset=reset)
         self.inventory.addPhy(phy)

@registerPlatform()
class CatalinaDD(CatalinaP):
   SID = ['CatalinaDD']
   SKU = ['DCS-7060DX5-64S']