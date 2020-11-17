from core.extract import Graph, FeatureNode
from core.session import Session
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--columns',
                    help='List of database columns, split by ",", i.e. "age,height,phone number".')
parser.add_argument('--database')
args = parser.parse_args()
args.columns = args.columns.strip().split(',')


def build_session():
    g = Graph(args.columns, args.database)
    # feature = FeatureNode(...)
    # g.add_feature(feature)
    # ...
    sess = Session(g)
    return sess
