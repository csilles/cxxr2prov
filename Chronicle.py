import rdflib
from rdflib import URIRef,Graph,RDF,RDFS,Literal
from rdflib.namespace import XSD
import hashlib

class Chronicle:
	__c2p = None

	def __init__ (self, c2p, command, parentids):
		self.__c2p = c2p
		self.command = command
		self.parentids = parentids
		self.URI = None
		self.parents = []

		self.establish_URIRef()

	def __str__ (self):
		return "Chronicle: Command '" + self.command +"', Parent IDs " + repr(self.parentids) + " " + \
		       "URI '" + repr(self.URI) + "', Parents : " + repr(self.parents)

	def establish_URIRef (self):
		hash_object = hashlib.md5(bytes(self.command + repr(self.parents)))
		name = "command-" + hash_object.hexdigest()
		self.URI = URIRef(self.__c2p.NS[name])

	def dereference (self):
		provenances = self.__c2p.get_provenances()
		for prov_oid in self.parentids:
			self.parents.append(provenances[prov_oid])

	def put_on_graph (self, graph):
		self.dereference()
		PROV = self.__c2p.PROV
		graph.add((self.URI, RDF.type, PROV["Activity"]))
		graph.add((self.URI, RDFS.label, Literal(self.command)))
		for parent in self.parents:
			if (self.__c2p.verbose): self.__c2p.count_used += 1
			graph.add((self.URI, PROV["used"], parent.getURI()))


	def getURI (self):
		return self.URI

