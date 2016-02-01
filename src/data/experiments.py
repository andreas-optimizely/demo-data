from datetime import datetime
from query import EventQuery, SegmentQuery, VisitorQuery

class Experiment(object):
  data = []

  def __init__(self, config, database):
    """
    :param : conversions (dict)
    :param : goal_ids (list<int>)
    :param : id (integer)
    :param : time.start (datetime)
    :param : time.stop (datetime)
    :param : time.range (integer)
    :param : variation_ids (list<int>)
    :param : variations (dict)

    """
    self._conversions   = config['conversions']
    self._experiment_id = config['experiment']['id']
    self._goal_ids      = config['goal_ids']
    self._segment_ids   = config['segment_ids']
    self._segments      = config['segments']
    self._variation_ids = config['variation_ids']
    self._visitors      = config['visitors']

    self._query = {
      'event':   EventQuery(database),
      'segment': SegmentQuery(database),
      'visitor': VisitorQuery(database)
    }

    # TODO(Brendan): auto defined stop as UTC NOW.
    self._time = {
      'start': datetime.strptime(config['experiment']['start'],'%Y-%m-%dT%H:%M:%SZ'),
      'stop':  datetime.strptime(config['experiment']['stop'],'%Y-%m-%dT%H:%M:%SZ')
    }

    self._time['range'] = (self._time['stop'] - self._time['start']).total_seconds()

  @property
  def conversions(self):
    return self._conversions

  @property
  def experiment_id(self):
    return self._experiment_id

  @property
  def goal_ids(self):
    return self._goal_ids

  @property
  def query(self):
    return self._query

  @property
  def segment_ids(self):
    return self._segment_ids

  @property
  def segments(self):
    return self._segments

  @property
  def variation_ids(self):
    return self._variation_ids

  @property
  def visitors(self):
    return self._visitors

  @property
  def time(self):
    return self._time
