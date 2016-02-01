from database import EventTable, SegmentTable, VisitorTable

class Query(object):
  def __init__(self, database):
    self.database = database

    self.tables = {
      'event':         EventTable.__tablename__,
      'segment':       SegmentTable.__tablename__,
      'segment_temp1': 'SegmentAggregated',
      'segment_temp2': 'SegmentManual',
      'visitor':       VisitorTable.__tablename__
    }

  def execute(self, sql_statements):
    connection    = self.database.engine.connect()
    index_of_last = len(sql_statements) - 1
    return_array  = []

    for i, statement in enumerate(sql_statements):
      result = connection.execute(statement)

      if i == index_of_last:
        for row in result:
          return_array.append(row)

    connection.close()
    return return_array


class VisitorQuery(Query):
  def __init__(self, database):
    Query.__init__(self, database)

  def query_variation_ids(self):
    sql = '''SELECT DISTINCT v.variation
                FROM {} v'''.format(self.tables['visitor'])

    return [x[0] for x in self.execute(sql)]

  def query_visitor_count(self, variation_id):
    sql_statements = []

    sql_statements.append('''SELECT MAX(v.number) as number
                              FROM {} v
                              WHERE v.variation = {};'''.format(self.tables['visitor'],
                                                                variation_id))

    result = self.execute(sql_statements)

    return result[0]['number']

  def query_visitor_count_for_variation(self):
    sql_statements = []

    sql_statements.append('''SELECT v.variation,
                                    COUNT(*) as var_count
                              FROM {} v
                              GROUP BY variation'''.format(self.tables['visitor']))

    return self.execute(sql_statements)

  def query_visitors_for_baseline_events(self, variation_id, count):
    sql_statements = []

    sql_statements.append('''SELECT v.id,
                                    v.time
                              FROM {0} v
                              WHERE v.variation = {1}
                              ORDER BY RANDOM()
                              LIMIT {2}'''.format(self.tables['visitor'],
                                                 variation_id,
                                                 count))

    return self.execute(sql_statements)

  def query_visitors_for_distributed_events(self, goal_name, variation_id, count):
    sql_statements = []

    sql_statements.append('''SELECT v.id,
                                    v.time as visitor_time,
                                    e.time as event_time
                              FROM {} v
                              INNER JOIN {} e
                                ON v.id = e.visitor_id
                              WHERE e.name = "{}"
                                AND v.variation = {}
                              ORDER BY RANDOM()
                              LIMIT {}'''.format(self.tables['visitor'],
                                                 self.tables['event'],
                                                 goal_name,
                                                 variation_id,
                                                 count))

    return self.execute(sql_statements)

  def query_for_segment_default(self, segment_id, segment_count, variation_id):
    sql_statements = []

    sql_statements.append('''SELECT v.id
                              FROM {} v
                              LEFT JOIN (SELECT * FROM {} WHERE gae_id = {}) s
                                ON v.id = s.visitor_id
                              WHERE v.variation = {}
                                AND s.visitor_id IS NULL
                              ORDER BY RANDOM()
                              LIMIT {}'''.format(self.tables['visitor'],
                                                 self.tables['segment'],
                                                 segment_id,
                                                 variation_id,
                                                 segment_count))

    return self.execute(sql_statements)

  def query_for_segment_manual_conversions(self, segment_id, variation_id, goal_distribution):
    sql_statements = []

    sql_statements.append('''DROP TABLE IF EXISTS {}'''.format(self.tables['segment_temp2']))

    sql_statements.append('''CREATE TEMPORARY TABLE {} (
                              id INT NOT NULL
                              )'''.format(self.tables['segment_temp2']))

    for goal_id, conversion_count in goal_distribution.iteritems():
      sql_statements.append('''INSERT INTO {} (id)
                                SELECT v.id
                                FROM {} v
                                INNER JOIN {} e
                                  ON v.id = e.visitor_id
                                LEFT JOIN (SELECT * FROM {} WHERE gae_id = {}) s
                                  ON v.id = s.visitor_id
                                WHERE e.goal_ids LIKE '%{}%'
                                  AND v.variation = {}
                                  AND s.visitor_id IS NULL
                                ORDER BY RANDOM()
                                LIMIT {}'''.format(self.tables['segment_temp2'],
                                                   self.tables['visitor'],
                                                   self.tables['event'],
                                                   self.tables['segment'],
                                                   segment_id,
                                                   goal_id,
                                                   variation_id,
                                                   conversion_count))

    sql_statements.append('''SELECT DISTINCT id FROM {}'''.format(self.tables['segment_temp2']))

    return self.execute(sql_statements)

  def query_for_segment_manual_bounce(self, segment_id, variation_id, count):
    sql_statements = []

    sql_statements.append('''SELECT v.id
                                FROM {} v
                                LEFT JOIN {} e
                                  ON v.id = e.visitor_id
                                LEFT JOIN (SELECT * FROM {} WHERE gae_id = {}) s
                                  ON v.id = s.visitor_id
                                WHERE e.visitor_id IS NULL
                                  AND s.visitor_id IS NULL
                                  AND v.variation = {}
                              LIMIT {}'''.format(self.tables['visitor'],
                                                 self.tables['event'],
                                                 self.tables['segment'],
                                                 segment_id,
                                                 variation_id,
                                                 count))

    return self.execute(sql_statements)


