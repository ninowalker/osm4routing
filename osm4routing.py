from osm4routing_xml import *
from progressbar import ProgressBar
import os
import bz2, gzip
import sys
from optparse import OptionParser
from sqlalchemy import Table, Column, MetaData, Integer, String, Float, SmallInteger, create_engine
from sqlalchemy.orm import mapper, sessionmaker

class Node(object):
    def __init__(self, id, lon, lat, the_geom = 0):
        self.original_id = id
        self.lon = lon
        self.lat = lat
        self.the_geom = the_geom

class Edge(object):
    def __init__(self, id, source, target, length, car, car_rev, bike, bike_rev, foot, the_geom):
        self.id = id
        self.source = source
        self.target = target
        self.length = length
        self.car = car
        self.car_rev = car_rev
        self.bike = bike
        self.bike_rev = bike
        self.foot = foot
        self.the_geom = the_geom

def parse(file, output="csv", edges_name="edges", nodes_name="nodes"):

    if not os.path.exists(file):
        raise IOError("File {0} not found".format(file))

    if output != "csv":
        metadata = MetaData()
        nodes_table = Table(nodes_name, metadata,
                Column('id', Integer, primary_key = True),
                Column('original_id', String, index = True),
                Column('lon', Float, index = True),
                Column('lat', Float, index = True),
                Column('the_geom', String)
                )
        
        edges_table = Table(edges_name, metadata,
            Column('id', Integer, primary_key=True),
            Column('source', Integer, index=True),
            Column('target', Integer, index=True),
            Column('length', Float),
            Column('car', SmallInteger),
            Column('car_rev', SmallInteger),
            Column('bike', SmallInteger),
            Column('bike_rev', SmallInteger),
            Column('foot', SmallInteger),
            Column('the_geom', String))

        engine = create_engine(output)
        metadata.drop_all(engine)
        metadata.create_all(engine) 
        mapper(Node, nodes_table)
        mapper(Edge, edges_table)
        Session = sessionmaker(bind=engine)
        session = Session()

    extension = os.path.splitext(file)[1]
    if extension == '.bz2':
        print "Recognized as bzip2 file"
        f = bz2.BZ2File(file, 'r') 

    elif extension == '.gz':
        print "Recognized as gzip2 file"
        f = gzip.open(file, 'r') 

    else:
        print "Supposing OSM/xml file"
        filesize = os.path.getsize(file)
        f = open(file, 'r') 

    buffer_size = 4096
    p = Parser()
    eof = False
    print "Step 1: reading file {0}".format(file)
    read = 0
    while not eof:
        s = f.read(buffer_size)
        eof = len(s) != buffer_size
        p.read(s, len(s), eof)
        read += len(s)

    print "  Read {0} nodes and {1} ways\n".format(p.get_osm_nodes(), p.get_osm_ways())

    print "Step 2: saving the nodes"
    nodes = p.get_nodes()
    if output == "csv":
        n = open(nodes_name + '.csv', 'w')
        n.write('"node_id","longitude","latitude"\n')

    pbar = ProgressBar(maxval=len(nodes))
    pbar.start()
    count = 0
    for node in nodes:
        if output == "csv":
            n.write("{0},{1},{2}\n".format(node.id, node.lon, node.lat))
        else:
            session.add(Node(node.id, node.lon, node.lat))
        count += 1
        pbar.update(count)
    if output == "csv":
        n.close()
    else:
        session.commit()
    pbar.finish()

    print "  Wrote {0} nodes\n".format(count)

    print "Step 3: saving the edges"
    edges = p.get_edges()
    pbar = ProgressBar(maxval=len(edges))
    pbar.start()
    count = 0
    if output == "csv":
        e = open(edges_name + '.csv', 'w')
        e.write('"edge_id","source","target","length","car","car reverse","bike","bike reverse","foot","WKT"\n')
    for edge in edges:
        if output == "csv":
            e.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},LINESTRING("{9}")\n'.format(edge.edge_id, edge.source, edge.target, edge.length, edge.car, edge.car_d, edge.bike, edge.bike_d, edge.foot, edge.geom))
        else:
            session.add(Edge(edge.edge_id, edge.source, edge.target, edge.length, edge.car, edge.car_d, edge.bike, edge.bike_d, edge.foot, edge.geom))
        count += 1
        pbar.update(count)
    if output == "csv":
        e.close()
    else:
        session.commit()
    pbar.finish()
    print "  Wrote {0} edges\n".format(count)

    print "Happy routing :) and please give some feedback!"

def main():
    usage = """Usage: %prog [options] input_file

input_file must be an OSM/XML file. It can be compressed with gzip (.gz) or bzip2 (.bz2)"""


    parser = OptionParser(usage)
    parser.add_option("-o", "--output", dest="output", default="csv",
            help="""'csv' if you want a simple file,
a connection string to use a database (Example: sqlite:///foo.db postgresql://john@localhost/my_database)
[default: %default]""")
    parser.add_option("-n", "--nodes_name", dest="nodes_name", default="nodes", help="Name of the file or table where nodes are stored [default: %default]")
    parser.add_option("-e", "--edges_name", dest="edges_name", default="edges", help="Name of the file or table where edges are stored [default: %default]")
    (options, args) = parser.parse_args()

    if len(args) != 1:
        sys.stderr.write("Wrong number of argumented. Expected 1, got {0}\n".format(len(args)))
        sys.exit(1)

    try:
        parse(args[0], options.output, options.edges_name, options.nodes_name)
    except IOError as e:
        sys.stderr.write("I/O error: {0}\n".format(e))
    except Exception as e:
        sys.stderr.write("Woops... an error occured: {0}\n".format(e))

if __name__ == "__main__":
    main()
