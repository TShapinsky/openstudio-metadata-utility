import openstudio
import os
from openstudio_metadata_utility.translator import Translator
import tasty.graphs as tg
import tasty.constants as tc

file_name = 'smallHotel.osm'
building_name = file_name.replace('.osm', '')
model = openstudio.model.Model().load(openstudio.path(os.path.join(os.path.dirname(__file__),"data", file_name))).get()

translator = Translator(model, building_name)
graphs = translator.translate()
with open(f"{building_name}_brick.ttl","w") as out:
    out.write(graphs[(tc.BRICK, tc.V1_2)].serialize(format='turtle').decode('utf-8'))

with open(f"{building_name}_haystack.json","w") as out:
    out.write(tg.graph_to_hayson_string(graphs[(tc.HAYSTACK, tc.V3_9_10)]))