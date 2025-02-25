
from .component import Priority
from .component.slot import SlotComponent
from .config import Config
from .exception import UnknownPlatformError
from .inventory import Inventory
from .log import getLogger
from .metainventory import MetaInventory
from .platform import getPlatformCls
from .sku import Sku

logging = getLogger(__name__)

class Card(Sku):

   CPU_CLS = None
   ABSOLUTE_CARD_OFFSET = 0

   def __init__(self, slot=None, standbyOnly=False, noStandby=False, **kwargs):
      self.slot = slot
      self.standby = None
      self.main = None
      self.cpu = None
      super(Card, self).__init__(inventory=Inventory(), **kwargs)
      if slot:
         if not noStandby:
            self.loadStandbyDomain()
         if not standbyOnly:
            self.loadMainDomain()
      else:
         self.loadCpuDomain()

   def getInventory(self):
      if Config().use_metainventory:
         return MetaInventory(self.iterInventory())
      return self.inventory

   def getSlotId(self):
      return self.slot.slotId

   def getRelativeSlotId(self):
      return self.slot.slotId - self.ABSOLUTE_CARD_OFFSET

   def getPresence(self):
      return self.slot.getPresence()

   def loadStandbyDomain(self):
      raise NotImplementedError

   def loadMainDomain(self):
      raise NotImplementedError

   def loadCpuDomain(self):
      raise NotImplementedError

   def powerOnIs(self, on, lcpuCtx=None):
      raise NotImplementedError

   def poweredOn(self):
      raise NotImplementedError

   def hasCpuModule(self):
      return self.CPU_CLS is not None

   def updateAsicAddr(self):
      pass

   def setup(self, filters=Priority.defaultFilter):
      super(Card, self).setup()
      super(Card, self).finish(filters=filters)

   def setupStandby(self, filters=Priority.defaultFilter):
      self.standby.setup()
      self.standby.finish(filters)

   def setupMain(self, filters=Priority.defaultFilter):
      self.main.setup()
      self.main.finish(filters)

   def __str__(self):
      if self.slot.parent is self:
         return '%s()' % self.__class__.__name__
      else:
         return '%s(slotId=%d)' % (self.__class__.__name__, self.slot.slotId)

class CardSlot(SlotComponent):
   def __init__(self, parent, slotId):
      super(CardSlot, self).__init__()
      self.slotId = slotId
      self.parent = parent
      self.card = None

   def getEeprom(self):
      raise NotImplementedError

   def disablePciPort(self):
      self.parent.pciSwitch.disable(self.slotId)

   def enablePciPort(self):
      self.parent.pciSwitch.enable(self.slotId)

   def loadCard(self, card=None, **kwargs):
      if card is None:
         assert self.card, "No default card definition loaded"
         if not self.getPresence():
            logging.debug('Card slot %d is not present', self.slotId)
            return

         eeprom = self.getEeprom()
         sid = eeprom.get('SID')
         if sid is None:
            logging.error('Unknown card in slot %d, eeprom is invalid', self.slotId)
            return

         try:
            cls = getPlatformCls(sid)
            # add some Config() for noStandby
            logging.debug('Loading card %s in slot %d', cls.__name__, self.slotId)
            card = cls(self, **kwargs)
         except UnknownPlatformError:
            logging.debug('Unsupported card %s for slot %d', sid, self.slotId)
            return

      self.card = card
      self.card.refresh()

   def genDiag(self, ctx):
      data = super(CardSlot, self).genDiag(ctx)
      try:
         eeprom = self.getEeprom() if ctx.performIo else None
      except Exception: # pylint: disable=broad-except
         eeprom = {}
      data.update({
         'eeprom': eeprom,
         'present': self.getPresence(),
         'slotId': self.slotId,
         'card': self.card.genDiag(ctx) if self.card else None,
      })
      return data
