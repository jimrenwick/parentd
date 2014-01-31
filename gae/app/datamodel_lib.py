# Description:
#   NDB/Endpoints objects and brokering between them.

import endpoints
import logging
import os

from apiclient.discovery import build
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.db import BadArgumentError
from oauth2client.appengine import OAuth2DecoratorFromClientSecrets
from protorpc import messages
from protorpc import message_types
from protorpc import remote

import oauth


# Users.
class UserMessage(messages.Message):
  id = messages.StringField(1)
  email_addresses = messages.StringField(6, repeated=True)


class User(ndb.Model):
  """The database entry."""
  email_addresses = ndb.StringProperty(repeated=True)
  is_super_user = ndb.BooleanProperty(default=False)
  created_by = ndb.UserProperty(auto_current_user_add=True)

  @classmethod
  def ToMessage(cls, obj):
    return UserMessage(
      id=obj.key.urlsafe(),
      email_addresses=obj.email_addresses)

  @classmethod
  def FromMessage(cls, msg):
    oauth.ValidateUser(None, None)
    u = oauth.GetEndpointsUser()
    db_user = None
    changed = False
    if msg.id:
      db_user = ndb.Key(urlsafe=msg.id).get()
      if db_user.created_by.user_id != u.user_id():  # Authorized.
        raise endpoints.UnauthorizedException('Invalid Request.')
    else:  # New-user?
      db_user = User.Find()  # Email exists.
      if not db_user:  # Real-new request
        db_user = User(email_addresses=[u.email()])
        changed = True
    if msg.email_addresses and db_user.email_addresses != msg.email_addresses:
      changed = True
      db_user.email_addresses = msg.email_addresses
    # User's cannot make themselves super users.
    if changed:
      db_user.put()
    return db_user

  @classmethod
  def Find(cls, email=None):
    oauth.ValidateUser(None, None)
    current_user = oauth.GetEndpointsUser()
    is_super_user = False
    if email:  # Super user attempt
      admin = User.query(
        User.email_addresses == current_user.email()).fetch(1)[0]
      if not admin:
        return None
      else:
        is_super_user = admin.is_super_user
    else:
      email = current_user.email()
    q = User.query(User.email_addresses == email)
    for db_user in q:
      if is_super_user or db_user.created_by.user_id() == current_user.user_id():
        return db_user
    return None

  @classmethod
  def SetSuperUser(cls, user_email, val):
    oauth.ValidateUser(None, None)
    current_user = User.Find()
    if not current_user or not current_user.is_super_user:
      raise endpoints.UnauthorizedException('Not Allowed.')
    other_user = User.Find(email=user_email)
    other_user.is_super_user = val
    other_user.put()


# A District is also an NDB RootEntity for xg-Transactions.
class DistrictMessage(messages.Message):
  """The endpoints protorpc for a single db record."""
  domain = messages.StringField(1, required=True)


class DistrictCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(DistrictMessage, 1, repeated=True)


def DistrictCollectionMessageFromDistrict(objs):
  container = []
  for o in objs:
    container.append(District.ToMessage(o))
  return DistrictCollectionMessage(items=container)


class District(ndb.Model):
  """The district information."""

  # The key is the name of the district.

  @classmethod
  def ToMessage(cls, obj):
    return DistrictMessage(domain=obj.key.id())

  @classmethod
  def FromMessage(cls, msg):
    v = District.get_by_id(msg.domain)
    if not v:
      if oauth.IsSuperUser(User):
        v = District(id=msg.domain)
        v.put()
      else:
        raise ValueError('District does not exist.')
    return v

  @classmethod
  def All(cls):
    return cls.query()


# Schools are in Districts (via ancestors).
class SchoolMessage(messages.Message):
  district = messages.StringField(1, required=True)
  name = messages.StringField(2, required=True)


class SchoolCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(SchoolMessage, 1, repeated=True)


def SchoolCollectionMessageFromSchool(objs):
  container = []
  for o in objs:
    container.append(School.ToMessage(o))
  return SchoolCollectionMessage(items=container)


class SchoolCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(SchoolMessage, 1, repeated=True)


class School(ndb.Model):
  """The database entry."""

  # name of the school is the id.
  @classmethod
  def ToMessage(cls, obj):
    return SchoolMessage(
      district=obj.key.parent().id(), name=obj.key.id())

  @classmethod
  def FromMessage(cls, msg):
    oauth.ValidateUser(  # TODO(renwick): Port to SchoolUser
      School, ndb.Key(District, msg.district, School, msg.name))
    d = District.get_by_id(msg.district)
    if not d:
      raise ValueError('Bad district')
    s = School.get_by_id(id=msg.name,
                         parent=ndb.Key(District, msg.district))
    if not s:
      if oauth.IsSuperUser(User):
        s = School(id=msg.name,
                   parent=ndb.Key(District, msg.district))
        s.put()
      else:
        raise ValueError('School does not exist.')  # Opaque on purpose
    return s

  @classmethod
  def All(cls):
    return cls.query()


