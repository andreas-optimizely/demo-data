""" This is the main entry point for the script to create example results pages in Optimizely.

This is a test for Connor.

How to run this bad-boy:

  1. Create a skeleton experiment with all Variations, Goals, Segments on Optimizely.
    a. TODO: Make this automated with the REST API

  2. Create a configuration YAML file to inform the program. An example can be found in
    ./optimizely-fake-data/config/web/travel.yaml

    This includes:

      a. All of the necessary backend information
        i. Experiment Id
        ii. Variation Ids
        iii. Goal Ids
        iv. Segment Ids and Values

      b. Distribution characteristics (how we want the data to look).
        i. Total visitors
        ii. Goal conversion counts
        iii. Revenue amounts
        iv. Retention timelines

  3. Run the program passing the YAML file as an argument, using the included Python Virtual Environment.

    From the ./optimizely-fake-data directory

      source .venv/bin/activate
      python ./src/main.py -c ./config/web/travel.yaml

    Note: See main() for additional parameters.

  4. Check your results page for results. With the new Hadoop backend, data should start coming through pretty fast.

An overview of the program execution:

  [x] Main.py
   |
   |-database.py-- Initialize a local SQLite database
   | |
   |-|-visitor.py-- Insert one record for each visitor to "visitor" table with variaton_id and timestamp.
   | |
   |-|-event.py-- Insert one record per conversion event to "event" table. Events have a FK to visitor.visitor_id
   | |
   |-|-segment.py-- Assign segments to visitors via "segment" table. Segments have a FK to visitor.visitor_id.
   |
   |-query.py-- Handles all queries necessary against database tables. Both for data population and sending via api.py
   |
   |-api.py-- Format the data and GET {{project_id}}.log.optimizely.com/event (uses Eventlet lib).

"""

from data.api import APIImport
from data.database import Database, EventTable, VisitorTable
from data.events import BaselineEventCollection, DistributedEventCollection
from data.query import APIQuery
from data.segments import SegmentCollection
from data.visitors import VisitorCollection

import argparse
import logging
import sys
import yaml


def create_baseline_events(config, database):
  baseline_events = BaselineEventCollection(config, database)
  baseline_events.generate()

  database.insert(EventTable, baseline_events.data)
  logging.info('Baseline events generated.')


def create_database(name):
  database = Database(name)
  database.create_tables()

  logging.info('Database created.')

  return database


def create_distributed_events(config, database):
  distributed_events      = DistributedEventCollection(config, database)
  distributed_events_data = distributed_events.generate()

  database.insert(EventTable, distributed_events_data)
  logging.info('Distributed events generated.')


def create_segments(config, database):
  segments = SegmentCollection(config, database)
  segments.generate()

  logging.info('Segments generated.')


def create_visitors(config, database):
  visitors      = VisitorCollection(config, database)
  visitors_data = visitors.generate()

  database.insert(VisitorTable, visitors_data)
  logging.info('Visitors generated.')


def get_config(config_path):
  try:
    config = yaml.load(file(config_path, 'r'))
  except IOError:
    print 'Invalid path to config file.'
    sys.exit(0)

  logging.info('Config loaded.')
  return config


def send_events(config, database):
  api_import = APIImport(config['account']['id'],
                         config['account']['admin_id'])

  api_query  = APIQuery(database)

  conversion_events = api_query.query_conversion_data(config['segment_ids'])
  visitor_events    = api_query.query_visitor_data(config['segment_ids'])

  api_import.send(visitor_events, title='Send first events')
  api_import.send(conversion_events, title='Send conversions')


# TODO Create logging infrastructure (run time, generated data counts, records inserted).
def main(args):
  logging.basicConfig(level=logging.INFO)

  config = get_config(args.config)
  database = create_database(config['experiment']['id'])

  create_visitors(config, database)
  create_baseline_events(config, database)

  if args.include_multiple_conversions:
    create_distributed_events(config, database)

  if args.include_segments:
    create_segments(config, database)

  if args.api_send:
    send_events(config, database)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Send fake data to an Optimizely experiment.')

  parser.add_argument('-a', '--api-send',
                      action='store_true',
                      help='Send events to Optimizely via GET.')

  parser.add_argument('-c', '--config',
                      default='./config/web/web_test.yaml',
                      help='Path to YAML file with experiment/distribution information.',
                      required=True)

  parser.add_argument('-m', '--include-multiple-conversions',
                      action='store_true',
                      help='Add additonal conversions for count goals.')

  parser.add_argument('-s', '--include-segments',
                      action='store_true',
                      help='Add segment values to events.')
  
  main(parser.parse_args())
