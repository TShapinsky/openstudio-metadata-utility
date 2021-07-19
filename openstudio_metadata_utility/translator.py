from rdflib import Namespace

import tasty.constants as tc
import tasty.graphs as tg
import tasty.entities as te

from openstudio_metadata_utility.openstudio_graph import OpenStudioGraph
from openstudio_metadata_utility.utilities import MetaNode, MetaRef, name_to_id, cast_openstudio_object

import openstudio

h_ont = tg.load_ontology(tc.HAYSTACK, tc.V3_9_10)
b_ont = tg.load_ontology(tc.BRICK, tc.V1_2)

# Specify the schema version (tc.V9_9_10, etc.) to use
hp = te.HaystackPointDefs(tc.V3_9_10)
he = te.HaystackEquipDefs(tc.V3_9_10)
hrefs = te.HaystackRefDefs(tc.V3_9_10)

bp = te.BrickPointDefs(tc.V1_2)
be = te.BrickEquipmentDefs(tc.V1_2)
bz = te.BrickZoneDefs(tc.V1_2)
bl = te.BrickLocationDefs(tc.V1_2)
bg = te.BrickGasDefs(tc.V1_2)
brefs = te.BrickRefDefs(tc.V1_2)

# Bind all of the first class types as attributes
hp.bind()
he.bind()
hrefs.bind()

bp.bind()
be.bind()
bz.bind()
bl.bind()
bg.bind()
brefs.bind()

# Simple wrapper around all of the shapes
shrap = te.ShapesWrapper(tc.HAYSTACK, tc.V3_9_10)

shrap.bind()
shrap.bind_composite()

equip_ref = MetaRef(hrefs.equipRef, brefs.isPartOf)
point_ref = MetaRef(hrefs.equipRef, brefs.isPointOf)
air_ref = MetaRef(hrefs.airRef, brefs.isFedBy)
space_ref = MetaRef(hrefs.spaceRef, brefs.hasLocation)

