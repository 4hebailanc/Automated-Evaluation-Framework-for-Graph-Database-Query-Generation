import json
from neo4j import GraphDatabase
import re
import math

# todo:
# put the current template into the table

# generate the testing pipeline

def percentile(data, perc: int):
    size = len(data)
    return sorted(data)[int(math.ceil((size * perc) / 100)) - 1]

def connect_db():
    # URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
    URI = "neo4j://localhost:7687"
    AUTH = ("test", "12345678")

    with GraphDatabase.driver(URI, auth=AUTH) as driver: 
        driver.verify_connectivity()
    return driver

def queries():
    driver = connect_db()

    # Cypher query
    node_labels_query = "MATCH (n) RETURN distinct labels(n) as n"
    relations_query = "CALL apoc.meta.stats YIELD labels, relTypes"
    properties_query = "MATCH (n) UNWIND keys(n) AS key RETURN labels(n)[0] AS label, collect(distinct key) AS propertyKeys UNION MATCH ()-[r]->() UNWIND keys(r) AS key RETURN type(r) AS label, collect(distinct key) AS propertyKeys"

    label_list, relations, properties = [], {}, {}

    # Create a driver session
    with driver.session(database="neo4j") as session:
        # Use .data() to access the results array
        labels_result = session.run(node_labels_query).data()

        for item in labels_result:
            for label in item['n']:
                if label == '_Neodash_Dashboard':
                    continue
                else:
                    label_list.append(label)
        
        relations_result = session.run(relations_query).data()
        relations = relations_result[0]['relTypes']

        properties_result = session.run(properties_query).data()
        del properties_result[0]  #remove '_Neodash_Dashboard'
        for item in properties_result:
            properties[item['label']] = item['propertyKeys']

    # Close the driver connection
    driver.close()
    
    relations_triplet = list(relations.keys())
    relations_list = sep_nodes_relations(relations_triplet)

    create_outputfile('nodetypes.txt',label_list)
    create_outputfile('nodesRelations.json',relations_list)
    create_outputfile('propertyKeys.json',properties)

def sep_nodes_relations(relations_triplet):
    relations_ls, nodes_ls = [],[]

    for item in relations_triplet:
        rel = item[item.find('[')+1:item.find(']')]
        rel = rel[1:] #remove ':' in str
        relations_ls.append(rel)
        
        two_nodes = [re.findall('\((.*?)\)',item)]
        if two_nodes[0][0] != '':
            two_nodes[0][0] = two_nodes[0][0][1:] #remove ':' in str
        if two_nodes[0][1] != '':
            two_nodes[0][1] = two_nodes[0][1][1:] #remove ':' in str
        nodes_ls.extend(two_nodes)
    
    rel_set = list(set(relations_ls))
    #current problem:cant ignore null
    #index would be the same
    #get the indexes of the same relations in the list of rels and nodes
    #temp = {'rel':[['sub1','obj1'], ['sub2','obj2']]}
    #combine = {'rel':{ 'sub1':['obj1', 'obj3'], 'sub2':['obj2'] } }
    
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

def get_numeric_properties(filename="./output/propertyKeys.json"):
    with open(filename) as file:
        property_data = json.load(file)
    keys = property_data.keys()
    
    driver = connect_db()
    prop_stats = {}
    
    with driver.session(database="neo4j") as session:
        for key in keys:
            num_query = 'CALL apoc.meta.nodeTypeProperties({includeLabels: ["n"]});'

            key = '"'+ key +'"'
            num_query = num_query.replace('"n"',key)
            type_result = session.run(num_query).data()
            
            for i in type_result:
                prop_query ='MATCH (n: Label1) RETURN collect(n.property1) as prop'
                temp_ls=[]
                if 'Double'in i['propertyTypes'] or 'Long'in i['propertyTypes']:
                    prop_query = prop_query.replace('Label1',i['nodeLabels'][0])
                    prop_query = prop_query.replace('property1',i['propertyName'])
                    prop_result = session.run(prop_query).data()
                    ls_result = prop_result[0]['prop']

                    ls_result =  [ x for x in ls_result if type(x) is not str]

                    temp_ls.append(round(percentile(ls_result,25),3))
                    temp_ls.append(round(percentile(ls_result,50),3))
                    temp_ls.append(round(percentile(ls_result,75),3))

                    prop_stats[i['propertyName']] = list(set(temp_ls))
        
    driver.close()
    create_outputfile('propertiesQuantile.json',prop_stats)


