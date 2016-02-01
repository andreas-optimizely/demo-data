from database import SegmentTable
from experiments import Experiment

import math


class Segment(object):
  def __init__(self, visitor_id, gae_id, value):
    self._gae_id     = gae_id
    self._value      = value
    self._visitor_id = visitor_id

  def format(self):
    if self._value == 0:
      formatted_value = 'false'
    elif self._value == 1:
      formatted_value = 'true'
    else:
      formatted_value = self._value

    return {
      'visitor_id': self._visitor_id,
      'gae_id':     self._gae_id,
      'value':      formatted_value
    }

  @property
  def gae_id(self):
    return self._gae_id

  @property
  def value(self):
    return self._value

  @property
  def visitor_id(self):
    return self._visitor_id

class SegmentCollection(Experiment):
  def __init__(self, config, database):
    Experiment.__init__(self, config, database)

    self._database = database

  @property
  def database(self):
    return self._database

  def generate(self):
    for segment_id in self.segments['default']:
      self.generate_default(segment_id)

    if 'manual' in self.segments:
      for segment_id, segment_distribution in self.segments['manual'].iteritems():
        self.generate_manual(segment_id, segment_distribution)

  def generate_default(self, segment_id):
    for segment_value, ratio in self.segments['default'][segment_id].iteritems():
      visitors = self.get_visitors_for_segment_value(segment_id, ratio)
      segments = self.get_segments(segment_id, segment_value, visitors)

      self.insert_segments(segments)

  def generate_manual(self, segment_id, segment_dist):
    for segment_value, segment_value_dist in segment_dist.iteritems():
      for variation_id, variation_dist in segment_value_dist.iteritems():
        self.generate_manual_conversions(segment_id, segment_value, variation_id, variation_dist)
        self.generate_manual_bounces(segment_id, segment_value, variation_id, variation_dist)

  def generate_manual_bounces(self, segment_id, segment_value, variation_id, variation_dist):
    conversion_total_count = self.query['segment'].query_segment_count_for_variation(variation_id, segment_id)
    bounce_count = variation_dist['total'] - conversion_total_count

    if bounce_count > 0:
      bounce_visitors = self.query['visitor'].query_for_segment_manual_bounce(segment_id,
                                                                              variation_id,
                                                                              bounce_count)

      bounce_segments = self.get_segments(segment_id, segment_value, bounce_visitors)

      self.insert_segments(bounce_segments)

  def generate_manual_conversions(self, segment_id, segment_value, variation_id, variation_dist):
    conversion_visitors = self.query['visitor'].query_for_segment_manual_conversions(segment_id,
                                                                                     variation_id,
                                                                                     variation_dist['conversions'])

    conversion_segments = self.get_segments(segment_id, segment_value, conversion_visitors)

    self.insert_segments(conversion_segments)

  @staticmethod
  def get_segments(segment_id, segment_value, visitors):
    segments = []

    for visitor in visitors:
      segment = Segment(visitor['id'], segment_id, segment_value)
      segments.append(segment.format())

    return segments

  def get_visitors_for_segment_value(self, segment_id, ratio):
    visitors = []

    for variation_id, distribution in self.visitors.iteritems():
      segment_count          = math.ceil(distribution['total'] * ratio)
      visitors_for_variation = self.query['visitor'].query_for_segment_default(segment_id,
                                                                             segment_count,
                                                                             variation_id)

      visitors += visitors_for_variation

    return visitors

  def insert_segments(self, segments):
    self.database.insert(SegmentTable, segments)
    self.data += segments
