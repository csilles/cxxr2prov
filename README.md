# cxxr2prov

## Outline

The objective of this program is to take a
[CXXR](https://github.com/cxxr-devel/cxxr) XML serialisation file and extract
from it [PROV-O](http://www.w3.org/TR/prov-o/) in
[Turtle](http://www.w3.org/TeamSubmission/turtle/).

**This program is intended to work (currently) with my
[prov](https://github.com/csilles/cxxr/tree/prov) branch of cxxr**

## Features
* XML stream-parsing algorithm enables parsing of large (several GB) XML files,
  with minimal memory overhead
* Pretty progress monitoring to display: elapsed time and numbers of
  `Provenance`, `CommandChronicle` and `Symbol` records encountered

## Installation
    $ git clone https://github.com/csilles/cxxr2prov
    $ cd cxxr2prov
    $ pip install -r requirements

## Usage
    $ ./cxxr2prov.py [path to input file] [path to output file]
Or for quick reference:

    $ ./cxxr2prov.py --help

## Assumptions
The algorithm assumes the following details about the structure of the CXXR XML
serialisation file:

* The root element is `<boost_serialization>`
* Classes `CXXR::{Provenance, Symbol, CommandChronicle}` are each exported by
  boost::serialization with key of their (namespace-qualified) class name.
    * This is the default behaviour of the macro `BOOST_CLASS_EXPORT_KEY`.
    * The first time an element of each of these types is encountered, its
      `class_id` attribute will be recorded, and subsequently used to determine
      whether an element is of interest to us.
* `CXXR::Symbol` will contain elements with the following tags:
    * `<symtype>`
    * `<name>`
* `CXXR::Provenance` will contain the following elements:
    * `<chronicle>`
    * `<symbol>`
    * `<sec>`
    * `<usec>`
* `CXXR::CommandChronicle` will contain the following elements:
    * `<str_command>`
    * `<parent>`, for each parent

## Details
The algorithm implemented uses a "iterative parsing" approach to XML
processing, which prevents the entire XML tree from being stored in memory and
instead processes **events** such as *start* and *end* of elements as they are
encountered. This enables the algorithm to maintain in memory only the elements
of a subtree rooted in a node in which we are **interested**. Because these
elements may potentially appear in any tag---e.g. a `CXXR::Symbol` is likely to
be defined in the `<m_command>` tag of a `CXXR::Provenance` as well as the
`<symbol>` tag of a `Frame::Binding`---it is necessary to determine the type of
an element by inspecting its `class_id` attribute as attributed by
`boost::serialization`.  Conversely, those elements in which we are not
interested, will be cleared so their memory occupation is released.

Inside an interested node, all nodes will be recorded (i.e. not cleared). A
mechanism has been included to manually **inhibit** this recording and clear
nodes between certain tags. This was introduced to prevent the `<m_value>` node
of a xenogenous Provenance being stored in memory. A list of tags to inhibit is
maintained.

Although it should in
[theory](http://www.ibm.com/developerworks/xml/library/x-hiperfparse/) be
possible at the **start** of an element to
look ahead (using XPath), in practice this did not always work and some of the
elements were truncated. For this reason, we wait until the **end** of an
element to perform processing the data it contains.
