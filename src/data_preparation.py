# load basic packages
import re
import math
import json
from functools import partial
import time
import os
import random
# Get the directory of the executed script
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
# Set the current working directory to the script directory
os.chdir(project_dir)

# local functions
from chatgpt_client import ChatGPTClient
from neo4j_client import Neo4jClient
from create_gold_template import create_gold_template

############## FUNCTIONS ##############
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

def extract_and_export_graph_info():
    '''
    Extract the graph schema information from the Neo4j database and export it to the data/graph directory.
    '''
    driver = neo4j_client._connect_to_neo4j()

    # Cypher query
    node_labels_query = "MATCH (n) RETURN distinct labels(n) as n"
    relations_query = "CALL apoc.meta.stats YIELD labels, relTypes"
    # TODO -> done
    properties_query = "MATCH (n) UNWIND keys(n) AS key RETURN labels(n)[0] AS label, collect(distinct key) AS propertyKeys UNION MATCH ()-[r]->() UNWIND keys(r) AS key RETURN type(r) AS label, collect(distinct key) AS propertyKeys"

    label_list, relations, properties = [], {}, {}

    # Create a driver session
    with driver.session(database="neo4j") as session:
        # Use .data() to access the results array
        labels_result = session.run(node_labels_query).data()

        for item in labels_result:
            for label in item['n']:
                if label == '_Neodash_Dashboard':  # remove '_Neodash_Dashboard'
                    continue
                else:
                    label_list.append(label)

        relations_result = session.run(relations_query).data()
        relations = relations_result[0]['relTypes']

        properties_result = session.run(properties_query).data()

        for item in properties_result:
            properties[item['label']] = item['propertyKeys']

    # Close the driver connection
    driver.close()

    relations_triplet = list(relations.keys())
    relations_list = sep_nodes_relations(relations_triplet)

    create_outputfile('nodetypes.txt', label_list)
    create_outputfile('nodesRelations.json', relations_list)
    create_outputfile('propertyKeys.json', properties)

def export_numeric_properties(save_path):
    '''
    Extract the numeric properties from the Neo4j database and export it to the data/graph directory.
    :param save_path: the path to save the output files
    '''
    filename = save_path + 'propertyKeys.json'
    with open(filename) as file:
        property_data = json.load(file)
    keys = property_data.keys()

    driver = neo4j_client._connect_to_neo4j()
    prop_stats = {}

    with driver.session(database="neo4j") as session:
        for key in keys:
            num_query = 'CALL apoc.meta.nodeTypeProperties({includeLabels: ["n"]});'

            key = '"' + key + '"'
            num_query = num_query.replace('"n"', key)
            type_result = session.run(num_query).data()

            for i in type_result:
                prop_query = 'MATCH (n: Label1) RETURN collect(n.property1) as prop'
                temp_ls = []
                if 'Double' in i['propertyTypes'] or 'Long' in i['propertyTypes']:
                    prop_query = prop_query.replace('Label1', i['nodeLabels'][0])
                    prop_query = prop_query.replace('property1', i['propertyName'])
                    prop_result = session.run(prop_query).data()
                    ls_result = prop_result[0]['prop']

                    ls_result = [x for x in ls_result if type(x) is not str]
                    
                    twenty_fifth = percentile(ls_result, 25)
                    fiftith = percentile(ls_result, 50)
                    senventy_fifth = percentile(ls_result, 75)

                    if math.isnan(twenty_fifth) or math.isnan(fiftith) or math.isnan(senventy_fifth):
                        break
                    else:
                        temp_ls.append(round(twenty_fifth, 3))
                        temp_ls.append(round(fiftith, 3))
                        temp_ls.append(round(senventy_fifth, 3))

                        prop_stats[i['propertyName']] = list(set(temp_ls))

    driver.close()
    create_outputfile('propertiesQuantile.json', prop_stats)

