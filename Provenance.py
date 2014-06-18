from datetime import datetime
import urllib
import rdflib
import hashlib
from rdflib import Graph,URIRef,RDF,RDFS,Literal
from rdflib.namespace import XSD

class Provenance:
    # Reserved characters in Turtle that will be replaced
    __chars = {'.' : '%2E'}
    __c2p = None

    def __init__(self, c2p, sym_id, sec, usec, ccoid):
        self.__c2p = c2p
        self.sym_id = sym_id
        timestamp = sec + (usec / 1e6)
        self.timestamp = datetime.utcfromtimestamp(timestamp).isoformat()
        self.ccoid = ccoid
        self.URI = None
        self.chronicle = None
        self.symbol = None

    def __str__(self):
        return "Provenance: Symbol ID {}; Timestamp {}; Chron ID {}; " + \
               "URI {}; Chronicle {}; Symbol {};"\
                 .format(self.sym_id, self.timestamp, self.ccoid, \
                         repr(self.URI), repr(self.chronicle), \
                         repr(self.symbol))

    def establish_URIRef (self):
        # Dereference the symbol id
        self.symbol = self.__c2p.dict_symbols[self.sym_id]
        # Create an object ID
        object_id = self.symbol + self.timestamp
        name = "binding-" + hashlib.md5(object_id).hexdigest()

        for k, v in self.__chars.iteritems():
            name = name.replace(k, v)
        self.URI = URIRef(self.__c2p.NS[name])

    def dereference (self):
        # Dereference the CommandChronicle Object ID against dictionary
        self.chronicle = self.__c2p.get_chronicles()[self.ccoid]

    def put_on_graph (self, graph):
        self.dereference()
        PROV = self.__c2p.PROV
        graph.add((self.URI, RDF.type, PROV["Entity"]))
        graph.add((self.URI, RDFS.label, Literal(self.symbol)))
        graph.add((self.URI, PROV["generatedAtTime"], \
                   Literal(self.timestamp, datatype=XSD.dateTime)))
        graph.add((self.URI, PROV["wasGeneratedBy"], self.chronicle.getURI()))
        if self.__c2p.verbose: self.__c2p.count_was_generated_by += 1

    def getChronicle (self): return chronicle

    def getURI (self): return self.URI

