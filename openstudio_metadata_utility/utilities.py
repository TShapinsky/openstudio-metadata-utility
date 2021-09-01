from typing import cast
from openstudio import openstudiomodelcore
from openstudio.openstudiomodelcore import Model_load
from openstudio import IddObjectType as idd
import tasty.entities as te
import openstudio
import inspect
from enum import Enum

class MetaNode:
    def __init__(self, *nodes):
        self.nodes = {}
        for node in nodes:
            init_node = None
            if type(node) == te.EntityType:
                init_node = node.deep_copy()
            elif type(node) == te.SimpleShape or type(node) == te.CompositeShape:
                init_node = node.cast_to_entity()
            self.nodes[init_node._type_uri.split('#')[0]] = init_node
    
    def set_namespace(self, namespace):
        for node in self.nodes.values():
            node.set_namespace(namespace)

    def set_id(self, id):
        for node in self.nodes.values():
            node.set_id(id)
        self._id = id

    def sync(self):
        for node in self.nodes.values():
            node.sync()
    
    def bind_to_graph(self, graph):
        for namespace in graph.namespaces():
            uri = namespace[1].split('#')[0]
            if uri in self.nodes:
                self.nodes[uri].bind_to_graph(graph)

    def add_tags(self, tags, ontology):
        for namespace in ontology.namespaces():
            uri = namespace[1].split('#')[0]
            if uri in self.nodes:
                self.nodes[uri].add_tags(tags, ontology)

    def add_relationship(self, relationship, node):
        if type(relationship) == te.RefType:
            uri = relationship._type_uri.split('#')[0]
            if uri in self.nodes:
                if type(node) == MetaNode:
                    self.nodes[uri].add_relationship(relationship, node.of_URI(uri))
                    if hasattr(relationship, 'inverse'):
                            node.of_URI(uri).add_relationship(relationship.inverse, self.nodes[uri])
                    self.nodes[uri].sync()
                elif type(node) == te.EntityType:
                    self.nodes[uri].add_relationship(relationship, node)
                    if hasattr(relationship, 'inverse'):
                            node.add_relationship(relationship.inverse, self.nodes[uri])
                    self.nodes[uri].sync()
        elif type(relationship) == MetaRef:
            for uri, ref in relationship.all_refs().items():
                if uri in self.nodes:
                    if type(node) == MetaNode:
                        self.nodes[uri].add_relationship(ref, node.of_URI(uri))
                        if hasattr(ref, 'inverse'):
                            node.of_URI(uri).add_relationship(ref.inverse, self.nodes[uri])
                        self.nodes[uri].sync()
                    elif type(node) == te.EntityType:
                        self.nodes[uri].add_relationship(relationship, node)
                        if hasattr(ref, 'inverse'):
                            node.add_relationship(ref.inverse, self.nodes[uri])
                        self.nodes[uri].sync()

    def of_URI(self, uri):
        return self.nodes[uri]

    def __eq__(self, other):
        for uri in self.nodes:
            if uri in other.nodes.keys():
                other_node = other.nodes[uri]
                node = self.nodes[uri]
                if other_node._id != node._id or other_node._namespace != node._namespace or other_node._type_uri != node._type_uri:
                    return False
            else:
                return False
        return True

    def __str__(self) -> str:
        return_str = ""
        for uri in self.nodes:
            return_str = return_str + f"{uri}:{self.nodes[uri]._namespace}/{self.nodes[uri]._id}\n"
        return return_str


class MetaRef:
    def __init__(self, *refs):
        self.refs = {}
        for ref in refs:
            self.refs[ref._type_uri.split('#')[0]] = ref

    def all_refs(self):
        return self.refs

class PlantType(Enum):
    HOT_WATER = 1
    CHILLED_WATER = 2
    CONDENSER_WATER = 3
    HEAT_PUMP = 4

    def plant_type_from_string(plant_name: str):
        print(plant_name)
        if 'Hot-Water' in plant_name:
            return PlantType.HOT_WATER
        elif 'Chilled-Water' in plant_name:
            return PlantType.CHILLED_WATER
        elif 'Condenser-Water' in plant_name:
            return PlantType.CONDENSER_WATER
        elif 'Heat-Pump' in plant_name:
            return PlantType.HEAT_PUMP

    def plant_type_from_object(plant_object):
        loop_type = plant_object.sizingPlant().loopType()
        if 'Heating'==loop_type:
            return PlantType.HOT_WATER
        elif 'Cooling'==loop_type:
            return PlantType.CHILLED_WATER
        elif 'Condenser'==loop_type:
            return PlantType.CONDENSER_WATER

def name_to_id(name):
    return name.replace(' ','-')

def get_object_type(object) -> openstudio.IddObjectType:
    if type(object) == openstudio.openstudioutilitiesidf.WorkspaceObject:
        return object.iddObject().type()
    if hasattr(object, 'iddObjectType'):
        return object.iddObjectType()

def cast_openstudio_object(model_object):
    object_type = get_object_type(model_object)
    cast_func_name = 'to'+object_type.valueDescription().replace('OS','').replace(':','').replace('_','')
    for member in inspect.getmembers(openstudio):
        if inspect.ismodule(member[1]):
            if hasattr(member[1], cast_func_name):
                return getattr(member[1], cast_func_name)(model_object).get()

def zone_get_fcu(zone_object):
    for equip in zone_object.equipment():
        equip_object = cast_openstudio_object(equip)
        if equip_object.iddObjectType() == idd('OS:ZoneHVAC:FourPipeFanCoil'):
            return equip_object
    return False

def zone_get_exhaust(zone_object):
    for equip in zone_object.equipment():
        equip_object = cast_openstudio_object(equip)
        if equip_object.iddObjectType() == idd('OS:Fan:ZoneExhaust'):
            return equip_object
    return False

def get_coils_from_list(equips):
    coils = []
    for equip in equips:
        idd_type = equip.iddObjectType()
        if idd_type == idd("OS:Coil:Heating:Electric"):
            coils.append(equip)
        elif idd_type == idd("OS:Coil:Heating:Water"):
            coils.append(equip)
        elif idd_type == idd("OS:Coil:Cooling:Water"):
            coils.append(equip)
        elif idd_type == idd("OS:Coil:Heating:Gas"):
            coils.append(equip)
        elif idd_type == idd("OS:Coil:Cooling:DX:SingleSpeed"):
            coils.append(equip)
        elif idd_type == idd("OS:Coil:Cooling:DX:TwoSpeed"):
            coils.append(equip)
    return coils
    

