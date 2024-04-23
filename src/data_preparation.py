# load basic packages
import re
import math
import json
from functools import partial
import time
import os
import random

# import openai

# Get the directory of the executed script
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
# Set the current working directory to the script directory
os.chdir(project_dir)

# local functions
from chatgpt_client import ChatGPTClient
from neo4j_client import Neo4jClient
import openai
############## FUNCTIONS ##############

def get_templates_and_descriptions(template_path):
    """
    Get the templates and descriptions from the template file
    :param template_path: str: the path to the template file
    :return: list: templates, descriptions, key_list
    """
    with open(template_path, 'r') as f:
        files = json.load(f)
    templates = []
    descriptions = []
    key_list = []
    for f in files.items():
        key = f[0]
        for pair in f[1]:
            key_list.append(key)
            temp, desc = pair.split('|')
            templates.append(temp.strip())
            descriptions.append(desc.strip())
    return templates, descriptions, key_list


def create_gold_template(save_path=None, templates_path=None, templates=None, descriptions=None):
    """
    Create the gold template file
    :param save_path: str: the path to save the gold template file
    :param templates_path: str: the path to the templates
    :param templates: list: the list of templates
    :param descriptions: list: the list of descriptions
    :return: None
    """
    # Get the directory of the executed script
    if templates is None or descriptions is None:
        template_path = templates_path + '/data/design_template.json'
        templates, descriptions, key_list = get_templates_and_descriptions(template_path)

    # initialize the dictionary
    gold_templates = {}
    # save templates and descriptions to file
    if save_path == None:
        key_list_save_path = './data/graph/key_list.json'
        gold_templates_save_path = './data/graph/gold_templates.json'
        # id2templates and id2descriptions
        id2descriptions_save_path = './data/graph/id2descriptions.json'
        descriptions2id_save_path = './data/graph/descriptions2id.json'
        id2templates_save_path = './data/graph/id2templates.json'
        templates2id_save_path = './data/graph/templates2id.json'

    else:
        key_list_save_path = save_path + '/key_list.json'
        gold_templates_save_path = save_path + '/gold_templates.json'
        id2descriptions_save_path = save_path + '/id2descriptions.json'
        descriptions2id_save_path = save_path + '/descriptions2id.json'
        id2templates_save_path = save_path + '/id2templates.json'
        templates2id_save_path = save_path + '/templates2id.json'

    id2templates = {}
    templates2id = {}
    id2descriptions = {}
    descriptions2id = {}
    for ix, temp in enumerate(templates):
        desc = descriptions[ix]
        # create the dictionary
        gold_templates[temp] = desc
        id2templates[ix] = temp
        id2descriptions[ix] = desc
        templates2id[temp] = ix
        descriptions2id[desc] = ix

    with open(gold_templates_save_path, 'w') as f:
        f.write(json.dumps(gold_templates))

    with open(key_list_save_path, 'w') as f:
        f.write(json.dumps(key_list))

    with open(id2templates_save_path, 'w') as f:
        f.write(json.dumps(id2templates))

    with open(id2descriptions_save_path, 'w') as f:
        f.write(json.dumps(id2descriptions))

    with open(templates2id_save_path, 'w') as f:
        f.write(json.dumps(templates2id))

    with open(descriptions2id_save_path, 'w') as f:
        f.write(json.dumps(descriptions2id))

def clear_relation(data):
    """
    Clear the relationship data
    :param data: the relationship data
    :return: the cleared relationship data
    """
    if "properties" in data:
        if len(data["properties"]) >0:
            data["properties"] = {key: {"type": value["type"]} for key, value in data["properties"].items()}
    else:
        data["properties"] = {}
    data = {key: value for key, value in data.items() if key in ['properties',"direction","labels","type"]}
    return data

def clear_node(data):
    """
    Clear the node data
    :param data: the node data
    :return: the cleared node data
    """
    if "properties" in data:
        if len(data["properties"]) > 0:
            data["properties"] = {key: {"type": value["type"]} for key, value in data["properties"].items()}
    else:
        data["properties"] = {}

    if "relationships" in data:
        if len(data["relationships"]) > 1:
            data["relationships"] = {key: clear_relation(value) for key, value in data["relationships"].items() if value['count']>0}
    else:
        data["relationships"] = {}
    data = {key: value for key, value in data.items() if key in ['relationships',"direction","labels","type","properties"]}
    return data

