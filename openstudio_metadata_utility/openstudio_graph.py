from networkx.algorithms.traversal.edgebfs import FORWARD
import openstudio
import networkx as nx
from openstudio.openstudioutilitiescore import number
from openstudio_metadata_utility.utilities import get_object_type, cast_openstudio_object
from enum import Enum

class OpenStudioGraph(nx.DiGraph):

    def __init__(self, model=None):
        super().__init__()
        if model is None:
            return
        connections = model.getObjectsByType(openstudio.IddObjectType("OS:Connection"))
        for connection in connections:
            source = connection.getField(2)
            target = connection.getField(4)
            if source.is_initialized() and target.is_initialized():
                sourceObject = openstudio.model.getModelObject(model, openstudio.toUUID(source.get())).get()
                targetObject = openstudio.model.getModelObject(model, openstudio.toUUID(target.get())).get()
                self.add_node(sourceObject.name().get(), object=sourceObject)
                self.add_node(targetObject.name().get(), object=targetObject)
                self.add_edge(sourceObject.name().get(), targetObject.name().get())

        zones = model.getObjectsByType(openstudio.IddObjectType("OS:ThermalZone"))
        for zone in zones:
            inlet_port = sourceObject = openstudio.model.getModelObject(model, openstudio.toUUID(zone.getField(9).get())).get()
            exhaust_port = sourceObject = openstudio.model.getModelObject(model, openstudio.toUUID(zone.getField(10).get())).get()
            return_port = sourceObject = openstudio.model.getModelObject(model, openstudio.toUUID(zone.getField(12).get())).get()
            self.add_node(inlet_port.name().get(), object=inlet_port)
            self.add_node(exhaust_port.name().get(), object=exhaust_port)
            self.add_node(return_port.name().get(), object=return_port)
            self.add_node(zone.name().get(), object=zone)
            self.add_edge(inlet_port.name().get(), zone.name().get())
            self.add_edge(zone.name().get(), exhaust_port.name().get())
            self.add_edge(zone.name().get(), return_port.name().get())

        self.extras = {}

    def subgraph(self, nodes):
        new_graph = super().subgraph(nodes)
        new_graph.extras = self.extras
        return new_graph

    def get_downstream_subgraph(self, node, stop_at_types=None, stop_at_nodes=None) -> 'OpenStudioGraph':
        if type(node) != str:
            node = node.name().get()
        nodes = [node]
        while True:
            additions = False
            for node in nodes:
                for node in self.neighbors(node):
                    if stop_at_types != None:
                        if self.get_type(node) in stop_at_types:
                            continue
                    if stop_at_nodes != None:
                        if node in stop_at_nodes:
                            continue
                    if not node in nodes:
                        nodes.append(node)
                        additions = True
            if not additions:
                return self.subgraph(nodes)

    def get_upstream_subgraph(self, node, stop_at_types=None, stop_at_nodes=None) -> 'OpenStudioGraph':
        if type(node) != str:
            node = node.name().get()
        nodes = [node]
        while True:
            additions = False
            for node in nodes:
                for node in self.predecessors(node):
                    if stop_at_types != None:
                        if self.get_type( node) in stop_at_types:
                            continue
                    if stop_at_nodes != None:
                        if node in stop_at_nodes:
                            continue
                    if not node in nodes:
                        nodes.append(node)
                        additions = True
            if not additions:
                return self.subgraph(nodes)

    def get_next_relative_of_type(self, node, target_type: openstudio.IddObjectType, direction: 'Direction'):
        if type(node) != str:
            node = node.name().get()
        nodes = [node]
        next_nodes_method = self.predecessors
        if direction == FORWARD:
            next_nodes_method = self.neighbors
        while True:
            additions = False
            for node in nodes:
                for node in next_nodes_method(node):
                    if self.get_type(node) == target_type:
                        return node
                    if not node in nodes:
                        nodes.append(node)
                        additions = True
            if not additions:
                return

    def get_nth_child_of_type(self, node, target_type: openstudio.IddObjectType, n: number):
        current_node = node
        for i in range(n):
            current_node = self.get_next_relative_of_type(current_node, target_type, self.Direction.FORWARD)
            if current_node is None:
                return
        return current_node

    def get_nth_parent_of_type(self, node, target_type: openstudio.IddObjectType, n: number):
        current_node = node
        for i in range(n):
            current_node = self.get_next_relative_of_type(current_node, target_type, self.Direction.BACK)
            if current_node is None:
                return
        return current_node



    def get_type(self, node) -> openstudio.IddObjectType:
        object = nx.get_node_attributes(self, "object")[node]
        return get_object_type(object)

    def get_nodes_by_type(self, idd_object_type):
        if type(idd_object_type) == str:
            idd_object_type = openstudio.IddObjectType(idd_object_type)
        nodes = []
        for node in self.nodes:
            if self.get_type(node) == idd_object_type:
                nodes.append(node)
        return nodes

    def get_object_from_node(self, node):
        model_object = nx.get_node_attributes(self, "object")[node]
        return cast_openstudio_object(model_object)

    def set_extra(self, key, value):
        self.extras[key] = value

    def get_extra(self, key):
        return self.extras[key]

    class Direction(Enum):
        FORWARD = 1
        BACK = 2
    #def get_reheat_terminals(self):
    #    types = {'OS:AirTerminal:SingleDuct:ConstantVolume:Reheat'}