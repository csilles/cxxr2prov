#!/usr/bin/env python
"""
cxxr2prov: A program to extract provenance information from a CXXR XML
           serialisation, and output an RDF Turtle representation of a PROV
           graph.
Chris A. Silles <casilles@gmail.com>
"""


""" general utilities """
import argparse,sys,os.path
import time
from datetime import datetime
""" threading """
import threading
""" cxxr2prov """
from ParseError import ParseError
from Provenance import Provenance
from Chronicle import Chronicle
""" rdf """
from rdflib import Graph
from rdflib import URIRef, Literal, BNode, Namespace, ConjunctiveGraph
from rdflib import RDF, RDFS
from rdflib.namespace import XSD # for dateTime
from rdflib.namespace import FOAF
""" xml parsing """
from lxml import etree
""" pretty output """
from clint.textui import puts, colored
from clint.textui import columns

STDOUT = sys.stdout

class CXXR2PROV:
    """ Classes. e.g. { 'CXXR::Symbol' : 5} """
    classes = {}
    """ Counters """
    count_elements_processed = 0
    count_used = 0
    count_was_generated_by = 0
    """ Protection and Inhibition """
    node_stack = []
    interest_count = 0
    inhibitor_queue = []
    inhibitors = []
    """ Thread-related """
    __time_start = None
    __interrupt = False
    """ RDF Output """
    __cxxr_ns = "http://cs.kent.ac.uk/projects/cxxr#"
    __prefixes = {
        "xsd" : "http://www.w3.org/2001/XMLSchema#",
        "foaf" : "http://xmlns.com/foaf/0.1/",
        "prov" : "http://www.w3.org/ns/prov#",
        "" : __cxxr_ns
    }
    NS = Namespace(__cxxr_ns)
    PROV = Namespace("http://www.w3.org/ns/prov#")

    def __init__ (self, in_file, out_file, verbose):
        self.verbose = verbose
        self.in_file = in_file
        self.out_file = out_file

        self.classes_of_interest = {
          'CXXR::Symbol' : (self.symbol_start, self.symbol_stop),
          'CXXR::Provenance' : (self.provenance_start, self.provenance_stop),
          'CXXR::CommandChronicle' : (self.chronicle_start, self.chronicle_stop)
        }
        self.dict_provenances = {}
        self.dict_chronicles = {}
        self.dict_symbols = {}
        self.iterparse()
        self.make_graph(out_file)

    def class_id (self, elem):
        if 'class_id' in elem.attrib or 'class_id_reference' in elem.attrib:
            return elem.get('class_id', elem.get('class_id_reference'))
        else: return None

    def element_of_interest (self, elem):
        class_id = self.class_id(elem)

        return class_id is not None and \
               class_id in self.classes and \
               'object_id' in elem.attrib

    def iterparse (self):
        if not self.verbose:
            self.iterparse2()
        else:
            puts(colored.green("Parsing '" + self.in_file + "'..."))
            self.__interrupt = False
            self.__working = True
            ip_thread = threading.Thread(target=self.iterparse2)
            ip_thread.start()

            status_thread = threading.Thread(target=self.iterparse_status)
            status_thread.start()

            while True:
                try:
                    ip_thread.join(5)
                    if not ip_thread.isAlive(): break
                except KeyboardInterrupt:
                    self.__interrupt = True
                    status_thread.join()
                    print('\nInterrupted. Exiting...')
                    sys.exit(1)

            self.__working = False
            status_thread.join() # Wait for status thread to finish
            print('')

    def iterparse2 (self):
        for (event, elem) in etree.iterparse(self.in_file, \
                                             events=('start', 'end')):
            if self.__interrupt:
                break;

            if event == 'start':
                self.node_start(elem)
            elif event == 'end':
                self.node_end(elem)

    def node_end (self, elem):
            self.count_elements_processed += 1

            if elem.tag in self.inhibitors:
                self.inhibitors.remove(elem.tag)
                return

            inhibit = len(self.inhibitors) > 0
            if inhibit:
                elem.clear()
                return

            if self.element_of_interest(elem):
                class_id = self.class_id(elem)
                handler = self.classes[class_id][1]
                handler(elem)
                self.interest_count -= 1

                no_interest = self.interest_count == 0
                if no_interest:
                    while len(self.node_stack) > 0:
                        e = self.node_stack.pop()
                        e.clear()

            recording = self.interest_count > 0
            if not recording:
                elem.clear()

    def node_start (self, elem):
            inhibited = len(self.inhibitors) > 0
            if inhibited:
                return

            if 'class_name' in elem.attrib:
                self.process_class(elem)

            if elem.tag in self.inhibitor_queue:
                self.inhibitor_queue.remove(elem.tag)
                self.inhibitors.append(elem.tag)
                return

            recording = self.interest_count > 0
            if recording or self.element_of_interest(elem):
                self.node_stack.append(elem)
            if self.element_of_interest(elem):
                self.interest_count += 1
                class_id = self.class_id(elem)
                handler = self.classes[class_id][0]
                handler(elem)

    def process_class (self, elem):
        class_name = elem.attrib['class_name']
        class_id = elem.attrib['class_id']

        if class_name in self.classes_of_interest:
            handler = self.classes_of_interest[class_name]
            self.classes[class_id] = handler

    def symbol_start (self, elem):
        pass

    def symbol_stop (self, elem):
        object_id = elem.attrib['object_id']
        xp1 = etree.XPath("child::symtype/text()")
        xp2 = etree.XPath("child::name/text()")
        x = xp1(elem)
        if not x or x[0] != '0': return # Only symtype 0

        x = xp2(elem)
        symbol = x[0]
        self.dict_symbols[object_id] = symbol

    def provenance_start (self, elem):
        # Establish a persistence inhibitor tag
        self.inhibitor_queue.append("m_value")

    def provenance_stop (self, elem):
        # Provenance ID
        prov_id = elem.get("object_id")
        # Chronicle ID
        xp_chron = etree.XPath("child::chronicle")
        chron = xp_chron(elem)[0]
        chron_id = chron.get("object_id", chron.get("object_id_reference"))

        # Symbol ID
        xp_sym = etree.XPath("child::symbol")
        sym = xp_sym(elem)[0]
        sym_id = sym.get("object_id", sym.get("object_id_reference"))

        # Timestamp
        xp_sec = etree.XPath("child::sec/text()")
        xp_usec = etree.XPath("child::usec/text()")
        sec = int(xp_sec(elem)[0])
        usec = int(xp_usec(elem)[0])

        self.dict_provenances[prov_id] = Provenance(self, sym_id, sec, usec, chron_id)


    def chronicle_start (self, elem):
        pass

    def chronicle_stop (self, elem):
        # Chronicle ID
        chron_id = elem.get("object_id")
        # Command string
        xp_cmd = etree.XPath("child::str_command/text()")
        str_command = xp_cmd(elem)[0]
        # Parents
        parents = []
        xp_par = etree.XPath("child::parent")
        for parent in xp_par(elem):
            par_id = parent.get("object_id", parent.get("object_id_reference"))
            parents.append(par_id)

        self.dict_chronicles[chron_id] = Chronicle(self, str_command, parents)

    def iterparse_status (self):
        self.__time_start = datetime.now()
        col = 29
        scol = 15
        puts(columns([(colored.blue('Time Elapsed')), col],
                     [(colored.green('Elements Processed')), col],
                     [(colored.green('Symbols')), scol],
                     [(colored.green('Provenances')), scol],
                     [(colored.green('Chronicles')), scol],
                     [(colored.red('Intr.')), scol],
                     [(colored.red('Inhib.')), scol]
                ))
        puts(columns([str(""), col],
                     [str(self.count_elements_processed), col],
                     [str(0), scol],
                     [str(0), scol],
                     [str(0), scol],
                     [str(0), scol],
                     [str(0), scol]
                            ), newline=False)

        interval = 0.1
        interval_changes = { 5 : 0.2, 10 : 0.5, 20 : 1, 30 : 5 }
        while True:
            elapsed = datetime.now() - self.__time_start
            STDOUT.write('\r')
            seconds = elapsed.seconds
            puts(colored.white(columns(['{:02}:{:02}:{:02}'.format(seconds // 3600, seconds % 3600 // 60, seconds % 60), col],
                ["{:,}".format(self.count_elements_processed), col],
                [str(len(self.dict_symbols)), scol],
                [str(len(self.dict_provenances)), scol],
                [str(len(self.dict_chronicles)), scol],
                [str(self.interest_count), scol],
                [str(len(self.inhibitors)), scol]
                )), newline=False)
            STDOUT.flush()
            if self.__interrupt or not self.__working: break
            if seconds in interval_changes:
                interval = interval_changes[seconds]
            time.sleep(interval)

    def get_chronicles (self): return self.dict_chronicles;

    def get_provenances (self): return self.dict_provenances;

    def make_graph (self, outputfile):
        g = Graph()

        for k, v in self.__prefixes.iteritems():
            g.bind(k, v)

        if self.verbose: puts(colored.green("Establishing URIRefs for Provenances..."))
        for k, v in self.dict_provenances.iteritems():
            v.establish_URIRef()

        if self.verbose: puts(colored.green("Putting Provenances to Graph..."))
        for k, v in self.dict_provenances.iteritems():
            v.put_on_graph(g)

        if self.verbose: puts(colored.green("Putting Chronicles to Graph..."))
        for k, v in self.dict_chronicles.iteritems():
            v.put_on_graph(g)

        if self.verbose: puts(colored.green("Serialising Graph..."))

        g.serialize(outputfile, format="turtle")

        if self.verbose:
            puts(colored.white("+-------------------+"))
            puts(colored.white("| ")+colored.blue("cxxr2prov Summary")+colored.white(" |"))
            puts(colored.white("+-------------------+"))
            puts("Number of PROV Entities: " + str(len(self.dict_provenances)))
            puts("Number of PROV Activities: " + str(len(self.dict_chronicles)))
            puts("Number of PROV used attributes: " + str(self.count_used))
            puts("Number of PROV wasGeneratedBy attributes: " + str(self.count_was_generated_by))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", type=str, help="Path to CXXR XML serialisation input")
    parser.add_argument("outfile", type=str, help="Path to Turtle PROV-O output file")
    parser.add_argument("--verbose", action='store_true')
    args = parser.parse_args()

    in_file = args.infile
    out_file = args.outfile
    verbose = args.verbose

    if not os.path.exists(in_file):
        sys.exit("File '" + in_file + "' does not exist");
    try:
        cxxr_2_prov = CXXR2PROV(in_file, out_file, verbose)
    except ParseError as exc:
        sys.exit("cxxr2prov parsing failed.\n" + str(exc))