def create_schema_file():
    """
    Create the schema file
    :return: None
    """
    driver = neo4j_client._connect_to_neo4j()
    schema_query = "CALL apoc.meta.schema()"
    # schema_query = "CALL apoc.meta.stats YIELD labels, relTypes"
    schema = {}
    node_rel_schema = {"node":[],"rel":[]}
    rel2node = {}
    property_dict = {}
    all_triplets = []

    with driver.session(database="neo4j") as session:
        # Use .data() to access the results array
        query_result = session.run(schema_query).data()

    # schema file
    raw_schema = query_result[0]['value']
    create_outputfile('raw_schema.json', raw_schema)
    get_key = ['type', 'properties']
    for key in raw_schema.keys():
        value = raw_schema[key]

        _type = raw_schema[key]['type']
        if _type == "relationship":
            node_rel_schema['rel'].append(key)
            value = clear_relation(value)

            if value['properties'] !={}:
                if key in property_dict.keys():
                    property_dict[key].update(value['properties'])
                else:
                    property_dict[key] = {k:value[k] for k in get_key if k in value.keys()}

        if _type == "node":
            if key == '_Neodash_Dashboard':  # remove '_Neodash_Dashboard'
                continue
            node_rel_schema['node'].append(key)
            value = clear_node(value)
            if value['relationships'] != {}:
                for rel in value['relationships'].keys():
                    for object in value['relationships'][rel]['labels']:
                        all_triplets.append(f"{key}--{rel}--{object}")
            if key in property_dict.keys():
                property_dict[key].update(value['properties'])
            else:
                property_dict[key] = {k: value[k] for k in get_key if k in value.keys()}

            for k,v in value['relationships'].items():
                if k in rel2node.keys():
                    rel2node[key].add(v['labels'])
                else:
                    rel2node[key] = set(v['labels'])
            for k,v in rel2node.items():
                rel2node[k] = list(v)

        schema[key] = value

    create_outputfile('schema.json', schema)
    create_outputfile('node_rel_schema.json', node_rel_schema)
    create_outputfile('rel2node.json', rel2node)
    create_outputfile("property_keys.json", property_dict)
    create_outputfile('schema_triplets.json', list(set(all_triplets)))









def percentile(data, perc: int):
    '''
    :param data: list of numbers
    '''
    size = len(data)
    return sorted(data)[int(math.ceil((size * perc) / 100)) - 1]

def sep_nodes_relations(relations_triplet):
    '''
    :param relations_triplet: list of relations
    '''
    relations_ls, nodes_ls = [], []

    for item in relations_triplet:
        rel = item[item.find('[') + 1:item.find(']')]
        rel = rel[1:]  # remove ':' in str
        relations_ls.append(rel)

        two_nodes = [re.findall('\((.*?)\)', item)]
        if two_nodes[0][0] != '':
            two_nodes[0][0] = two_nodes[0][0][1:]  # remove ':' in str
        if two_nodes[0][1] != '':
            two_nodes[0][1] = two_nodes[0][1][1:]  # remove ':' in str
        nodes_ls.extend(two_nodes)

    rel_set = list(set(relations_ls))
    # get the indexes of the same relations in the list of rels and nodes
    # temp = {'rel':[['sub1','obj1'], ['sub2','obj2']]}
    # combine = {'rel':{ 'sub1':['obj1', 'obj3'], 'sub2':['obj2'] } }

    temp, combine = {}, {}
    for i in range(len(rel_set)):
        uni_rel_indices = [j for j, x in enumerate(relations_ls) if x == rel_set[i]]

        temp[rel_set[i]] = []
        for idx in uni_rel_indices:
            temp[rel_set[i]].append(nodes_ls[idx])

    for key, value in temp.items():
        combine[key] = {}
        subjects = [item[0] for item in value]
        objects = [item[1] for item in value]

        for i in range(len(subjects)):
            combine[key][subjects[i]] = []

        for i in range(len(subjects)):
            combine[key][subjects[i]].append(objects[i])

    return combine


