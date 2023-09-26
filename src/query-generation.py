# load basic packages
import argparse
import json
import difflib
import time
import os
# Get the directory of the executed script
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
# Set the current working directory to the script directory
os.chdir(project_dir)

from src.chatgpt_client import ChatGPTClient
from src.neo4j_client import Neo4jClient

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
neo4j_client = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password, database=neo4j_database)


# Define the Cypher query generator function
def generate_cypher_query(verbalization, additional_instructions, schema, property_keys):
    # Use the ChatGPT client to generate a Cypher query based on the natural language description and additional
    # instructions
    prompt = f"""          
        Given the Neo4j schema delimited with tripple dashes, and the property key delimited with ope angle brackets,
        generate a cypher query corresponding to the verbalization delimited with triple backticks and using the 
        following additional instructions separated with triple underscores:          

        Schema: ---{schema}---          

        Property keys: <<<{property_keys}>>>  

        Query verbalization: ```{verbalization}```      

        Additional instructions: ___{additional_instructions}___      

        The output should a cypher_query and nothing else.

        [no prose]
        """

    cypher_query = chat_gpt_client.get_completion(prompt=prompt)
    return cypher_query

def similarity(query1, query2):
    try:
        # Tokenize the queries into words/symbols
        tokens1 = query1.split()
        tokens2 = query2.split()

        # Calculate the Longest Common Subsequence (LCS)
        seq_matcher = difflib.SequenceMatcher(None, tokens1, tokens2)
        lcs_ratio = seq_matcher.ratio()
    except:
        lcs_ratio = 0

    return lcs_ratio


