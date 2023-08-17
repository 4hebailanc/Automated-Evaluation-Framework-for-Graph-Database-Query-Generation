import sys
sys.path.append('./')

import json
from src.chatgpt_client import ChatGPTClient
from src.neo4j_client import Neo4jClient
from neo4j import GraphDatabase

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
neo4j_client = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password, database=neo4j_database)

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

def simple_describe_cypher_query(query):
    prompt = f"""      
        Given cypher query below, please provide a description for the query in one sentance like how a user who has no background in database might ask a question.
        Cypher Query: ```{query}```                                                                                                                                                                                                                                                                                     
        [no prose]
        """
    description = chat_gpt_client.get_completion(prompt = prompt)
    return description

def example_describe_cypher_query(query):
    prompt = f"""      
        Given cypher query below, please provide a description for the query in one sentance like how a user who has no background in database might ask a question.
        Example would be: return the nodes that have the tier one relationship with suppliers for ```MATCH ()-[r:TIER_ONE_OF]->(m:Supplier) RETURN n,m```
        Cypher Query: ```{query}```                                                                                                                                                                                                                                                                                     
        
        """
    description = chat_gpt_client.get_completion(prompt = prompt)
    return description

def schema_describe_cypher_query(query):
    with open('data/schema.json') as f:
        schema = json.load(f)

    prompt = f"""
        Given the Neo4j schema, and cypher query below. please provide a description for the query in one sentance like how a user who has no background in database might ask a question.               
        Schema: ---{schema}---      
        Cypher Query: ```{query}```                                                                                                                                                                                                                                                                                     
        """
    description = chat_gpt_client.get_completion(prompt = prompt)
    return description

def get_template(file_name):
    temp_ls = []
    with open(file_name) as f:
        schema = json.load(f)

    for k in schema.keys():
        temp = schema[k]
        temp.pop(0)
        temp_ls.extend(temp)

    return temp_ls

def compare_results(template, generated):
    indices = len(template)

    for i in range (indices):
        if template[i] == generated[i]:
            #print('yes',template[i],generated[i])
            print('yes')
        else:
            #print('no',template[i],generated[i])
            print('no')
    #todo: compare results and save queries

def create_outputfile(filename, data):
    with open('./output/'+filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


if __name__ == "__main__":
    template_ls = get_template('output/template.json')
    
    description_ls, cypher_ls = [], []
    output_json = {}
    for template in template_ls:
        temp = []
        temp.append(simple_describe_cypher_query(template))
        temp.append(example_describe_cypher_query(template))
        temp.append(schema_describe_cypher_query(template))
        description_ls.append(temp)
    
    for i in range(len(template_ls)):
        output_json[template_ls[i]] = description_ls[i]
    
    create_outputfile('template_description.json', output_json)