def create_outputfile(filename, data):
    with open('./output/'+filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
def create_template():
    #data = {'template':['description', 'ex1', 'ex2']}

    templates = ['MATCH (n:Label1) RETURN n AS node',
                 'MATCH (n:Label1) WHERE n.property1 > num RETURN n',
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN *',
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN n,m',
                 'MATCH (n:Label1)-[r:R1]->(m:Label2) RETURN n,m', #good above
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel',
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel ORDER BY n.property1',
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel LIMIT 10',
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN count(*) AS nbr',
                 'MATCH (n:Label1)-[r:R1]->(m:Label2) WHERE n.property1 = '' RETURN m.property2']
    descriptions = ['Find all nodes and return all nodes.',
                    'Find all nodes that their property is greater than a number ',
                    'Return the value of all variables.',
                    'Reture the nodes that have a relationship',
                    'Reture the nodes that satisfied the relationship', #good above
                    'Use alias for result column name.',
                    'Sort the result. The default order is ASCENDING.',
                    'Limit the number of rows to a maximum of 10, for the result set.',
                    'The number of matching rows.',
                    'Return the property of node m where the property of node n is filtered']

    #generate label list
    node_file = open("./output/nodetypes.txt", "r")
    file_txt = node_file.read()
    label_ls = file_txt.strip('][').split(', ')
    node_file.close()

    for i in range(len(label_ls)):
        label_ls[i] =  label_ls[i].strip('\"')
    #print(label_ls)

    with open("./output/propertyKeys.json") as file:
        property_data = json.load(file)
        #print(property_data)
    
    with open("./output/nodesRelations.json") as file:
        nodeRel_data = json.load(file)
        rel_labels_ls = get_rellabels(nodeRel_data)
    
    with open("./output/propertiesQuantile.json") as file:
        propStats_data = json.load(file)
    keys = propStats_data.keys()

    
    #todo: formulate the file
    template_data = {}
    property1, num = '', ''
    for i in range(len(templates)):
        k = 0
        ex = []
        ex.append(descriptions[i])
        #here
        for triplet in rel_labels_ls:
            if triplet[0] not in property_data:
                continue
            else:
                label = triplet[0]
                query = templates[i].replace("Label1", label)

                if "property1" in templates[i]:
                    temp_idx = 0
                    
                    if "num" in templates[i]:
                        if label in propStats_data:
                            if property_data[label][temp_idx] in propStats_data[label]:
                                query = query.replace('num',str(propStats_data[property_data[label][temp_idx]][0]))
                                query = query.replace("property1", property_data[label][temp_idx])
                                property1 = property_data[label][temp_idx]
                                num = str(propStats_data[property_data[label][temp_idx]][0])
                            else:
                                continue
                        else:
                            continue
                    else:
                        query = query.replace("property1", property_data[label][0])
                        property1 = property_data[label][0]

                if "Label2" in templates[i]:
                    label2 = triplet[2]
                    if label2 is None or label2 is '':
                        label2 = label
                        label = ''
                        query = templates[i].replace("Label1", "")
                        query = query.replace("Label2", label)

                        #how to solve when one of the label is empty???
                        #change the template accordingly
                        if "property1" in templates[i]:
                            query = query.replace("property1",'')
                        if "num" in templates[i]:
                            pass
                    else:
                        query = query.replace("Label2", label2)
                
                if "property2" in templates[i]:
                    query = query.replace("property2", property_data[label2][0])
                
                if "R1" in templates[i]:
                    query = query.replace("R1", triplet[1])

                ex.append(query)

                k+=1
                if k == 5:
                    break
        
            
        template_data[templates[i]] = ex

    create_outputfile('new_template.json',template_data) 

def get_rellabels(relations_dict):
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
    print(ls)
    return ls

def test_template():
    with open("./output/template.json") as file:
        template_data = json.load(file)

    template_ls = []
    for value in template_data.values():
        value.pop(0)
        template_ls.extend(value)
    print(template_ls)
    #issue here: label2 is empty, thus query is error
    '''
    driver = connect_db()

    result_ls = []
    for template in template_ls:
        query = template + ' LIMIT 1'
        with driver.session(database="neo4j") as session:
            # Use .data() to access the results array
            result = session.run(query).data()
        result_ls.extend(result)
    
    print(result_ls)'''


#todo: 
# test out new dump
# look into paper to see if cover all the categories -> create an excel
# then expand the template/ modify code
# create more complex template, less simple template

# run the queries to see if it's semantically correct
# ask chatgpt to describe the query, consistency

#explain + cypherquery  
#profile + cypherquery
#https://neo4j.com/docs/cypher-manual/current/query-tuning/query-profile/

if __name__ == "__main__":
    #queries()
    #get_numeric_properties()
    create_template()
    #test_template()