def jaccard_similarity(list1, list2):
    # Convert the complex results to sets of unique identifiers (e.g., node IDs)
    set1 = {item['id'] for item in str(list1)}
    set2 = {item['id'] for item in list2}

    # Calculate the Jaccard Similarity
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union
# Define the Streamlit app
def main(property_keys_path='data/property_keys.json',schema_path='data/schema.json',graph_path='data/graph'):
    # Load the schema
    with open(schema_path) as f:
        schema = json.load(f)
    with open(property_keys_path) as g:
        property_keys = json.load(g)
    with open(graph_path+ '/template_description.json') as h:
        description_data = json.load(h)

    # set default values
    additional_instructions = ""
    simple_description_ex = 0
    example_description_ex = 0
    schema_description_ex = 0
    avg_simple_description_query_similarity = 0
    avg_example_description_query_similarity = 0
    avg_schema_description_query_similarity = 0
    simple_description_results = {}
    example_description_results = {}
    schema_description_results = {}

    template_results = {}

    for idx,[gold_query, descriptions] in enumerate(description_data.items()):
        template_id = descriptions[0]
        simple_description = descriptions[1]
        example_description = descriptions[2]
        schema_description = descriptions[3]

        time.sleep(5)
        simple_describtion_generate_query = generate_cypher_query(simple_description, additional_instructions, schema, property_keys)
        time.sleep(5)
        example_describtion_generate_query = generate_cypher_query(example_description, additional_instructions, schema, property_keys)
        time.sleep(5)
        schema_description_generate_query = generate_cypher_query(schema_description, additional_instructions, schema, property_keys)

        # metrics
        ## compare similarity to gold_query
        simple_describtion_similarity_score = similarity(gold_query, simple_describtion_generate_query)
        example_describtion_similarity_score = similarity(gold_query, example_describtion_generate_query)
        schema_description_similarity_score = similarity(gold_query, schema_description_generate_query)

        avg_simple_description_query_similarity = avg_simple_description_query_similarity + simple_describtion_similarity_score
        avg_example_description_query_similarity = avg_example_description_query_similarity + example_describtion_similarity_score
        avg_schema_description_query_similarity = avg_schema_description_query_similarity + schema_description_similarity_score

        # get the query results
        gold_query_results = neo4j_client.check_and_execute_cypher_query(gold_query)
        simple_describtion_generate_query_results = neo4j_client.check_and_execute_cypher_query(simple_describtion_generate_query)
        example_describtion_generate_query_results = neo4j_client.check_and_execute_cypher_query(example_describtion_generate_query)
        schema_description_generate_query_results = neo4j_client.check_and_execute_cypher_query(schema_description_generate_query)

        ## Execution Accuracy (EX)
        simple_description_ex = simple_description_ex + simple_describtion_generate_query_results[1]
        example_description_ex = example_description_ex + example_describtion_generate_query_results[1]
        schema_description_ex = schema_description_ex + schema_description_generate_query_results[1]

        # results similarity
        # TODO
        # ==  True, 1.
        # No return using difflib.SequenceMatcher: reason too long string
        # if temple ix == "0":
        #     xxx

        # simple_description_output_similarity = jaccard_similarity(simple_describtion_generate_query_results[0], gold_query_results[0])
        # example_description_output_similarity = similarity(example_describtion_generate_query_results[0], gold_query_results[0])
        # schema_description_output_similarity = similarity(schema_description_generate_query_results[0], gold_query_results[0])


        simple_description_output_similarity = 0
        example_description_output_similarity = 0
        schema_description_output_similarity = 0

        simple_description_results[idx] = [template_id,gold_query, simple_describtion_generate_query, simple_description_ex, simple_describtion_similarity_score, simple_describtion_generate_query_results[0], simple_description_output_similarity]
        example_description_results[idx] = [template_id,gold_query, example_describtion_generate_query, example_description_ex, example_describtion_similarity_score, example_describtion_generate_query_results[0], example_description_output_similarity]
        schema_description_results[idx] = [template_id,gold_query, schema_description_generate_query, schema_description_ex, schema_description_similarity_score, schema_description_generate_query_results[0], schema_description_output_similarity]

    for idx,_ in enumerate(simple_description_results):
        templated_id = simple_description_results[idx][0]
        simple_description_similarity_score = simple_description_results[idx][4]
        example_description_similarity_score = example_description_results[idx][4]
        schema_description_similarity_score = schema_description_results[idx][4]

        simple_description_ex = simple_description_results[idx][3]
        example_description_ex = example_description_results[idx][3]
        schema_description_ex = schema_description_results[idx][3]

        if templated_id not in template_results:
            template_results[templated_id] = {
                "simple_description": [],
                "example_description": [],
                "schema_description": []
            }

        template_results[templated_id]["simple_description"].append({
            "query similarity": simple_description_similarity_score,
            "execution accuracy": simple_description_ex
        })

        template_results[templated_id]["example_description"].append({
            "query similarity": example_description_similarity_score,
            "execution accuracy": example_description_ex
        })

        template_results[templated_id]["schema_description"].append({
            "query similarity": schema_description_similarity_score,
            "execution accuracy": schema_description_ex
        })


    # results in total
    simple_description_results['total'] = {"query similarity": avg_simple_description_query_similarity/len(description_data),
                                            "execution accuracy": simple_description_ex/len(description_data)}
    example_description_results['total'] = {"query similarity": avg_example_description_query_similarity/len(description_data),
                                            "execution accuracy": example_description_ex/len(description_data)}
    schema_description_results['total'] = {"query similarity": avg_schema_description_query_similarity/len(description_data),
                                           "execution accuracy": schema_description_ex / len(description_data)}





if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("property_keys_path", nargs='?', default='data/property_keys.json',
                        help="path to Neo4j schema file in JSON format")
    parser.add_argument("schema_path", nargs='?', default='data/schema.json',
                        help="path to Neo4j schema file in JSON format")
    parser.add_argument("graph_path", nargs='?', default='data/graph/',
                        help="path to Neo4j graph files folder")
    args = parser.parse_args()
    main(args.property_keys_path,args.schema_path,args.graph_path)
    print("Final")
