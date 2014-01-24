# Description:
#   NDB/Endpoints objects and brokering between them.

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
    oauth.ValidateUser(obj.key.id())
    return DistrictMessage(domain=obj.key.id())

  @classmethod
  def FromMessage(cls, msg):
    oauth.ValidateUser(msg.domain)
    v = District.get_by_id(msg.domain)
    if not v:
      if oauth.IsSuperUser():
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


class School(ndb.Model):
  """The database entry."""

  # name of the school is the id.
  @classmethod
  def ToMessage(cls, obj):
    # TODO(jimrenwick): This is probably a perf hit.
    oauth.ValidateUser(obj.parent().key.id())
    return SchoolMessage(
      district=obj.parent().key.id(), name=obj.key.id())

  @classmethod
  def FromMessage(cls, msg):
    oauth.ValidateUser(msg.district)
    d = District.get_by_id(msg.district)
    if not d:
      raise ValueError('Bad district')
    s = School.get_by_id(id=msg.name,
                         parent=ndb.Key(District, msg.district))
    if not s:
      if oauth.IsSuperUser():
        s = School(id=msg.name,
                   parent=ndb.Key(District, msg.district))
        s.put()
      else:
        raise ValueError('School does not exist.')
    return s

  @classmethod
  def All(cls):
    return cls.query()
