# cxxr2prov

## Outline

The objective of this program is to take a
[CXXR](https://github.com/cxxr-devel/cxxr) XML serialisation file and extract
from it [PROV-O](http://www.w3.org/TR/prov-o/) in
[Turtle](http://www.w3.org/TeamSubmission/turtle/).

## Algorithm Details
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
element.

```
begin
    classes_of_interest := {
                            'CXXR::Symbol' : (symbol_start, symbol_end),
    			            'CXXR::Provenance' : (prov_start, prov_end),
    			            'CXXR::CommandChronicle' : (chron_start, chron_end)
    					   }
   	classes := []
   	inhibitor_queue := []
   	node_stack := []
   	interest_count = 0

    for each (event, element) in iterativeparse(input_file) do
    	if event = 'start' then
    		if count(inhibitors) > 0 then return
    		if elem.attrib['class_name'] then
    			store callbacks in classes with key class_id
    		end
    		if element tag in inhibitor_queue then
    			remove tag from inhibitor_queue
    			add tag to inhibitors
    			return
    		end
    		if interest_count > 0 then
    			push element to node_stack
    		end
    		if element is of interest then
    			push element to node_stack
    			increment interest_count
    			call element start callback function
    		end
    	end

    	if event = 'end' then
    		if element tag in inhibitors then
    			remove tag from inhibitors
    			return
    		end if
    		if count(inhibitors) > 0 then
    			clear element
    			return
    		end
    		if element is of interest then
    			call element end callback function
                decrement interest_count

                if interest_count = 0 then
                    until node_stack is empty do
                        pop E from node_stack
                        clear E
            if interest_count > 0 then
                clear element
            end
    	end
    end
end

```
