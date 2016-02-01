from datetime import datetime
from os.path import abspath, dirname
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, DateTime, Integer, ForeignKey, String


# Class from which all mapped classes should inherit
# http://docs.sqlalchemy.org/en/rel_0_9/orm/extensions/declarative.html
Base = declarative_base()


class EventTable(Base):
  """Holds one record for each event.
    Child of the Visitor table bound by foreign key (visitor_id).
  """
  __tablename__ = 'event'
  id         = Column(Integer, primary_key=True)
  visitor_id = Column(Integer, ForeignKey('visitor.id'))
  goal_ids   = Column(String(32))
  name       = Column(String(255))
  time       = Column(DateTime, default=datetime.now())
  revenue    = Column(Integer, default=0)


class SegmentTable(Base):
  """Holds one row for each segment a visitor belongs to.
    Child of the Visitor table bound by foreign key (visitor_id).
  """
  __tablename__ = 'segment'
  id         = Column(Integer, primary_key=True)
  visitor_id = Column(Integer, ForeignKey('visitor.id'))
  gae_id     = Column(Integer)
  value      = Column(String(32))


class VisitorTable(Base):
  __tablename__ = 'visitor'
  id            = Column(Integer, primary_key=True)
  number        = Column(Integer)
  experiment_id = Column(Integer)
  time          = Column(DateTime, default=datetime.now())
  variation     = Column(Integer)


class Database(object):
  """ Handles all logic for creating and maintaining local SQLite DB. """
  def __init__(self, db_name):
    self.db_name       = db_name
    self.db_file       = dirname(dirname(abspath(__file__))) + '/sql/' + str(db_name) + '.db'
    self.engine        = create_engine('sqlite://')# /' + self.db_file, echo=False)
    self.metadata      = Base.metadata
    self.metadata.bind = self.engine

  def create_tables(self):
    """Create all tables that inherit from Base."""
    self.metadata.drop_all(checkfirst=True)
    self.metadata.create_all(checkfirst=True)

  def insert(self, table, rows):
    """Calls the insert method for the table--available from Base."""
    if type(rows) is list and len(rows):
      self.engine.execute(
        table.__table__.insert(),
        rows
      )