def export_properties(save_path):
    '''
    Extract the numeric properties from the Neo4j database and export it to the data/graph directory.
    :param save_path: the path to save the output files
    '''
    filename = save_path + 'property_keys.json'
    with open(filename) as file:
        property_data = json.load(file)
    keys = property_data.keys()

    driver = neo4j_client._connect_to_neo4j()
    prop_stats = {}

    with driver.session(database="neo4j") as session:
        for key in keys:
            if property_data[key]['type'] == 'relationship':
                num_query = 'CALL apoc.meta.relTypeProperties({includeRels: ["key"]});'
                # continue
            if property_data[key]['type'] == 'node':
                num_query = 'CALL apoc.meta.nodeTypeProperties({includeLabels: ["key"]});'

            num_query = num_query.replace('key', key)
            type_result = session.run(num_query).data()
            node_prop_dict = {}

            for i in type_result:
                if i == {}:
                    continue
                if property_data[key]['type'] == 'relationship':
                    prop_query = 'MATCH ()-[r: Label1]->() RETURN collect(r.property1) as prop'
                if property_data[key]['type'] == 'node':
                    prop_query = 'MATCH (n: Label1) RETURN collect(n.property1) as prop'
                temp_ls = []
                try:
                    if 'id' in i['propertyName']:
                        i['propertyTypes'] = ['String']
                except:
                    # print(i)
                    continue
                prop_query = prop_query.replace('Label1', key)
                prop_query = prop_query.replace('property1', i['propertyName'])
                prop_result = session.run(prop_query).data()
                ls_result = prop_result[0]['prop']
                if 'Double' in i['propertyTypes'] or 'Long' in i['propertyTypes']:
                    ls_result = [x for x in ls_result if type(x) is not str]
                    min_value = min(ls_result)
                    min_fifth = percentile(ls_result, 5)
                    twenty_fifth = percentile(ls_result, 25)
                    fiftith = percentile(ls_result, 50)
                    senventy_fifth = percentile(ls_result, 75)
                    max_ninety_fifth = percentile(ls_result, 95)
                    max_value = max(ls_result)

                    if math.isnan(twenty_fifth) or math.isnan(fiftith) or math.isnan(senventy_fifth):
                        break
                    else:
                        temp_ls.append(round(min_value, 3))
                        temp_ls.append(round(min_fifth, 3))
                        temp_ls.append(round(twenty_fifth, 3))
                        temp_ls.append(round(fiftith, 3))
                        temp_ls.append(round(senventy_fifth, 3))
                        temp_ls.append(round(max_ninety_fifth, 3))
                        temp_ls.append(round(max_value, 3))
                    if i['propertyName'] not in node_prop_dict.keys():
                        node_prop_dict[i['propertyName']] = list(set(temp_ls))
                    else:
                        node_prop_dict[i['propertyName']].extend(temp_ls)
                        node_prop_dict[i['propertyName']] = list(set(node_prop_dict[i['propertyName']]))
                elif i['propertyTypes'] == ['String']:
                    ls_result = set(x for x in ls_result if type(x) is str and len(x) < 100)
                    #
                    if len(ls_result) <= 1:
                        break
                    else:
                        if len(ls_result) < 10:
                            k = len(ls_result)
                        else:
                            k = 10
                    temp_ls = random.choices(list(set(ls_result)),k=k)
                    if i['propertyName'] not in node_prop_dict.keys():
                        node_prop_dict[i['propertyName']] = list(set(temp_ls))
                    else:
                        node_prop_dict[i['propertyName']].extend(temp_ls)
                        node_prop_dict[i['propertyName']] = list(set(node_prop_dict[i['propertyName']]))

                    # prop_stats[i['nodeLabels'][0]] = {i['propertyName']:temp_ls}
                prop_stats[key] = node_prop_dict
    driver.close()
    create_outputfile('properties_quantile.json', prop_stats)

