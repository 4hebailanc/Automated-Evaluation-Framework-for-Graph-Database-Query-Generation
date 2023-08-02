import json
from chatgpt_client import ChatGPTClient
from neo4j_client import Neo4jClient
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

def describe_cypher_query(query):
    description = chat_gpt_client.get_completion(prompt = query)
    return description

def get_template(file_name):
    temp_ls = []
    with open(file_name) as f:
        schema = json.load(f)

    for k in schema.keys():
        temp = schema[k]
        temp.pop(0)
        temp_ls.extend(temp)

    print(temp_ls)
    return temp_ls

def compare_results(template, generated):
    indices = len(template)

    for i in range (indices):
        if template[i] == generated[i]:
            print('yes',template[i],generated[i])
        else:
            print('no',template[i],generated[i])


if __name__ == "__main__":
    template_ls = get_template('output/template.json')
    
    description_ls, cypher_ls = [], []

    for template in template_ls:
        description_ls.append(generate_cypher_query(template))
    
    for description in description_ls:
        cypher_ls.append(describe_cypher_query(description))

    compare_results(template_ls,cypher_ls)
