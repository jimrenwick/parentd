# Description:
#   unittests for datamodel_lib.py

import unittest

from google.appengine.ext import ndb
from google.appengine.ext import testbed

import datamodel_lib


class DistrictTest(unittest.TestCase):

  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()
    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()
    # Next, declare which service stubs you want to use.
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()
    self.testbed.setup_env(
      USER_EMAIL='joe@parentd.com', USER_ID='1234', USER_IS_ADMIN='0',
      overwrite=True)
    self.testbed.init_user_stub()

  def tearDown(self):
    self.testbed.deactivate()

  def testDistrictToMessage(self):
    msg = datamodel_lib.DistrictMessage(domain='domain.org')
    ndb = datamodel_lib.District.FromMessage(msg)
    self.assertEquals('domain.org', ndb.key.id())
    msg = datamodel_lib.District.ToMessage(ndb)
    self.assertEquals('domain.org', msg.domain)

  def testDistrictCollection(self):
    for i in xrange(5):
      msg = datamodel_lib.DistrictMessage(domain='domain-%s.org' % (i))
      ndb = datamodel_lib.District.FromMessage(msg)
    col = datamodel_lib.DistrictCollectionMessageFromDistrict(
      datamodel_lib.District.All())
    self.assertEquals(5, len(col.items))
    for i, item in enumerate(col.items):
      self.assertEquals('domain-%s.org' % (i), item.domain)


class SchoolTest(unittest.TestCase):

  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()
    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()
    # Next, declare which service stubs you want to use.
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()
    self.testbed.setup_env(
      USER_EMAIL='joe@parentd.com', USER_ID='1234', USER_IS_ADMIN='0',
      overwrite=True)
    self.testbed.init_user_stub()

  def tearDown(self):
    self.testbed.deactivate()
