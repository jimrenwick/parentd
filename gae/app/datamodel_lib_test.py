# Description:
#   unittests for datamodel_lib.py

import endpoints
import unittest

from google.appengine.ext import ndb
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

import datamodel_lib


def _SetUser(testbed, email, user_id):
  testbed.setup_env(
    USER_EMAIL=email, USER_ID=user_id, USER_IS_ADMIN='0',
    ENDPOINTS_USE_OAUTH_SCOPE='0', ENDPOINTS_AUTH_EMAIL=email,
    ENDPOINTS_AUTH_DOMAIN=email.split('@')[-1],
    OAUTH_ERROR_CODE='', OAUTH_LAST_SCOPE='0',
    AUTH_DOMAIN=email.split('@')[-1],
    OAUTH_EMAIL=email, OAUTH_AUTH_DOMAIN=email.split('@')[-1],
    OAUTH_USER_ID=user_id, overwrite=True)


class DistrictTest(unittest.TestCase):

  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()
    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()
    # Next, declare which service stubs you want to use.
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()
    _SetUser(self.testbed, 'admin@parentd.com', '8888')
    self.testbed.init_user_stub()
    # Set admin for these tests.
    datamodel_lib.User(email_addresses=['admin@parentd.com'],
                       is_super_user=True).put()

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

  def testNonSuperCannotCreate(self):
    _SetUser(self.testbed, 'joe@parentd.com', '1234')
    msg = datamodel_lib.DistrictMessage(domain='domain.org')
    self.assertRaises(ValueError, datamodel_lib.District.FromMessage, msg)


class SchoolTest(unittest.TestCase):

  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()
    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()
    # Create a consistency policy that will simulate the High
    # Replication consistency model.
    self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
    # Initialize the datastore stub with this policy.
    self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
    self.testbed.init_memcache_stub()
    _SetUser(self.testbed, 'joe@parentd.com', '1234')
    self.testbed.init_user_stub()
    # Make joe admin for these tests.
    datamodel_lib.User(email_addresses=['joe@parentd.com'],
                       is_super_user=True).put()
    datamodel_lib.District.FromMessage(
      datamodel_lib.DistrictMessage(domain='test.org'))

  def tearDown(self):
    self.testbed.deactivate()

  def testSchoolFromMessage(self):
    msg = datamodel_lib.SchoolMessage(district='test.org', name='test')
    ndb = datamodel_lib.School.FromMessage(msg)
    self.assertEquals('test', ndb.key.id())
    self.assertEquals('test.org', ndb.key.parent().id())
    new_msg = datamodel_lib.School.ToMessage(ndb)
    self.assertEquals(new_msg, msg)

  def testNonSuperCannotCreate(self):
    _SetUser(self.testbed, 'sam@parentd.com', '5678')
    msg = datamodel_lib.SchoolMessage(district='test.org', name='test')
    self.assertRaises(ValueError, datamodel_lib.School.FromMessage, msg)


class UserTest(unittest.TestCase):

  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()
    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()
    # Create a consistency policy that will simulate the High
    # Replication consistency model.
    self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
    # Initialize the datastore stub with this policy.
    self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
    self.testbed.init_memcache_stub()
    _SetUser(self.testbed, 'admin@parentd.com', '8888')
    self.testbed.init_user_stub()
    datamodel_lib.User(email_addresses=['admin@parentd.com'],
                       is_super_user=True).put()

  def tearDown(self):
    self.testbed.deactivate()

  def testToMessage(self):
    _SetUser(self.testbed, 'joe@parentd.com', '1234')
    msg = datamodel_lib.UserMessage(email_addresses=['joe@parentd.com'])
    obj = datamodel_lib.User.FromMessage(msg)
    self.assertEquals(['joe@parentd.com'], obj.email_addresses)
    self.assertEquals('joe@parentd.com', obj.created_by.email())
    self.assertEquals('1234', obj.created_by.user_id())
    self.assertFalse(obj.is_super_user)
    final_msg = datamodel_lib.User.ToMessage(obj)
    self.assertEquals(obj.key.urlsafe(), final_msg.id)

  def testCheckAdminSuper(self):
    # Validate admin.
    _SetUser(self.testbed, 'admin@parentd.com', '8888')
    admin = datamodel_lib.User.Find(email='admin@parentd.com')
    self.assertTrue(admin.is_super_user)
    # Create joe.
    _SetUser(self.testbed, 'joe@parentd.com', '1234')
    msg = datamodel_lib.UserMessage(email_addresses=['joe@parentd.com'])
    joe = datamodel_lib.User.FromMessage(msg)
    self.assertEquals('1234', joe.created_by.user_id())
    # Joe can't set super
    self.assertRaises(endpoints.UnauthorizedException,
                      datamodel_lib.User.SetSuperUser, 'joe@parentd.com', True)
    # But admin can.
    _SetUser(self.testbed, 'admin@parentd.com', '8888')
    datamodel_lib.User.SetSuperUser('joe@parentd.com', True)
    joe = datamodel_lib.User.Find(email='joe@parentd.com')
    self.assertTrue(joe.is_super_user)


class PersonTest(unittest.TestCase):

  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()
    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()
    # Create a consistency policy that will simulate the High
    # Replication consistency model.
    self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
    # Initialize the datastore stub with this policy.
    self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
    self.testbed.init_memcache_stub()
    _SetUser(self.testbed, 'admin@parentd.com', '8888')
    self.testbed.init_user_stub()
    self.super = datamodel_lib.Person(first_name='super', last_name='admin',
                                      email_addresses=['admin@parentd.com']).put()

  def tearDown(self):
    self.testbed.deactivate()

  def testFromMessage(self):
    msg = datamodel_lib.PersonMessage(first_name='first',
                                      last_name='last',
                                      phone_numbers=['123-456-7890'],
                                      email_addresses=['joe@parentd.com'])
    obj = datamodel_lib.Person.FromMessage(msg)
    self.assertEquals('first', obj.first_name)
    self.assertEquals('last', obj.last_name)
    self.assertEquals(['123-456-7890'], obj.phone_numbers)
    self.assertEquals(['joe@parentd.com'], obj.email_addresses)

  def testToMessage(self):
    msg = datamodel_lib.Person.ToMessage(self.super.get())
    self.assertEquals('super', msg.first_name)
    self.assertEquals('admin', msg.last_name)
    self.assertEquals(['admin@parentd.com'], msg.email_addresses)
    self.assertEquals([], msg.phone_numbers)

  def changedData(self):
    obj = self.super.get()
    self.assertTrue(obj.phone_numbers is None)
    msg = datamodel_lib.Person.ToMessage(obj)
    msg.phone_numbers = ['987-678-9876']
    obj = datamodel_lib.Person.FromMessage(msg)
    self.assertEquals(['987-678-9876'], obj.phone_numbers)


# TODO(renwick): Record Testcase needed.


if __name__ == '__main__':
  unittest.main()
