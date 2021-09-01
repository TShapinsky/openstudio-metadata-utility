import openstudio
import os
from openstudio_metadata_utility.translator import Translator
import tasty.graphs as tg
import tasty.constants as tc

translator = Translator()

def translate_model(translator, file_name):
    building_name = file_name.replace('.osm', '')
    model = openstudio.model.Model().load(openstudio.path(os.path.join(os.path.dirname(__file__),"data", file_name))).get()

    if not os.path.isdir(f'outputs/{building_name}'):
        if not os.path.isdir(f'outputs'):
            os.mkdir(f'outputs')
        os.mkdir(f'outputs/{building_name}')
    graphs = translator.translate(model, building_name)
    with open(f"outputs/{building_name}/{building_name}_brick.ttl","w") as out:
        out.write(graphs[(tc.BRICK, tc.V1_2_1)].serialize(format='turtle').decode('utf-8'))

    with open(f"outputs/{building_name}/{building_name}_haystack.json","w") as out:
        out.write(tg.graph_to_hayson_string(graphs[(tc.HAYSTACK, tc.V3_9_10)]))

#translate_model(translator, 'smallOffice.osm')

for file in os.listdir(os.path.join(os.path.dirname(__file__), 'data')):
    if file[-4:] == '.osm':
        print(f'translating {file}')
        translate_model(translator, file)