class SchoolUser(ndb.Model):
  """Relationship between Users and schools. These are managers."""
  pass


# TODO(renwick): Build the SchoolUser functionality.
class PersonMessage(messages.Message):
  id = messages.StringField(1)
  first_name = messages.StringField(3)
  last_name = messages.StringField(4)
  phone_numbers = messages.StringField(5, repeated=True)
  email_addresses = messages.StringField(6, repeated=True)
  addresses = messages.StringField(7, repeated=True)


class Person(ndb.Model):
  """The database entry."""
  first_name = ndb.StringProperty()
  last_name = ndb.StringProperty()
  phone_numbers = ndb.StringProperty(repeated=True)
  email_addresses = ndb.StringProperty(repeated=True)
  addresses = ndb.StringProperty(repeated=True)
  created_by = ndb.UserProperty(auto_current_user_add=True)

  @classmethod
  def ToMessage(cls, obj):
    return PersonMessage(
      id=obj.key.urlsafe(),
      first_name=obj.first_name,
      last_name=obj.last_name,
      phone_numbers=obj.phone_numbers,
      email_addresses=obj.email_addresses,
      addresses=obj.addresses)

  @classmethod
  def FromMessage(cls, msg):
    oauth.ValidateUser(None, None)
    changed = False
    person = None
    if msg.id:
      person = ndb.Key(urlsafe=msg.id).get()
    else:
      person = Person()
      changed = True
    if msg.first_name and person.first_name != msg.first_name:
      changed = True
      person.first_name = msg.first_name
    if msg.last_name and person.last_name != msg.last_name:
      changed = True
      person.last_name = msg.last_name
    if msg.phone_numbers and person.phone_numbers != msg.phone_numbers:
      changed = True
      person.phone_numbers = msg.phone_numbers
    if msg.email_addresses and person.email_addresses != msg.email_addresses:
      changed = True
      person.email_addresses = msg.email_addresses
    if msg.addresses and person.addresses != msg.addresses:
      changed = True
      person.addresses = msg.addresses
    # User's cannot make themselves super users.
    if changed:
      person.put()
    return person


class RecordMessage(messages.Message):
  id = messages.StringField(1)
  school = messages.MessageField(SchoolMessage, 2, required=True)
  parents = messages.MessageField(PersonMessage, 3, repeated=True)
  children = messages.MessageField(PersonMessage, 4, repeated=True)


class RecordCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(RecordMessage, 1, repeated=True)


def RecordCollectionMessageFromRecord(objs):
  container = []
  for o in objs:
    container.append(Record.ToMessage(o))
  return RecordCollectionMessage(items=container)


class RecordCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(RecordMessage, 1, repeated=True)


class Record(ndb.Model):
  school = ndb.KeyProperty(School, required=True)
  parents = ndb.KeyProperty(Person, repeated=True)
  children = ndb.KeyProperty(Person, repeated=True)
  created_by = ndb.UserProperty(auto_current_user_add=True)

  @classmethod
  def ToMessage(cls, obj):
    msg = RecordMessage(id=obj.key.urlsafe(), school=School.ToMessage(obj.school))
    parents = []
    for parent in obj.parents:
      parents.append(Person.ToMessage(parent))
    msg.parents = parents
    children = []
    for child in obj.children:
      children.append(Person.ToMessage(child))
    msg.children = children
    return msg

  @classmethod
  def FromMessage(cls, msg):
    oauth.ValidateUser(None, None)
    if msg.id:
      record = ndb.Key(urlsafe=msg.id).get()
    else:
      record = Record(
        school=School.FromMessage(msg.school).key,
        parents=[Person.FromMessage(p).key for p in msg.parents],
        children=[Person.FromMessage(p).key for p in msg.children])
      record.puts()
      return record
    if msg.school != record.school:
      record.school = msg.school
      changed = True
    if msg.parents:
      parents = [Person.FromMessage(p).key for p in msg.parents]
      if parents != record.parents:
        changed = True
        record.parents = parents
    if msg.children:
      children = [Person.FromMessage(p).key for p in msg.children]
      if children != record.children:
        changed = True
        record.children = children
    if changed:
      record.put()
    return record

  @classmethod
  def All(cls, school):
    return cls.query(Record.school == school)
