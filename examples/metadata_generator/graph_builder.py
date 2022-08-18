import os

import openstudio

from openstudio_metadata_utility.translator import Translator
import tasty.graphs as tg
import tasty.constants as tc


def version_translate(osm_path):
    version_translator = openstudio.osversion.VersionTranslator()
    if openstudio.exists(osm_path):
        model = version_translator.loadModel(osm_path)
        if not model:
            print(f"cannot translate model version")
        else:
            return model.get()
    else:
        print(f"model not found at path = {osm_path}")


translator = Translator()

def translate_model(translator, file_name):
    building_name = file_name.replace('.osm', '')
    osm_path = openstudio.path(os.path.join(os.path.dirname(__file__),"data", file_name))
    model = version_translate(osm_path)
    if model:
        if not os.path.isdir(f'outputs/{building_name}'):
            if not os.path.isdir(f'outputs'):
                os.mkdir(f'outputs')
            os.mkdir(f'outputs/{building_name}')
        graphs = translator.translate(model, building_name)
        with open(f"outputs/{building_name}/{building_name}_brick.ttl","w") as out:
            out.write(graphs[(tc.BRICK, tc.V1_2_1)].serialize(format='turtle').decode('utf-8'))

        with open(f"outputs/{building_name}/{building_name}_haystack.json","w") as out:
            out.write(tg.graph_to_hayson_string(graphs[(tc.HAYSTACK, tc.V3_9_10)]))
    else:
        print(f"cannot translate model to graph")

#translate_model(translator, 'smallOffice.osm')

for file in os.listdir(os.path.join(os.path.dirname(__file__), 'data')):
    if file[-4:] == '.osm':
        print(f'translating {file}')
        translate_model(translator, file)
