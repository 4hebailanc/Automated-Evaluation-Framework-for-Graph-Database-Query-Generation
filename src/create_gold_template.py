import json
import os
# Get the directory of the executed script
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
# Set the current working directory to the script directory
os.chdir(project_dir)

from neo4j_client import Neo4jClient

def get_templates_and_descriptions(template_path):

    with open(template_path,'r') as f:
        files = f.read().split('\n')[:-1]
    templates = []
    descriptions = []

    for f in files:
        temp, desc = f.split('|')
        templates.append(temp.strip())
        descriptions.append(desc.strip())
    # templates = ['MATCH (n:Label1) RETURN n AS node',
    #          'MATCH (n:Label1) WHERE n.property1 > num RETURN n',
    #          'MATCH (n:Label1)-[r]->(m:Label2) RETURN *',
    #          'MATCH (n:Label1)-[r]->(m:Label2) RETURN n,m',
    #          'MATCH (n:Label1)-[r:R1]->(m:Label2) RETURN n,m',
    #          'MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel',
    #          'MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel ORDER BY n.property1',
    #          'MATCH (n:Label1)-[r]->(m:Label2) RETURN n AS node, r AS rel LIMIT 10',
    #          'MATCH (n:Label1)-[r]->(m:Label2) RETURN count(*) AS nbr',
    #          'MATCH (n:Label1)-[r:R1]->(m:Label2) WHERE n.property1 = '' RETURN m.property2']
    # descriptions = ['Find all nodes and return all nodes.',
    #             'Find all nodes that their property is greater than a number ',
    #             'Return the value of all variables.',
    #             'Reture the nodes that have a relationship',
    #             'Reture the nodes that satisfied the relationship',
    #             'Use alias for result column name.',
    #             'Sort the result. The default order is ASCENDING.',
    #             'Limit the number of rows to a maximum of 10, for the result set.',
    #             'The number of matching rows.',
    #             'Return the property of node m where the property of node n is filtered']
    return templates, descriptions


def create_gold_template(save_path=None, templates_path=None, templates = None, descriptions=None):
    # Get the directory of the executed script
    if templates is None or descriptions is None:
        template_path = templates_path + '/data/template.txt'
        templates, descriptions = get_templates_and_descriptions(template_path)

    # initialize the dictionary
    gold_templates = {}
    # save templates and descriptions to file
    if save_path == None:
        gold_templates_save_path = './data/graph/gold_templates.json'
        # id2templates and id2descriptions
        id2descriptions_save_path = './data/graph/id2descriptions.json'
        descriptions2id_save_path = './data/graph/descriptions2id.json'
        id2templates_save_path = './data/graph/id2templates.json'
        templates2id_save_path = './data/graph/templates2id.json'

    else:
        gold_templates_save_path = save_path + '/gold_templates.json'
        id2descriptions_save_path = save_path + '/id2descriptions.json'
        descriptions2id_save_path = save_path + '/descriptions2id.json'
        id2templates_save_path = save_path + '/id2templates.json'
        templates2id_save_path = save_path + '/templates2id.json'

    id2templates = {}
    templates2id = {}
    id2descriptions = {}
    descriptions2id = {}
    for ix,temp in enumerate(templates):
        desc = descriptions[ix]
        # create the dictionary
        gold_templates[temp] = desc
        id2templates[ix] = temp
        id2descriptions[ix] = desc
        templates2id[temp] = ix
        descriptions2id[desc] = ix

    with open(gold_templates_save_path, 'w') as f:
        f.write(json.dumps(gold_templates))

    with open(id2templates_save_path, 'w') as f:
        f.write(json.dumps(id2templates))

    with open(id2descriptions_save_path, 'w') as f:
        f.write(json.dumps(id2descriptions))

    with open(templates2id_save_path, 'w') as f:
        f.write(json.dumps(templates2id))

    with open(descriptions2id_save_path, 'w') as f:
        f.write(json.dumps(descriptions2id))

def create_schema_file():
    driver = neo4j_client._connect_to_neo4j()
    schema_query = "CALL apoc.meta.stats YIELD labels, relTypes"
    schema = {}
    with driver.session(database="neo4j") as session:
        # Use .data() to access the results array
        query_result = session.run(schema_query).data()
        schema['labels'] = query_result[0]['labels']
        schema['relTypes'] = query_result[0]['relTypes']
    
    with open('./data/schema.json', 'w', encoding='utf-8') as f:
        json.dump(schema, f, ensure_ascii=False)
        
if __name__ == "__main__":
    with open('app/neo4j_specifications.json') as f:
        neo4j_specifications = json.load(f)

    neo4j_uri = neo4j_specifications['uri']
    neo4j_user = neo4j_specifications['user']
    neo4j_password = neo4j_specifications['password']
    neo4j_database = neo4j_specifications['database']

    neo4j_client = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password, database=neo4j_database)
    create_schema_file()