class Translator:

    def __init__(self, model, building_name) -> None:
        self.model = model
        self.building_name = building_name
        self.namespace = Namespace(f'{building_name}/')
        self.nodes = []


    def translate(self):
        model = self.model
        self.nodes = []

        G = OpenStudioGraph(model)
        hg = tg.get_versioned_graph(tc.HAYSTACK, tc.V3_9_10)
        bg = tg.get_versioned_graph(tc.BRICK, tc.V1_2)

        graphs = {(tc.HAYSTACK, tc.V3_9_10): hg, (tc.BRICK, tc.V1_2): bg}

        hg.bind(self.building_name, self.namespace)
        bg.bind(self.building_name, self.namespace)

        site_object = cast_openstudio_object(model.getObjectsByType(openstudio.IddObjectType('OS:Building'))[0])
        site = self.create_node(shrap.SiteShape, bl.Building, model_object=site_object)
        site.bind_to_graph(hg)
        site.bind_to_graph(bg)

        site_ref = MetaRef(hrefs.siteRef, brefs.hasLocation)


        for node in G.get_nodes_by_type(openstudio.IddObjectType('OS:AirloopHVAC')):
            loop_object = G.get_object_from_node(node)

            ahu = self.create_node(he.ahu, be.AHU, name=node)
            ahu.add_relationship(site_ref, site)

            outdoor_air_node = loop_object.outdoorAirNode().get()
            mixed_air_node = loop_object.mixedAirNode().get()
            supply_outlet_node = loop_object.supplyOutletNode()
            supply_inlet_node = loop_object.supplyInletNode()
            relief_air_node = loop_object.reliefAirNode().get()

            supply_context = G.get_downstream_subgraph(supply_inlet_node, stop_at_nodes=[node])
            demand_context = G.get_downstream_subgraph(loop_object.demandInletNode(), stop_at_nodes=[node])

            self.add_sensor(outdoor_air_node, "System Node Temperature", ahu, self.create_node(hp.outside_air_temp_sensor, bp.Outside_Air_Temperature_Sensor), point_ref)
            self.add_sensor(outdoor_air_node, "System Node Relative Humidity", ahu, self.create_node(hp.outside_air_humidity_sensor, bp.Outside_Air_Humidity_Sensor), point_ref)
            oadp = self.create_node(hp.outside_air_temp_sensor, bp.Outside_Air_Dewpoint_Sensor)
            oadp.add_tags(['dewPoint'], h_ont)
            self.add_sensor(outdoor_air_node, "System Node Dewpoint Temperature", ahu, oadp, point_ref)
            self.add_sensor(outdoor_air_node, "System Node Mass Flow Rate", ahu, self.create_node(hp.outside_air_flow_sensor, bp.Outside_Air_Flow_Sensor), point_ref)

            self.add_sensor(mixed_air_node, "System Node Temperature", ahu, self.create_node(hp.air_temp_sensor, bp.Mixed_Air_Temperature_Sensor), point_ref)
            self.add_sensor(mixed_air_node, "System Node Relative Humidity", ahu, self.create_node(hp.air_humidity_sensor, bp.Mixed_Air_Humidity_Sensor), point_ref)
            self.add_sensor(mixed_air_node, "System Node Mass Flow Rate", ahu, self.create_node(hp.air_flow_sensor, bp.Air_Flow_Sensor), point_ref)

            self.add_sensor(supply_outlet_node, "System Node Temperature", ahu, self.create_node(hp.discharge_air_temp_sensor, bp.Discharge_Air_Temperature_Sensor), point_ref)
            self.add_sensor(supply_outlet_node, "System Node Relative Humidity", ahu, self.create_node(hp.discharge_air_humidity_sensor, bp.Discharge_Air_Humidity_Sensor), point_ref)
            self.add_sensor(supply_outlet_node, "System Node Mass Flow Rate", ahu, self.create_node(hp.discharge_air_flow_sensor, bp.Discharge_Air_Flow_Sensor), point_ref)

            self.add_sensor(supply_inlet_node, "System Node Temperature", ahu, self.create_node(hp.return_air_temp_sensor, bp.Return_Air_Temperature_Sensor), point_ref)
            self.add_sensor(supply_inlet_node, "System Node Relative Humidity", ahu, self.create_node(hp.return_air_humidity_sensor, bp.Return_Air_Humidity_Sensor), point_ref)
            self.add_sensor(supply_inlet_node, "System Node Mass Flow Rate", ahu, self.create_node(hp.return_air_flow_sensor, bp.Return_Air_Flow_Sensor), point_ref)

            self.add_sensor(relief_air_node, "System Node Temperature", ahu, self.create_node(hp.exhaust_air_temp_sensor, bp.Exhaust_Air_Temperature_Sensor), point_ref)
            self.add_sensor(relief_air_node, "System Node Relative Humidity", ahu, self.create_node(hp.exhaust_air_humidity_sensor, bp.Exhaust_Air_Humidity_Sensor), point_ref)
            self.add_sensor(relief_air_node, "System Node Mass Flow Rate", ahu, self.create_node(hp.exhaust_air_flow_sensor, bp.Exhaust_Air_Flow_Sensor), point_ref)

            self.resolve_supply_coils(supply_context, ahu)
            self.resolve_supply_fans(supply_context, ahu)

            zones = demand_context.get_nodes_by_type(openstudio.IddObjectType("OS:ThermalZone"))
            multi_zones = len(zones) > 1
            for node in zones:
                zone_context = demand_context.get_upstream_subgraph(node, stop_at_types=[openstudio.IddObjectType("OS:AirLoopHVAC:ZoneSplitter")])
                zone_object = demand_context.get_object_from_node(node)
                zone_return_object = zone_object.returnAirModelObject().get()
                zone = self.create_node(shrap.HVACZoneShape, bz.HVAC_Zone, name=node)
                zone.add_relationship(hrefs.siteRef, site)

                for node in zone_context.get_nodes_by_type(openstudio.IddObjectType("OS:AirTerminal:SingleDuct:VAV:Reheat")):
                    terminal_object = demand_context.get_object_from_node(node)
                    terminal_inlet_object = terminal_object.inletModelObject().get()
                    terminal_outlet_object = terminal_object.outletModelObject().get()

                    terminal = self.create_node(he.vav, be.VAV, name=node)
                    terminal.add_relationship(air_ref, ahu)
                    terminal.add_relationship(space_ref, zone)

                    coil_object = terminal_object.reheatCoil()
                    coil = self.create_node(shrap.ElecHeatingCoilShape, be.Heating_Coil, model_object=coil_object)
                    coil.add_tags(['reheats'], h_ont)
                    coil.add_relationship(equip_ref, terminal)

                    hcdat = self.create_node(hp.discharge_air_temp_sensor, bp.Discharge_Air_Temperature_Sensor)
                    hcdat.add_tags(['heatingCoil'], h_ont)
                    hcdarh = self.create_node(hp.discharge_air_humidity_sensor, bp.Discharge_Air_Humidity_Sensor)
                    hcdarh.add_tags(['heatingCoil'], h_ont)
                    hceps = self.create_node(shrap.ElecHeatingPowerSensorShape, bp.Electrical_Power_Sensor)
                    self.add_sensor(terminal_outlet_object, "System Node Temperature", coil, hcdat, point_ref)
                    self.add_sensor(terminal_outlet_object, "System Node Relative Humidity", coil, hcdarh, point_ref)
                    self.add_sensor(coil_object, "Heating Coil Electricity Rate", coil, hceps, point_ref)
                    damper_position_command = self.create_node(he.damper_actuator, bp.Damper_Position_Command)
                    self.add_empty_actuator(terminal_object, "Zone Air Terminal VAV Damper Position", terminal, damper_position_command, point_ref)
                    self.add_empty_actuator(terminal_object, "Zone Air Terminal Minimum Air Flow Fraction", terminal, self.create_node(hp.air_flow_sp, bp.Min_Position_Setpoint_Limit), point_ref)

                for node in zone_context.get_nodes_by_type(openstudio.IddObjectType("OS:AirTerminal:SingleDuct:ConstantVolume:NoReheat")):
                    terminal_object = demand_context.get_object_from_node(node)
                    terminal_inlet_object = terminal_object.inletModelObject().get()
                    terminal_outlet_object = terminal_object.outletModelObject().get()

                    terminal = self.create_node(he.cav, be.CAV, name=node)
                    terminal.add_relationship(air_ref, ahu)
                    terminal.add_relationship(space_ref, zone)
                    damper_position_command = self.create_node(he.damper_actuator, bp.Damper_Position_Command)
                    self.add_empty_actuator(terminal_object, "Zone Air Terminal VAV Damper Position", terminal, damper_position_command, point_ref)
                    self.add_empty_actuator(terminal_object, "Zone Air Terminal Minimum Air Flow Fraction", terminal, self.create_node(hp.air_flow_sp, bp.Min_Position_Setpoint_Limit), point_ref)

                if multi_zones:
                    zrat = self.create_node(hp.return_air_temp_sensor, bp.Return_Air_Temperature_Sensor)
                    zrat.add_tags(['zone'], h_ont)
                    zrarh = self.create_node(hp.return_air_humidity_sensor, bp.Return_Air_Humidity_Sensor)
                    zrarh.add_tags(['zone'], h_ont)
                    zraf = self.create_node(hp.return_air_flow_sensor, bp.Return_Air_Flow_Sensor)
                    zraf.add_tags(['zone'], h_ont)
                    self.add_sensor(zone_return_object, "System Node Temperature", zone, zrat, point_ref)
                    self.add_sensor(zone_return_object, "System Node Relative Humidity", zone, zrarh, point_ref)
                    self.add_sensor(zone_return_object, "System Node Mass Flow Rate", zone, zraf, point_ref)

                    self.add_sensor(terminal_inlet_object, "System Node Temperature", terminal, self.create_node(hp.discharge_air_temp_sensor, bp.Discharge_Air_Temperature_Sensor), point_ref)
                    self.add_sensor(terminal_inlet_object, "System Node Mass Flow Rate", terminal, self.create_node(hp.discharge_air_flow_sensor, bp.Discharge_Air_Flow_Sensor), point_ref)
                    self.add_sensor(terminal_inlet_object, "System Node Relative Humidity", terminal, self.create_node(hp.discharge_air_humidity_sensor, bp.Discharge_Air_Humidity_Sensor), point_ref)

                zat = self.create_node(hp.air_temp_sensor, bp.Zone_Air_Temperature_Sensor)
                zat.add_tags(['zone'], h_ont)
                self.add_sensor(zone_object.zoneAirNode(), "System Node Temperature", zone, zat, point_ref)

                zarh = self.create_node(hp.air_humidity_sensor, bp.Zone_Air_Humidity_Sensor)
                zarh.add_tags(['zone'], h_ont)
                self.add_sensor(zone_object.zoneAirNode(), "System Node Relative Humidity", zone, zarh, point_ref)

                zathsp = self.create_node(hp.air_temp_sp, bp.Zone_Air_Heating_Temperature_Setpoint)
                zathsp.add_tags(['zone', 'heating'], h_ont)
                self.add_actuator(zone_object.zoneAirNode(), "Zone Temperature Control", "Heating Setpoint", zone, zathsp, point_ref)

                zatcsp = self.create_node(hp.air_temp_sp, bp.Zone_Air_Cooling_Temperature_Setpoint)
                zatcsp.add_tags(['zone', 'cooling'], h_ont)
                self.add_actuator(zone_object.zoneAirNode(), "Zone Temperature Control", "Cooling Setpoint", zone, zatcsp, point_ref)

        self.sync()
        return graphs

    def resolve_supply_fans(self, context, ahu):
        for node in context.get_nodes_by_type(openstudio.IddObjectType("OS:Fan:VariableVolume")):
            fan = self.create_node(shrap.VAVFanShape, be.Discharge_Fan, name=node)
            fan.add_tags(['discharge'], h_ont)
            fan.add_relationship(equip_ref, ahu)

        for node in context.get_nodes_by_type(openstudio.IddObjectType("OS:Fan:ConstantVolume")):
            fan = self.create_node(shrap.CAVFanShape, be.Discharge_Fan, name=node)
            fan.add_tags(['discharge'], h_ont)
            fan.add_relationship(equip_ref, ahu)

    def add_supply_fan_points(self, fan, fan_object):
        self.add_sensor(fan_object, "Heating Coil Electricity Rate", fan, self.create_node(shrap.ElecPowerSensor, bp.Electrical_Power_Sensor), point_ref)
    
    def resolve_supply_coils(self, context, ahu):
        equip_ref = MetaRef(hrefs.equipRef, brefs.isPartOf)
        point_ref = MetaRef(hrefs.equipRef, brefs.isPointOf)
        
        for node in context.get_nodes_by_type(openstudio.IddObjectType("OS:Coil:Heating:Gas")):
            coil_object = context.get_object_from_node(node)
            coil = self.create_node(shrap.GasHeatingCoilShape, be.Heating_Coil, name=node)
            coil.add_relationship(equip_ref, ahu)
            #coil.add_relationship(brefs.isFedBy, bg.Natural_Gas) #brick natual gas

            hcgs = self.create_node(shrap.GasEnergySensorShape, bp.Energy_Sensor)
            self.add_sensor(coil_object, "Heating Coil NaturalGas Rate", coil, hcgs, point_ref)
            self.add_supply_coil_points(coil, coil_object)

        for node in context.get_nodes_by_type(openstudio.IddObjectType("OS:Coil:Cooling:DX:TwoSpeed")):
            coil = self.create_node(shrap.DXCoolingCoilShape, be.Cooling_Coil, name=node)
            coil.add_relationship(equip_ref, ahu)
            self.add_supply_coil_points(coil, coil_object, heating=False)

    def add_supply_coil_points(self, coil, coil_object, heating=True):
        outlet_object = cast_openstudio_object(coil_object.outletModelObject().get())
        cdat = self.create_node(hp.discharge_air_temp_sensor, bp.Discharge_Air_Temperature_Sensor)
        cdarh = self.create_node(hp.discharge_air_humidity_sensor, bp.Discharge_Air_Humidity_Sensor)
        cdaf = self.create_node(hp.discharge_air_flow_sensor, bp.Discharge_Air_Flow_Sensor)

        if heating:
            cdat.add_tags(['heatingCoil'], h_ont)
            cdarh.add_tags(['heatingCoil'], h_ont)
            cdaf.add_tags(['heatingCoil'], h_ont)
            self.add_sensor(coil_object, "Heating Coil Air Heating Rate", coil, self.create_node(shrap.HeatingCapacitySensorShape, bp.Heating_Thermal_Power_Sensor), point_ref)
        else:
            cdat.add_tags(['coolingCoil'], h_ont)
            cdarh.add_tags(['coolingCoil'], h_ont)
            cdaf.add_tags(['coolingCoil'], h_ont)
            self.add_sensor(coil_object, "Cooling Coil Total Cooling Rate", coil, self.create_node(shrap.CoolingCapacitySensorShape, bp.Heating_Thermal_Power_Sensor), point_ref)
        
        self.add_sensor(outlet_object, "System Node Temperature", coil, cdat, point_ref)
        self.add_sensor(outlet_object, "System Node Mass Flow Rate", coil, cdaf, point_ref)
        self.add_sensor(outlet_object, "System Node Relative Humidity", coil, cdarh, point_ref)

    def add_sensor(self, node_object, system_node_property, tasty_parent_object, tasty_object, tasty_relationship):
        name = node_object.name().get() + '_' + system_node_property.replace(' ','_')
        output_variable = openstudio.openstudiomodel.OutputVariable(system_node_property, self.model)
        output_variable.setKeyValue(node_object.name().get())
        output_variable.setReportingFrequency('timestep')
        output_variable.setName(name)

        sensor = openstudio.openstudiomodel.EnergyManagementSystemSensor(self.model, output_variable)
        sensor.setKeyName(str(node_object.handle()))
        sensor.setName(f"EMS_{name}")

        sensor_name = name_to_id(output_variable.name().get())
        tasty_object.set_namespace(self.namespace)
        tasty_object.set_id(sensor_name)
        tasty_object.add_relationship(tasty_relationship, tasty_parent_object)
        tasty_object.sync()
        return tasty_object

    def add_actuator(self, node_object, actuator_component_type, actuator_control_type, tasty_parent_object, tasty_object, tasty_relationship):
        name = name_to_id(node_object.name().get() + ' ' + actuator_component_type + ' ' + actuator_control_type)
        actuator  = openstudio.openstudiomodel.EnergyManagementSystemActuator(node_object, actuator_component_type, actuator_control_type)
        actuator.setName(name)

        actuator_name = name_to_id(actuator.name().get())
        tasty_object.set_namespace(self.namespace)
        tasty_object.set_id(actuator_name)
        tasty_object.add_relationship(tasty_relationship, tasty_parent_object)
        tasty_object.sync()
        return tasty_object

    def add_empty_actuator(self, node_object, actuator_name, tasty_parent_object, tasty_object, tasty_relationship):
        name = name_to_id(node_object.name().get() + ' ' + actuator_name)
        tasty_object.set_id(name)
        tasty_object.set_namespace(self.namespace)
        tasty_object.add_relationship(tasty_relationship, tasty_parent_object)
        tasty_object.sync()
        return tasty_object


    def create_node(self, *nodes, name=None, model_object=None):
        node = MetaNode(*nodes)
        if model_object != None:
            name = model_object.name().get()
        if name != None:
            name = name_to_id(name)
            node.set_id(name)   
        node.set_namespace(self.namespace)
        self.register_node(node)
        return node

    def register_node(self, node):
        self.nodes.append(node)
    
    def sync(self):
        for node in self.nodes:
            node.sync()