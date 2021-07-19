import openstudio
import networkx as nx
from openstudio_metadata_utility.utilities import get_object_type, cast_openstudio_object

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

    def get_downstream_subgraph(self, node, stop_at_types=None, stop_at_nodes=None):
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

    def get_upstream_subgraph(self, node, stop_at_types=None, stop_at_nodes=None):
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