def create_outputfile(filename, data, save_path= './data/graph/'):
    '''
    Create the output file.
    :param filename: the name of the output file
    :param data: the data to be saved
    :param save_path: the path to save the output files
    '''
    with open(save_path + filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def get_label_information(label):
    # get the label index
    label_index = label[0]
    value_index = label[-1]
    return label_index, value_index

def check_relation(rel_string, current_template, relation_ls, property_data, propStats_data,schema, condition_label=False):
    rel_index = rel_string[:2]
    if len(rel_string) > 2:
        value_index = rel_string[3:5]
    else:
        value_index = None
    relation = False

    if condition_label:
        relation_pool = list(schema[condition_label]['relationships'].keys())
        if relation_pool == []:
            is_break = True
            return current_template, relation, is_break
    else:
        relation_pool = relation_ls
    num_property = current_template.count(rel_index + ".property") - current_template.count("{" + rel_index + ".property")
    if num_property !=0:
        relation_pool = set(relation_pool) & set(property_data.keys())
        if relation_pool == set():
            is_break = True
            return current_template, relation, is_break

    relation = random.choice(list(relation_pool))

    is_break = False
    property_exist = []

    if value_index is None and num_property == 0:
        return current_template, relation, is_break
    if num_property == 0:
        current_template = current_template.replace(value_index, relation)
        return current_template, relation, is_break
    try:
        property_pool = list(property_data[relation]['properties'].keys())
    except:
        is_break = True
        return current_template, relation, is_break

    for i in range(1, 1 + num_property):
        property_label = rel_index + ".property" + str(i)
        if property_label in current_template:
            property = random.choice(property_pool)
            property_type = property_data[relation]['properties'][property]['type']

            property_exist.append(property)
            property_pool = list(set(property_pool) - set(property_exist))

            property_pattern = r'(min|max|avg)\({}\)'.format(property_label)
            property_matches = re.findall(property_pattern, current_template)
            current_template = current_template.replace("property" + str(i), property)
            if property_matches:
                if relation not in propStats_data.keys() or property not in propStats_data[relation].keys():
                    is_break = True
                    return current_template, relation, is_break
                if property_type == 'STRING':
                    is_break = True
                    return current_template, relation, is_break

            num_property_values = current_template.count("{" + f"{rel_index}.{property}.")
            for j in range(1, 1 + num_property_values):
                if "{" + f"{rel_index}.{property}.Value" + str(j) + "}" in current_template:
                    if relation not in propStats_data.keys() or property not in propStats_data[relation].keys():
                        is_break = True
                        return current_template, relation, is_break
                    value = random.choice(propStats_data[relation][property])
                    value_pattern = re.compile(r'[<>=!]=?\s*{' + f"{rel_index}.{property}.Value" + str(j) + '}')
                    matches = value_pattern.findall(current_template)
                    for m in matches:
                        if '>' in m or '<' in m:
                            if "<>" not in m:
                                if property_type == 'STRING':
                                    is_break = True
                                    return current_template, relation, is_break
                            current_template = current_template.replace("{" + f"{rel_index}.{property}.Value" + str(j) + "}", str(value))
                        else:
                            current_template = current_template.replace("{" + f"{rel_index}.{property}.Value" + str(j) + "}", f"\"{str(value)}\"")

                    string_pattern = r'[^a-zA-Z0-9]+'
                    if "{" + f"{rel_index}.{property}.Prefix" + str(j) + "}" in current_template:
                        if relation not in propStats_data.keys() or property not in propStats_data[relation].keys() or property_type != 'String':
                            is_break = True
                            return current_template, relation, is_break
                        value = random.choice(propStats_data[property])
                        if len(value) < 4:
                            is_break = True
                            return current_template, relation, is_break
                        substrings = re.split(string_pattern, value)
                        if len(substrings) > 1:
                            value = substrings[0]
                        else:
                            value = value[:2]
                        current_template = current_template.replace("{" + f"{rel_index}.{property}.Prefix" + str(j) + "}",  f"\"{str(value)}\"")
                    if "{" + f"{rel_index}.{property}.Suffix" + str(j) + "}" in current_template:
                        if relation not in propStats_data.keys() or property not in propStats_data[relation].keys() or property_type != 'String':
                            is_break = True
                            return current_template, relation, is_break
                        value = random.choice(propStats_data[property])
                        if len(value) < 4:
                            is_break = True
                            return current_template, relation, is_break
                        substrings = re.split(string_pattern, value)
                        if len(substrings) > 1:
                            value = substrings[-1]
                        else:
                            value = value[-2:]
                        current_template = current_template.replace("{" + f"{rel_index}.{property}.Suffix" + str(j) + "}",  f"\"{str(value)}\"")
                    if "{" + f"{rel_index}.{property}.Substring" + str(j) + "}" in current_template:
                        if relation not in propStats_data.keys() or property not in propStats_data[relation].keys() or property_type != 'STRING':
                            is_break = True
                            return current_template, relation, is_break
                        value = random.choice(propStats_data[property])
                        if len(value) < 4:
                            is_break = True
                            return current_template, relation, is_break
                        substrings = re.split(string_pattern, value)
                        if len(substrings) > 1:
                            value = random.choice(substrings)
                        else:
                            start_index = random.randint(0, len(value) - 1)
                            max_length = min(len(value) - start_index, 20)
                            length = random.randint(1, max_length)
                            value = value[start_index:start_index + length]
                        current_template = current_template.replace("{" + f"{rel_index}.{property}.Substring" + str(j) + "}", f"\"{str(value)}\"")
    return current_template, relation, is_break

def check_label(label_string, current_template, label_ls, property_data, propStats_data, schema, condition_relation=False,pre_label=False):
    if 'Label' in pre_label and condition_relation:
        label_pool = schema[pre_label]['relationships'][condition_relation]['labels']
    else:
        label_pool = label_ls
    label = random.choice(label_pool)
    label_index, value_index = get_label_information(label_string)
    num_property = current_template.count(label_index + ".property") - current_template.count("{" + label_index + ".property")
    property_pool = list(property_data[label]['properties'].keys())
    is_break = False
    property_exist = []
    if len(property_pool) < num_property:
        is_break = True
        return current_template,label,is_break
    if ':' in label_string:
        current_template = current_template.replace(label_string, label_index + ":" + label)
    if num_property == 0:
        return current_template, label, is_break
    for i in range(1,1+ num_property):
        property_label = label_index + ".property" + str(i)
        # replace_label = "property" + str(i)
        if property_label in current_template:
            property = random.choice(property_pool)
            # print(property_data[label][property])
            property_type = property_data[label]['properties'][property]['type']
            property_exist.append(property)
            property_pool = list(set(property_pool) - set(property_exist))
            property_pattern = r'(min|max|avg)\({}\)'.format(property_label)
            property_matches = re.findall(property_pattern, current_template)
            if property_matches:
                if label not in propStats_data.keys() or property not in propStats_data[label].keys():
                    is_break = True
                    return current_template, label, is_break
                if property_type == 'STRING':
                    is_break = True
                    return current_template, label, is_break
            current_template = current_template.replace(property_label, label_index + '.' + property)
            num_property_values = current_template.count("{" + f"{label_index}.{property}.")
            for j in range(1, 1 + num_property_values):
                if "{" + f"{label_index}.{property}.Value" + str(j) + "}" in current_template:
                    if label not in propStats_data.keys() or property not in propStats_data[label].keys():
                        is_break = True
                        return current_template, label, is_break
                    value = random.choice(propStats_data[label][property])
                    value_pattern = re.compile(r'[<>=!]=?\s*{' + f"{label_index}.{property}.Value" + str(j) + '}')
                    matches = value_pattern.findall(current_template)
                    for m in matches:
                        if '>' in m or '<' in m:
                            if "<>" not in m:
                                if property_type == 'STRING':
                                    is_break = True
                                    return current_template, label, is_break
                            current_template = current_template.replace("{" + f"{label_index}.{property}.Value" + str(j) + "}", str(value))
                        current_template = current_template.replace(
                            "{" + f"{label_index}.{property}.Value" + str(j) + "}",  f"\"{str(value)}\"")
                    if property_type == 'STRING':
                        current_template = current_template.replace("{" + f"{label_index}.{property}.Value" + str(j) + "}", f"\"{str(value)}\"")
                    else:
                        current_template = current_template.replace("{" + f"{label_index}.{property}.Value" + str(j) + "}", str(value))

                string_pattern = r'[^a-zA-Z0-9]+'
                if "{" + f"{label_index}.{property}.Prefix" + str(j) + "}" in current_template:
                    print(label,property,property_type)
                    if label not in propStats_data.keys() or property not in propStats_data[label].keys() or property_type != 'STRING':
                        is_break = True
                        return current_template, label, is_break
                    value = random.choice(propStats_data[label][property])
                    value = str(value)
                    if len(value) < 4:
                        is_break = True
                        return current_template, label, is_break
                    substrings = re.split(string_pattern, value)
                    if len(substrings) > 1:
                        value = substrings[0]
                    else:
                        value = value[:2]
                    current_template = current_template.replace("{" + f"{label_index}.{property}.Prefix" + str(j) + "}", f"\"{str(value)}\"")
                if "{" + f"{label_index}.{property}.Suffix" + str(j) + "}" in current_template:
                    if label not in propStats_data.keys() or property not in propStats_data[label].keys() or property_type != 'STRING':
                        is_break = True
                        return current_template, label, is_break
                    value = random.choice(propStats_data[label][property])
                    value = str(value)
                    if len(value) < 4:
                        is_break = True
                        return current_template, label, is_break
                    substrings = re.split(string_pattern, value)
                    if len(substrings) > 1:
                        value = substrings[-1]
                    else:
                        value = value[-2:]
                    current_template = current_template.replace("{" + f"{label_index}.{property}.Suffix" + str(j) + "}", f"\"{str(value)}\"")
                if "{" + f"{label_index}.{property}.Substring" + str(j) + "}" in current_template:
                    if label not in propStats_data.keys() or property not in propStats_data[label].keys() or property_type != 'STRING':
                        is_break = True
                        return current_template, label, is_break
                    value = random.choice(propStats_data[label][property])
                    value = str(value)
                    if len(value) < 4:
                        is_break = True
                        return current_template, label, is_break
                    substrings = re.split(string_pattern, value)
                    if len(substrings) > 1:
                        value = random.choice(substrings)
                    else:
                        start_index = random.randint(0, len(value) - 1)
                        max_length = min(len(value) - start_index, 20)  # Limit the max length to 20 characters
                        length = random.randint(1, max_length)
                        value = value[start_index:start_index + length]
                    current_template = current_template.replace("{" + f"{label_index}.{property}.Substring" + str(j) + "}", f"\"{str(value)}\"")
                
    return current_template, label, is_break
def create_template(save_path= './data/graph/',max_example_number=5):
    '''
    Create the template.json file.
    :param save_path: the path to save the output files
    :param max_example_number: the maximum number of examples for each template
    '''
    schema_save_path = save_path + 'schema.json'
    template_save_path = save_path + 'gold_templates.json'
    nodeRelSchema_save_path = save_path + 'node_rel_schema.json'
    propertyKeys_save_path = save_path + 'property_keys.json'
    propertiesQuantile_save_path = save_path + 'properties_quantile.json'
    rel2node_save_path = save_path + 'rel2node.json'
    key_list_save_path = save_path + 'key_list.json'

    # data = {'template':['description', 'ex1', 'ex2']}
    with open(template_save_path) as file:
        data = json.load(file)
        templates = list(data.keys())
        descriptions = list(data.values())
    with open(key_list_save_path) as file:
        key_list = json.load(file)
    with open(schema_save_path) as file:
        schema = json.load(file)
        # print(schema)

    with open(nodeRelSchema_save_path) as file:
        node_rel_schema = json.load(file)
        label_ls = node_rel_schema['node']
        rel_ls = node_rel_schema['rel']

    with open(rel2node_save_path) as file:
        rel2node = json.load(file)

    with open(propertyKeys_save_path) as file:
        property_data = json.load(file)

    with open(propertiesQuantile_save_path) as file:
        propStats_data = json.load(file)

    template_data = {}
    for i in range(len(templates)):
        k = 0
        ex = []
        structure_pattern = r' [\[(](.*?)[\])]'
        ex.append(descriptions[i])
        ex.append(key_list[i])
        iter = 0
        while k < max_example_number:
            iter += 1
            if iter > 100:
                break
            current_template = templates[i]
            # current_template = 'MATCH (n:Label1) WHERE n.property1 IN [{n.property1.Value1}, {n.property1.Value2}, {n.property1.Value3}] RETURN n'
            current_template_structure = re.findall(structure_pattern, current_template.replace('->','-').replace('-',' ').split('RETURN')[0])
            current_template_structure = [x for x in current_template_structure if x != '']
            label = False
            is_break = False
            relation = False
            second_label = ''
            save_sign = True
            # print(current_template_structure)
            # print(current_template)
            for ix, element in enumerate(current_template_structure):
                if "Label" in element or 'x'== element:
                    current_template,label,is_break = check_label(element,current_template=current_template,
                                                                        label_ls=label_ls,property_data=property_data,
                                                                        propStats_data=propStats_data,schema=schema,condition_relation=relation,pre_label=second_label)
                    if ix > 1 and "Label" in current_template_structure[ix-2]:
                        second_label = label
                if is_break:
                    break
                rel_filter = r'r\d'
                rel_match = re.search(rel_filter, element)
                if rel_match:
                    current_template, relation,is_break = check_relation(element,current_template=current_template,
                                                                            relation_ls=rel_ls,property_data=property_data,
                                                                            propStats_data=propStats_data,schema=schema,condition_label=label)
                if is_break:
                    break

            for element in current_template_structure:
                if element in current_template.split('RETURN')[0]:
                    if 'r' not in element and 'x' not in element:
                        save_sign = False
                        break
                if 'R' in element and element in current_template.split('RETURN')[0]:
                    save_sign = False
                    break

            filters = [r'Value\d', r'Prefix\d', r'Substring\d', r'Suffix\d' , r'property\d']
            for filter_pattern in filters:
                if re.search(filter_pattern, current_template):
                    save_sign = False

            if save_sign and current_template not in ex:
                ex.append(current_template)
                print(current_template)
                print(k)
                k += 1

        template_data[templates[i]] = ex
    create_outputfile('template.json', template_data)

def get_relation_labels(label,current_template_structure):
    label_index = 0
    for i, element in enumerate(current_template_structure):
        if label in element:
            label_index = i
            break
    # get relation before label2
    relation_label = current_template_structure[label_index - 1]
    return relation_label

def get_rellabels(relations_dict):
    '''
    :param relations_dict: the relations dictionary
    '''
    ls = []
    # {rel:{sub:[obj]}}
    # [[sub, rel, obj],[sub, rel, obj]]
    for key in relations_dict.keys():
        temp = []
        for inside_key in relations_dict[key].keys():
            for value in relations_dict[key][inside_key]:
                temp.append(inside_key)
                temp.append(key)
                temp.append(value)
                ls.append(temp)
                temp = []
    # print(ls)
    return ls


############## TESTING ##############
def generate_cypher_query(verbalization):
    # Use the ChatGPT client to generate a Cypher query based on the natural language description and additional
    # instructions
    with open('data/schema.json') as f:
        schema = json.load(f)
    with open('data/property_keys.json') as g:
        property_keys = json.load(g)

    prompt = f"""          
        Given the Neo4j schema delimited with tripple dashes, and the property key delimited with ope angle brackets,
        generate a cypher query corresponding to the verbalization delimited with triple backticks and using the 
        following additional instructions separated with triple underscores:          

        Schema: ---{schema}---          

        Property keys: <<<{property_keys}>>>  

        Query verbalization: ```{verbalization}```      

        The output should a cypher_query and nothing else.

        [no prose]
        """

    cypher_query = chat_gpt_client.get_completion(prompt=prompt)
    return cypher_query

def simple_describe_cypher_query(query, temprature=0.5):
    prompt = f"""
        I want you to act as a Neo4j specialist. I will supply you with a Cypher query that needs to be explained in a simple manner, suitable for someone without any knowledge of databases.
        Please write a user-friendly question for the given query in one sentence, ensuring it is concise, easily understandable, and avoids technical jargon.
        The question should not start the description with "This query..." or "The query..." and do not mention the database or network.
    [Query]: ```{query}```.
    [Question]: 
    """
    description = chat_gpt_client.get_completion(prompt=prompt, temperature=temprature)
    return description

def example_describe_cypher_query(query, temprature=0.5):
    with open('data/graph/schema.json') as f:
        schema = json.load(f)

    prompt = f"""      
I want you to act as a Neo4j specialist. I will supply you with the schema of the database and a Cypher query that needs to be explained in a simple manner, suitable for someone without any knowledge of databases.
Please write a user-friendly question for the given query in one sentence, ensuring it is concise, easily understandable, and avoids technical jargon.
The question should not start the description with "This query..." or "The query..." and do not mention the database or network.
The schema is delimited with tripple dashes. I will supply you with tree examples of questions and answers. Each example contains a [Query] and an [Question]. In the end you need to supply a question for the given query.
Schema: ---{schema}---  
Example:
[Query]: ```MATCH (n)-[r:RELATED_TO]->(m:Supplier) RETURN n,m```
[Question]: Which items are related to suppliers, and can you show me both the items and their respective suppliers?
[Query]: ```MATCH (n)-[r]->(m:ManufacturerPart) RETURN n, r```
[Question]: What are the things connected to manufacturer parts, and how are they related to each other?
[Query]: ```MATCH (n:BusinessPartner) WITH min(n.supplier_triangles_norm) AS minPropertyValue RETURN minPropertyValue```
[Question]: What is the smallest "supplier_triangles_norm" value among all the Business Partners?
[Query]: ```MATCH (n:Branch)-[r1]->(m:Branch) RETURN COUNT(r1)```
[Question]: How many connections exist between different branches?
[Query]: ```{query}```         
[Question]: 
"""
    description = chat_gpt_client.get_completion(prompt=prompt, temperature=temprature)
    return description

def schema_describe_cypher_query(query, temprature=0.5):
    with open('data/graph/schema.json') as f:
        schema = json.load(f)

    prompt = f"""
I want you to act as a Neo4j specialist. I will supply you with the schema of the database and a Cypher query that needs to be explained in a simple manner, suitable for someone without any knowledge of databases.
Please write a user-friendly question for the given query in one sentence, ensuring it is concise, easily understandable, and avoids technical jargon.
The question should not start the description with "This query..." or "The query..." and do not mention the database or network.
The schema is delimited with tripple dashes. 
Schema: ---{schema}---      
[Query]:  ```{query}```               
[Question]: 
        """
    description = chat_gpt_client.get_completion(prompt=prompt, temperature=temprature)
    return description

def describe_cypher_query(description_ls, template, temprature = 0.5):
    prompt = f"""I want you to act as a Neo4j specialists, I will supply you with a Cypher query and three questions that could be answered by the query. 
    Please evaluate the coherence and quality of these questions and keep the best one, you are
    allowed to edit the question if you think it is necessary, but keep the meaning of the question. 
    Then return the best description and two other descriptions that paraphrase the best description.
    The paraphrase descriptions should be different from the best description, but they should have the same meaning. 
    The format of paraphrase descriptions should only be the paraphrase description itself, without any other information.
    For example: ' paraphrase_This query will list all SiemensParts' is not a valid paraphrase description, just 'This query will list all SiemensParts' is a valid paraphrase description.
    
    The return format should be a string with the following format:
    best_description|paraphrase_description1|paraphrase_description2.
    
    Neo4j Cypher query: {template}
    Description 1: {description_ls[0]}
    Description 2: {description_ls[1]}
    Description 3: {description_ls[2]}
    Final description:"""
    description = chat_gpt_client.get_completion(prompt=prompt, temperature=temprature)
    return description

def get_template(file_name):
    temp_ls = []
    query_ls = []
    with open(file_name) as f:
        schema = json.load(f)

    for k in schema.keys():
        temp = schema[k]
        temp = temp[2:]

        query_ls.extend([k]*len(temp))
        temp_ls.extend(temp)

    return temp_ls,query_ls

def compare_results(template, generated):
    indices = len(template)

    for i in range(indices):
        if template[i] == generated[i]:
            # print('yes',template[i],generated[i])
            print('yes')
        else:
            # print('no',template[i],generated[i])
            print('no')
    # todo: compare results and save queries

def clean_schema(input_data):
    cleaned_data = []
    for entry in input_data:
        cleaned_entry = {}
        for key, value in entry.items():
            if isinstance(value, list):
                cleaned_entry[key] = []
                for sub_entry in value:
                    cleaned_sub_entry = {}
                    for sub_key in sub_entry.keys():
                        cleaned_sub_entry[sub_key] = {}
                    cleaned_entry[key].append(cleaned_sub_entry)
        cleaned_data.append(cleaned_entry)
    return cleaned_data

def create_test_dataset(save_path,temperture=0):
    # TESTING
    # load template json
    template_ls,query_ls = get_template(save_path + 'template.json')
    # # delete duplicate
    # template_ls = list(dict.fromkeys(template_ls))
    with open(save_path + 'key_list.json') as f:
        key_list = json.load(f)
    with open(save_path + '/templates2id.json') as f:
        template2id = json.load(f)

    try:
        with open('/Users/bailanhe/PycharmProjects/siemens/gitlab/query-generator/data/graph/template_description_249_20231105-102819.json') as f:
            template_description = json.load(f)
    except:
        template_description = None



    query_id_ls = [template2id[x] for x in query_ls]
    description_ls, cypher_ls = [], []
    output_json = {}
    # count running time
    start_time = time.time()
    idx = 0
    max_explore_number = 10
    explore_number = 0

    if template_description:
        idx = len(template_description)

        description_ls = list(template_description.values())

    while idx < len(template_ls):

        template = template_ls[idx]
        temp = []
        query_id = query_id_ls[idx]
        key = key_list[query_id]
        temp.append(query_id)
        time.sleep(4)
        temp.append(simple_describe_cypher_query(template, temperture).strip(" "))
        time.sleep(4)
        temp.append(schema_describe_cypher_query(template, temperture).strip(" "))
        time.sleep(4)
        temp.append(example_describe_cypher_query(template, temperture).strip(" "))

        three_description = describe_cypher_query(temp, template, temperture).strip(" ")
        three_description = three_description.split('|')
        try:
            assert len(three_description) == 3
            # string should not contain "paraphrase"
            assert 'paraphrase' not in three_description[0] and "Paraphrase" not in three_description[0]
            assert 'paraphrase' not in three_description[1] and "Paraphrase" not in three_description[1]
            assert 'paraphrase' not in three_description[2] and "Paraphrase" not in three_description[2]
            assert ':' not in three_description[0] and ':' not in three_description[1] and ':' not in three_description[2]
            # assert '_' not in three_description[0] and '_' not in three_description[1] and '_' not in three_description[2]
            three_description = [query_id] + three_description
            description_ls.append([key, three_description])
            print(f"{idx}:{[key, three_description]}")
            idx += 1
        except:
            print(f"template is not valid:{idx}:{three_description} ")
            explore_number += 1
            if explore_number >= max_explore_number:
                explore_number = 0
                print("explore number is too large, skip this template{idx}:{template}")
                description_ls.append([key, []])
                idx += 1
        if idx % 50 == 0:
            for i in range(len(description_ls)):
                output_json[template_ls[i]] = description_ls[i]
                template_description_save_path = 'template_description'+ '_' + str(idx-1) +'_' + time.strftime("%Y%m%d-%H%M%S") + '.json'
            create_outputfile(template_description_save_path, output_json)

    print("--- %s seconds ---" % (time.time() - start_time))
    for i in range(len(description_ls)):
        output_json[template_ls[i]] = description_ls[i]
        template_description_save_path = 'template_description' + time.strftime("%Y%m%d-%H%M%S") + '.json'
    create_outputfile(template_description_save_path, output_json)


if __name__ == "__main__":
    # Read the API credentials from the file
    with open('app/api_credentials.json') as f:
        api_credentials = json.load(f)

    deployment_name = api_credentials['deployment_name']
    openai_api_key = api_credentials['openai_api_key']
    openai_api_base = api_credentials['openai_api_base']
    openai_api_version = api_credentials['openai_api_version']

    # Read the neo4j specifications
    with open('app/neo4j_specifications.json') as f:
        neo4j_specifications = json.load(f)

    neo4j_uri = neo4j_specifications['uri']
    neo4j_user = neo4j_specifications['user']
    neo4j_password = neo4j_specifications['password']
    neo4j_database = neo4j_specifications['database']

    # Define the ChatGPT client
    chat_gpt_client = ChatGPTClient(deployment_name=deployment_name, api_key=openai_api_key, api_base=openai_api_base,
                                    api_version=openai_api_version)
    # Define the Neo4j client
    neo4j_client = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password, database=neo4j_database)

    save_path = './data/graph/'
    create_outputfile = partial(create_outputfile, save_path= save_path)

    # Create the directory if it doesn't exist
    os.makedirs(save_path, exist_ok=True)
    create_schema_file()
    create_gold_template(save_path = save_path, templates_path=project_dir)
    export_properties(save_path)
    # create template
    create_template(save_path)
    create_test_dataset(save_path,temperture=0.3)