class EventQuery(Query):
  def __init__(self, database):
    Query.__init__(self, database)

  def query_event_names(self):
    sql_statements = []

    sql_statements.append('''SELECT DISTINCT e.name
                              FROM {} e'''.format(self.tables['event']))

    return self.execute(sql_statements)


class SegmentQuery(Query):
  def __init__(self, database):
    Query.__init__(self, database)

  def query_segment_ids(self):
    sql_statements = []

    sql_statements.append('''SELECT DISTINCT s.gae_id
                              FROM {} s'''.format(self.tables['segment']))

    return [x[0] for x in self.execute(sql_statements)]

  def query_segment_count_for_variation(self, variation_id, gae_id):
    sql_statements = []

    sql_statements.append('''SELECT COUNT(DISTINCT visitor_id) as count
                              FROM {} s
                              INNER JOIN {} v
                                ON s.visitor_id = v.id
                              WHERE s.gae_id = {}
                                AND v.variation = {}
                              GROUP BY s.gae_id, v.variation'''.format(self.tables['segment'],
                                                                       self.tables['visitor'],
                                                                       gae_id,
                                                                       variation_id))

    return self.execute(sql_statements)[0]['count']

class APIQuery(Query):
  def __init__(self, database):
    Query.__init__(self, database)

  @staticmethod
  def transpose_segments(segment_ids, table_prefix="", trailing_comma=True):
    sql_snippet = ''

    for segment_id in segment_ids:
      sql_case = '''ifnull(group_concat(case when {1}.gae_id = {0}
                                      then {1}.value
                                      else NULL
                                      end, ""), "false") as s{0},'''.format(segment_id,
                                                                        table_prefix)

      sql_snippet += sql_case

    if not trailing_comma:
      sql_snippet = sql_snippet[0:(len(sql_snippet)-1)]

    return sql_snippet

  def query_conversion_data(self, segment_ids):
    sql_statements = []

    sql_statements.append('''CREATE TEMPORARY TABLE {} AS
                              SELECT visitor_id,
                                    {}
                              FROM {} s
                              GROUP BY visitor_id;'''.format(self.tables['segment_temp1'],
                                                             self.transpose_segments(segment_ids,
                                                                                      table_prefix="s",
                                                                                      trailing_comma=False),
                                                             self.tables['segment']))

    sql_statements.append('''SELECT v.id as u,
                                    v.variation as variation_id,
                                    v.experiment_id as x,
                                    s.*,
                                    e.time as t,
                                    e.name as n,
                                    e.goal_ids as g,
                                    e.revenue as v
                              FROM {} v
                              LEFT JOIN {} s
                                ON v.id = s.visitor_id
                              INNER JOIN {} e
                                ON v.id = e.visitor_id
                              GROUP BY v.id, v.variation, v.experiment_id, e.time,
                                    e.name, e.goal_ids, e.revenue;'''.format(self.tables['visitor'],
                                                                             self.tables['segment_temp1'],
                                                                             self.tables['event']))

    return self.execute(sql_statements)

  def query_visitor_data(self, segment_ids):
    sql_statements = []

    sql_statements.append('''SELECT v.id as u,
                                    v.variation as variation_id,
                                    v.experiment_id as x,
                                    {}
                                    v.time as t,
                                    'register' as n,
                                    v.experiment_id as g,
                                    0 as v
                                FROM {} v
                                LEFT JOIN {} s
                                  ON v.id = s.visitor_id
                                GROUP BY v.id, v.variation, v.experiment_id, v.time,
                                      n, g, v'''.format(self.transpose_segments(segment_ids, table_prefix="s"),
                                                        self.tables['visitor'],
                                                        self.tables['segment']))

    return self.execute(sql_statements)