def create_outputfile(filename, data, save_path= './data/graph/'):
    '''
    Create the output file.
    :param filename: the name of the output file
    :param data: the data to be saved
    :param save_path: the path to save the output files
    '''
    with open(save_path + filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def create_template(save_path= './data/graph/',max_example_number=5):
    '''
    Create the template.json file.
    :param save_path: the path to save the output files
    :param max_example_number: the maximum number of examples for each template
    '''

    template_save_path = save_path + 'gold_templates.json'
    propertyKeys_save_path = save_path + 'propertyKeys.json'
    nodeRelations_save_path = save_path + 'nodesRelations.json'
    propertiesQuantile_save_path = save_path + 'propertiesQuantile.json'
    # data = {'template':['description', 'ex1', 'ex2']}
    with open(template_save_path) as file:
        data = json.load(file)
        templates = list(data.keys())
        descriptions = list(data.values())

    # generate label list
    nodetypes_save_path = save_path + 'nodetypes.txt'
    with open(nodetypes_save_path) as file:
        label_ls = file.read().strip('][').split(', ')
        label_ls = [x.strip('\"') for x in label_ls]

    with open(propertyKeys_save_path) as file:
        property_data = json.load(file)
        # print(property_data)

    with open(nodeRelations_save_path) as file:
        nodeRel_data = json.load(file)
        rel_labels_ls = get_rellabels(nodeRel_data)
        random.shuffle(rel_labels_ls)

    with open(propertiesQuantile_save_path) as file:
        propStats_data = json.load(file)

    template_data = {}
    for i in range(len(templates)):
        k = 0
        ex = []
        ex.append(descriptions[i])

        for triplet in rel_labels_ls:
            if triplet[0] not in property_data:
                continue
            else:
                label = triplet[0]
                query = templates[i].replace("Label1", label)

                if "property1" in templates[i]:
                    temp_idx = 0
                # TODO
                if "num" in templates[i]:
                    if property_data[label][temp_idx] in propStats_data:
                        query = query.replace('num', str(propStats_data[property_data[label][temp_idx]][0]))
                        query = query.replace("property1", property_data[label][temp_idx])
                        
                    else:
                        continue

                else:
                    query = query.replace("property1", property_data[label][0])

                if "Label2" in templates[i]:
                    label2 = triplet[2]
                    if label2 is None or label2 == '':
                        label2 = label
                        label = ''
                        query = templates[i].replace("n:Label1", "n")
                        query = query.replace("Label2", label2)

                        if "property1" in templates[i]:
                            query = query.replace("property1", '')
                        if "num" in templates[i]:
                            pass
                    else:
                        query = query.replace("Label2", label2)

                if "property2" in templates[i]:
                    query = query.replace("property2", property_data[label2][0])

                if "R1" in templates[i]:
                    query = query.replace("R1", triplet[1])

                if query in ex:
                    continue
                else:
                    ex.append(query)
                    k += 1

                if k == max_example_number:
                    break

        template_data[templates[i]] = ex

    create_outputfile('template.json', template_data)

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
    I want you to act as a Neo4j specialist. I will supply you with a Cypher query that needs to be explained 
    in a simple manner, suitable for someone without any knowledge of databases. 
    # TODO command not a description

    Please write a user-friendly description for the given query in one sentence, ensuring it is concise, 
    easily understandable, and avoids technical jargon. Do not start the description with "This query..." or "The query...".
    [Query]: ```{query}```.
    [Answer]: """
    description = chat_gpt_client.get_completion(prompt=prompt, temperature=temprature)
    return description

def example_describe_cypher_query(query, temprature=0.5):
    prompt = f"""      
        I want you to act as a Neo4j specialist. I will supply you with a Cypher query that needs to be explained 
        in a simple manner, suitable for someone without any knowledge of databases. 
        Please write a user-friendly description for the given query in one sentence, ensuring it is concise, 
        easily understandable, and avoids technical jargon. 

        Example:
        [Query]: ```MATCH ()-[r:TIER_ONE_OF]->(m:Supplier) RETURN n,m```
        [Answer]: Return the nodes that have the tier one relationship with suppliers for.
        [Query]: ```MATCH (n:Label1) WHERE n.property1 > num RETURN n```
        [Answer]: Find all nodes that their property is greater than a number.
        [Query]: ```MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel ORDER BY n.property1```
        [Answer]: Sort the result. The default order is ASCENDING.
        [Query]: ```{query}```         
        [Answer]: """
    description = chat_gpt_client.get_completion(prompt=prompt, temperature=temprature)
    return description

def schema_describe_cypher_query(query, temprature=0.5):
    with open('data/schema.json') as f:
        schema = json.load(f)
    #cleaned_schema = clean_schema(schema)

    prompt = f"""
        I want you to act as a Neo4j specialist. I will supply you with the schema of the database and a Cypher query that needs to be explained 
        in a simple manner, suitable for someone without any knowledge of databases. 
        Please write a user-friendly description for the given query in one sentence, ensuring it is concise, 
        easily understandable, and avoids technical jargon.       
        Schema: ---{schema}---      
        [Query]:  ```{query}```               
        [Answer]: """
    description = chat_gpt_client.get_completion(prompt=prompt, temperature=temprature)
    return description

def get_template(file_name):
    temp_ls = []
    query_ls = []
    with open(file_name) as f:
        schema = json.load(f)

    for k in schema.keys():
        temp = schema[k]
        temp.pop(0)
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
    template_ls,query_ls = get_template(save_path + '/template.json')
    # # delete duplicate
    # template_ls = list(dict.fromkeys(template_ls))
    with open(save_path + '/templates2id.json') as f:
        template2id = json.load(f)
    query_id_ls = [template2id[x] for x in query_ls]
    description_ls, cypher_ls = [], []
    output_json = {}
    # count running time
    start_time = time.time()
    for idx, template in enumerate(template_ls):
        # print(f"{id}:{template}")
        temp = []
        query_id = query_id_ls[idx]
        temp.append(query_id)
        time.sleep(10)
        temp.append(simple_describe_cypher_query(template, temperture))
        time.sleep(10)
        temp.append(example_describe_cypher_query(template, temperture))
        time.sleep(10)
        temp.append(schema_describe_cypher_query(template, temperture))
        description_ls.append(temp)
        print(f"{idx}:{temp}")
    print("--- %s seconds ---" % (time.time() - start_time))
    for i in range(len(template_ls)):

        output_json[template_ls[i]] = description_ls[i]
    create_outputfile('template_description.json', output_json)



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
    create_gold_template(save_path = save_path, templates_path=project_dir)
    # graph schema information
    extract_and_export_graph_info()
    export_numeric_properties(save_path)
    # create template
    create_template(save_path)

    #create_test_dataset(save_path,temperture=0)