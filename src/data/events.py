from __future__ import division
from datetime import datetime, timedelta
from experiments import Experiment

import math
import random


class Event(object):
  def __init__(self, goal_ids, name, time, visitor_id, revenue_data=None):
    self._goal_ids   = goal_ids
    self._name       = name
    self._time       = time
    self._visitor_id = visitor_id
    self._revenue    = self.get_revenue_amount(revenue_data) if revenue_data else 0

  def format(self):
    return {
      'goal_ids':   self._goal_ids,
      'name':       self._name,
      'time':       self._time,
      'visitor_id': self._visitor_id,
      'revenue':    self._revenue
    }

  @staticmethod
  def get_revenue_amount(revenue_data):
    """Using gamma distribution: http://en.wikipedia.org/wiki/Gamma_distribution

    :arg : alpha (int): Shape parameter
    :arg : beta (int): Scale parameter
    """
    pdf_value = random.gammavariate(revenue_data['alpha'], revenue_data['beta'])

    return int(math.floor(pdf_value * 100))

  @property
  def goal_ids(self):
    return self._goal_ids

  @property
  def name(self):
    return self._name

  @property
  def time(self):
    return self._time

  @property
  def visitor_id(self):
    return self._visitor_id

  @property
  def revenue(self):
    return self._revenue


class EventCollection(Experiment):
  """Base class for generating lists of Events. Super class for each special Event list type.
    You must inherit from this class and define self.get_events(). It will throw a NotImplementedError
    if you call this class directly.
  """
  def __init__(self, config, database):
    Experiment.__init__(self, config, database)

  def generate(self):
    """Entry point"""
    if self.data:
      self.data = []

    for goal_name, goal_data in self.conversions.iteritems():
      goal_ids = ','.join(str(x) for x in goal_data['goal_ids'])

      for variation_id, conversion_data in goal_data['counts'].iteritems():
        events     = self.get_events(conversion_data, goal_ids, goal_name, variation_id)
        self.data += events

    return self.data

  def get_events(self, conversion_data, goal_ids, goal_name, variation_id):
    raise NotImplementedError('Must use BaselineEvents or DistributedEvents to generate data.')

  @property
  def query(self):
    return self._query


class BaselineEventCollection(EventCollection):
  """ Handles creating first events for visitors who converted *at least* once."""
  def __init__(self, config, database):
    EventCollection.__init__(self, config, database)

  def get_events(self, conversion_data, goal_ids, event_name, variation_id):
    """ For each goal/variaton, return a list of events for every visitor who converted at least once."""
    events       = []
    events_count = conversion_data['unique']
    visitors     = self.query['visitor'].query_visitors_for_baseline_events(variation_id, events_count)

    for visitor in visitors:
      event_time = self.get_event_time(visitor['time'])

      event = Event(goal_ids=goal_ids,
                    name=event_name,
                    revenue_data=conversion_data['revenue'] if 'revenue' in conversion_data else None,
                    time=event_time,
                    visitor_id=visitor['id'])

      events.append(event.format())

    return events

  @staticmethod
  def get_event_time(visitor_time):
    """Baseline events should occur at the initial time of the visitor."""
    return datetime.strptime(visitor_time, '%Y-%m-%d %H:%M:%S.%f').replace(microsecond=0)


class DistributedEventCollection(EventCollection):
  def __init__(self, config, database):
    EventCollection.__init__(self, config, database)

  # TODO: Update to handle conversions > 2 per visitor.
  def get_events(self, conversion_data, goal_ids, event_name, variation_id):
    """For each goal/variation, add additional events to previously converted visitors."""
    if conversion_data['total'] < conversion_data['unique']:
      return None

    events       = []
    events_count = conversion_data['total'] - conversion_data['unique']
    visitors     = self.query['visitor'].query_visitors_for_distributed_events(event_name, variation_id, events_count)

    for visitor in visitors:
      event_time = self.get_event_time(visitor['event_time'])

      event = Event(goal_ids=goal_ids,
                    name=event_name,
                    revenue_data=conversion_data['revenue'] if 'revenue' in conversion_data else None,
                    time=event_time,
                    visitor_id=visitor['id'])

      events.append(event.format())

    return events

  @staticmethod
  def get_event_time(event_time):
    """Front loaded gamma distriubuution between visitor time and end of experiment."""
    event_datetime  = datetime.strptime(event_time, '%Y-%m-%d %H:%M:%S.%f')

    distribution_average = 12
    distribution_shape   = 2
    distribution_scale   = int(distribution_average / distribution_shape)

    pdf_value = random.gammavariate(distribution_shape, distribution_scale)

    return (event_datetime + timedelta(hours=pdf_value)).replace(microsecond=0)
