from datetime import timedelta
from experiments import Experiment


class Visitor(object):
  def __init__(self, experiment_id, number, time, variation_id):
    self._experiment_id = experiment_id
    self._id            = int(str(variation_id) + str(number))
    self._number        = number
    self._time          = time
    self._variation_id   = variation_id

  def format(self):
    return {
      'experiment_id': self._experiment_id,
      'id':            self._id,
      'number':        self._number,
      'time':          self._time,
      'variation':     self._variation_id
    }

  @property
  def experiment_id(self):
    return self._experiment_id

  @property
  def id(self):
    return self._id

  @property
  def number(self):
    return self._number

  @property
  def time(self):
    return self._time

  @property
  def variation_id(self):
    return self._variation_id


class VisitorCollection(Experiment):
  """Creates data for all visitors in the experiment."""
  def __init__(self, config, database):
    Experiment.__init__(self, config, database)

  def generate(self):
    """Entry point."""
    # If generate has already been called, make sure we have a clean slate.
    if self.data:
      self.data = []

    for variation_id in self.variation_ids:
        self.data += self.generate_visitors_for_variation(variation_id)

    return self.data

  def generate_visitors_for_variation(self, variation_id):
    data_array    = []
    visitor_total = self.visitors[variation_id]['total']

    for number in xrange(1, visitor_total):
      visitor = Visitor(experiment_id=self._experiment_id,
                        number=number,
                        time=self.get_visitor_timestamp(visitor_total, number),
                        variation_id=variation_id)

      data_array.append(visitor.format())

    return data_array

  def get_visitor_timestamp(self, visitor_total, visitor_number):
    """Evenly spread visitors through the life of the experiment."""
    delta_per_visitor = self.time['range'] / visitor_total
    delta             = delta_per_visitor * (visitor_number - 1)

    return (self.time['start'] + timedelta(seconds=delta)).\
            replace(microsecond=0)
