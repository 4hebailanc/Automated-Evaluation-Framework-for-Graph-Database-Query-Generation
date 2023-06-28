import json
from neo4j import GraphDatabase
import re

'''
todo:
explain + cypherquery
profile + cypherquery
https://neo4j.com/docs/cypher-manual/current/query-tuning/query-profile/
'''

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
        del labels_result[0]  #remove '_Neodash_Dashboard'
        for item in labels_result:
            for label in item['n']:
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
        
def create_outputfile(filename, data):
    with open('./output/'+filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
def create_template():
    #data = {'template':['description', 'ex1', 'ex2']}
    data = {}
    templates = ['MATCH (n:Label1) RETURN n AS node',
                 'MATCH (n:Label1) WHERE n.property1 > num RETURN n',
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN *',
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN n,m',
                 'MATCH (n:Label1)-[r:R1]->(m:Label2) RETURN n,m', #good above
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel',
                 'MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel ORDER BY n.name',
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
        #print(nodeRel_data)

    #todo: formulate the file
    template_data = {}
    for i in range(len(templates)):
        j = 0
        ex = []
        ex.append(descriptions[i])
        for label in label_ls:
            query = templates[i].replace("Label1", label)

            
            if "property1" in templates[i]:
                query = query.replace("property1", property_data[label][0])

            if "Label2" in templates[i]:
                label2= get_seclabel(nodeRel_data, label)
                query = query.replace("Label2", label2)
            
            if "property2" in templates[i] and label2 != '':
                query = query.replace("property2", property_data[label2][0])
            
            if "R1" in templates[i]:
                rel = get_relation(nodeRel_data, label, label2)
                query = query.replace("R1", rel)

            ex.append(query)

            j+=1
            if j == 5:
                break
        template_data[templates[i]] = ex

    create_outputfile('template.json',template_data)
    '''
    query = temp_str.format(l=label)
    label_ex, rel_ex = [], []
    for label in label_ls:
        query = 'MATCH (n:{l}) RETURN n'.format(l=label)
        label_ex.append(query)

    for rel in relTypes_ls:
        query = 'MATCH p={r} RETURN p'.format(r=rel) 
        rel_ex.append(query)

    data[node_template] = label_ex
    data[rel_template]  = rel_ex

    create_outputfile('template.json',data)
    '''
def get_seclabel(relations, subject):
    #return the first object of the subject inputted
    for value in relations.values():
        if subject in value.keys():
            return value[subject][0]

def get_relation(relations, subject, object=''):
    #object=get_seclabel(relations,subject)
    for value in relations.values():
        if subject in value.keys() and object in value[subject]:
            return list(relations.keys())[list(relations.values()).index(value)]

if __name__ == "__main__":
    #queries()
    create_template()