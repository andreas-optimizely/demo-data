from __future__ import division
from datetime import datetime
from eventlet.green import urllib2
from httplib import BadStatusLine
from interface import progress_bar

import eventlet
import re
import urllib


class APIImport(object):
  errors   = 0
  pause    = 5
  pool     = eventlet.GreenPool(size=10)
  url_base = 'http://{}.log.optimizely.com/v1/offline/event'

  regex = {
    'experiment': '^x(\d+)$',
    'segment':    '^s(\d+)$'
  }

  def __init__(self, account_id, admin_id):
    self.credentials = {
      'account_id': account_id,
      'admin_id':   admin_id
    }

    self.env = {
      'url': self.url_base.format(account_id)
    }

  def format_event(self, event):
    formatted_event = {
      'a':     self.credentials['account_id'],
      'd':     self.credentials['admin_id'],
      'f':     self.format_event_experiment_ids(event['x']),
      'g':     self.format_event_goal_ids(event['g']),
      'n':     self.format_event_name(event['n']),
      'time':  self.format_event_time(event['t']),
      'tsent': self.format_event_tsent(),
      'u':     self.format_event_user_id(event['u']),
      'v':     self.format_event_revenue(event['v']),
      'wxhr':  'true',
      'y':     'false'
    }

    # Dynamically set the bucket key (x12345={{variation_id}})
    bucket_key = 'x{}'.format(event['x'])
    formatted_event[bucket_key] = event['variation_id']

    # There can be any number of segments, need to dynamically set the keys
    for key in event.keys():
      if re.match(self.regex['segment'], str(key)):
        formatted_event[key] = event[key]

    return formatted_event

  @staticmethod
  def format_event_experiment_ids(experiment_id):
    return str(experiment_id)

  @staticmethod
  def format_event_goal_ids(goal_ids):
    formatted_goals = ','.join(goal_ids) if type(goal_ids) is list else str(goal_ids)
    return formatted_goals

  @staticmethod
  def format_event_name(name):
    return str(name)

  @staticmethod
  def format_event_revenue(revenue):
    return int(revenue)

  # TODO(brendan): split out time logic
  @staticmethod
  def format_event_time(event_time):
    epoch          = datetime.utcfromtimestamp(0)
    event_datetime = datetime.strptime(event_time, '%Y-%m-%d %H:%M:%S.%f').replace(microsecond=0)
    delta          = event_datetime - epoch

    return int(delta.total_seconds())

  # TODO(brendan): split out time logic
  @staticmethod
  def format_event_tsent():
    epoch          = datetime.utcfromtimestamp(0)
    event_datetime = datetime.utcnow()
    delta          = event_datetime - epoch

    return int(delta.total_seconds())

  @staticmethod
  def format_event_user_id(user_id):
    return 'oeu' + str(user_id)

  def send(self, events, title='Sending events'):
    # Initialize progress bar
    events_count = len(events)
    events_sent  = 0
    warning      = ''

    progress_bar(title, 0, warning)

    for event in events:
      self.pool.spawn(self.send_event,
                      self.format_event(event))

      events_sent += 1

      if events_sent % 1000 == 0:
        progress_bar(title, (events_sent / events_count), warning)

      if self.errors > 10:
        warning = 'High error rate!'


    progress_bar(title, 1, warning)

  def send_event(self, event):
    try:
      url = '?'.join([self.env['url'], urllib.urlencode(event)])
      urllib2.urlopen(url)
    except BadStatusLine, urllib2.HTTPError:
      self.errors += 1
