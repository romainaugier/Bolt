# Bolt
Acyclic node graphs for easy task automation.

Dependencies :
- Python 3.9.7 
- PyQt5
- Colorama
- PyInstaller (required if you want to build the executable)


## Description
Bolt was designed to ease task automation by enabling users to create graphs composed of nodes representing either data or actions, and connecting them together to create workflows that can be reused later, thus avoiding repetitive work.
The node library can be easily maintained and extended as a node definition is simply represented by a text file, respecting a syntax convention to declare attributes (such as name, category, icon...), plugs (inputs and outputs) and the op (the python script to execute). 

Bolt provides a few utilities for the python script executed by the node :
- inputs and outputs of the node are available as global variables (the variable name of a plug is its short name)
- you can define macros to ease the development and allow quick refactoring
- a library is provided to the client with various functions and classes

Graph files saves the content of every node, thus ensuring backward compatibility if you modify the definition of a node. You can always update the node either with the Bolt Application or with the BoltCommand in interact mode.