# load basic packages
import argparse
import json
import difflib
import time
import os
import re
import multiprocessing
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from bert_score import score
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
def generate_cypher_query_raw(verbalization, additional_instructions):
    """
    Generate a Cypher query based on the natural language description and additional instructions.
    :param verbalization: str: The natural language description of the query.
    :param additional_instructions: str: Additional instructions for generating the Cypher query.
    :return: str: The generated Cypher query.
    """
    prompt = f"""
        Generate a Cypher query corresponding to the following verbalization delimited with triple backticks:
        Query verbalization: ```{verbalization}```      

        Additionally, follow these instructions separated with triple underscores:
        ___
        {additional_instructions}
        ___
        The output should be a Cypher query and nothing else.
        [no prose]
        """
    cypher_query = chat_gpt_client.get_completion(prompt=prompt)
    return cypher_query


def generate_cypher_query_seperate(verbalization, additional_instructions):
    """
    Generate a Cypher query based on the natural language description and additional instructions,
    schema and property keys are provided separately.
    :param verbalization: str: The natural language description of the query.
    :param additional_instructions: str: Additional instructions for generating the Cypher query.
    :return: str: The generated Cypher query.
    """
    with open('data/graph/schema_triplets.json') as f:
        schema_triplets = json.load(f)
    with open('data/graph/property_keys.json') as g:
        property_keys = json.load(g)
    prompt = f"""
        Given the following Neo4j schema delimited with triple dashes:
        ---
        all the shcema triplets: {schema_triplets}
        property keys: {property_keys}
        ---
        Generate a Cypher query corresponding to the following verbalization delimited with triple backticks:
        Query verbalization: ```{verbalization}```      

        Additionally, follow these instructions separated with triple underscores:
        ___
        {additional_instructions}
        ___
        The output should be a Cypher query and nothing else.
        [no prose]
        """
    cypher_query = chat_gpt_client.get_completion(prompt=prompt)
    return cypher_query
def generate_cypher_query_simple(verbalization, additional_instructions):
    """
    Generate a Cypher query based on the natural language description and additional instructions without schema.
    :param verbalization: str: The natural language description of the query.
    :param additional_instructions: str: Additional instructions for generating the Cypher query.
    :return: str: The generated Cypher query.
    """
    with open('data/graph/schema.json') as f:
        schema = json.load(f)

    prompt = f"""
        Given the following Neo4j schema delimited with triple dashes:
        ---
        {schema}
        ---
        Generate a Cypher query corresponding to the following verbalization delimited with triple backticks:
        Query verbalization: ```{verbalization}```      
        
        Additionally, follow these instructions separated with triple underscores:
        ___
        {additional_instructions}
        ___
        The output should be a Cypher query and nothing else.
        [no prose]
        """
    cypher_query = chat_gpt_client.get_completion(prompt=prompt)
    return cypher_query
def generate_cypher_query_example_1(verbalization, additional_instructions):
    """
    Generate a Cypher query based on the natural language description and additional instructions.
    one demonstration example is provided.
    :param verbalization: str: The natural language description of the query.
    :param additional_instructions: str: Additional instructions for generating the Cypher query.
    :return: str: The generated Cypher query.
    """
    with open('data/graph/schema.json') as f:
        schema = json.load(f)
    # Use the ChatGPT client to generate a Cypher query based on the natural language description and additional
    # instructions
    prompt = f"""          
        Given the Neo4j schema delimited with tripple dashes, and the property key delimited with ope angle brackets,
        generate a cypher query corresponding to the verbalization delimited with triple backticks and using the 
        following additional instructions separated with triple underscores:  

        Schema: ---{schema}---          

        Additional instructions: ___{additional_instructions}___
        Several example will be provided.The output should a cypher_query and nothing else. [no prose].
        
        Example:
        [verbalization]: ```Find all BusinessPartner nodes with an aggregate score greater than 0.041.```
        [Query]: MATCH (n:BusinessPartner) WHERE n.agg_score > 0.041 RETURN n
        [verbalization]: ```{verbalization}```    
        [Query]:  
        """

    cypher_query = chat_gpt_client.get_completion(prompt=prompt)
    return cypher_query


def generate_cypher_query_example_3(verbalization, additional_instructions):
    """
    Generate a Cypher query based on the natural language description and additional instructions.
    three demonstration examples are provided.
    :param verbalization: str: The natural language description of the query.
    :param additional_instructions: str: Additional instructions for generating the Cypher query.
    :return: str: The generated Cypher query.
    """
    with open('data/graph/schema.json') as f:
        schema = json.load(f)
    # Use the ChatGPT client to generate a Cypher query based on the natural language description and additional
    # instructions
    prompt = f"""          
        Given the Neo4j schema delimited with tripple dashes, and the property key delimited with ope angle brackets,
        generate a cypher query corresponding to the verbalization delimited with triple backticks and using the 
        following additional instructions separated with triple underscores:  

        Schema: ---{schema}---          

        Additional instructions: ___{additional_instructions}___
        Several example will be provided.The output should a cypher_query and nothing else. [no prose].

        Example:
        [verbalization]: ```What websites are connected to branches, and which branches are they connected to?```
        [Query]: MATCH (n:Branch)-[r1]->(m:Branch) RETURN n, collect(m.website)
        [verbalization]: ```Find all BusinessPartner nodes with an aggregate score greater than 0.041.```
        [Query]: MATCH (n:BusinessPartner) WHERE n.agg_score > 0.041 RETURN n
        [verbalization]: ```Return the number of matching rows as a count, but only count each node once```
        [Query]: MATCH (n)-[r:PRODUCED_IN]->(m:Substance) RETURN count(DISTINCT n.) AS nbr
        [verbalization]: ```{verbalization}```    
        [Query]:  
        """

    cypher_query = chat_gpt_client.get_completion(prompt=prompt)
    return cypher_query

def generate_cypher_query_example_5(verbalization, additional_instructions):
    """
    Generate a Cypher query based on the natural language description and additional instructions.
    five demonstration examples are provided.
    :param verbalization: str: The natural language description of the query.
    :param additional_instructions: str: Additional instructions for generating the Cypher query.
    :return: str: The generated Cypher query.
    """
    with open('data/graph/schema.json') as f:
        schema = json.load(f)
    # Use the ChatGPT client to generate a Cypher query based on the natural language description and additional
    # instructions
    prompt = f"""          
        Given the Neo4j schema delimited with tripple dashes, and the property key delimited with ope angle brackets,
        generate a cypher query corresponding to the verbalization delimited with triple backticks and using the 
        following additional instructions separated with triple underscores:  

        Schema: ---{schema}---          

        Additional instructions: ___{additional_instructions}___
        Several example will be provided.The output should a cypher_query and nothing else. [no prose].

        Example:
        [verbalization]: ```Return the nodes that have the tier one relationship with suppliers for```
        [Query]: MATCH ()-[r:TIER_ONE_OF]->(m:Supplier) RETURN n,m
        [verbalization]: ```Find all BusinessPartner nodes with an aggregate score greater than 0.041.```
        [Query]: MATCH (n:BusinessPartner) WHERE n.agg_score > 0.041 RETURN n
        [verbalization]: ```Return the number of matching rows as a count, but only count each node once```
        [Query]: MATCH (n)-[r:PRODUCED_IN]->(m:Substance) RETURN count(DISTINCT n.) AS nbr
        [verbalization]: ```What substances are refined by smelters, and what are the names of the smelters?```
        [Query]: MATCH (n:Substance)-[r1]->(m:Smelter) RETURN n, m, collect(m.name)
        [verbalization]: ```What websites are connected to branches, and which branches are they connected to?```
        [Query]: MATCH (n:Branch)-[r1]->(m:Branch) RETURN n, collect(m.website)
        [verbalization]: ```{verbalization}```    
        [Query]:  
        """

    cypher_query = chat_gpt_client.get_completion(prompt=prompt)
    return cypher_query

def remove_numbers(d):
    """
    Remove numbers from the dictionary values.
    :param d: dict: The dictionary to process.
    :return: None
    """
    if isinstance(d, dict):
        for key, value in list(d.items()):
            if isinstance(value, (int, float)):
                d[key] = ''
            else:
                remove_numbers(value)
    elif isinstance(d, list):
        for item in d:
            remove_numbers(item)
def similarity(query1, query2, type = 'bertscore'):
    """
    Calculate the similarity between two Cypher queries.
    :param query1: str: The first Cypher query.
    :param query2: str: The second Cypher query.
    :param type: str: The type of similarity metric to use ('bertscore' or 'cos').
    :return: float: The similarity score between the queries.
    """
    if type == 'bertscore':
        try:
            query1_list = [query1]
            query2_list = [query2]

            # Calculate BERTScore
            precision, recall, f1 = score(query1_list, query2_list, lang='en', model_type='bert-base-uncased')

            # BERTScore is the F1 score
            similarity_score = f1.item()
        except:
            similarity_score = 0

    # Token level TF - IDF, cosine similarity

    if type == 'cos':
        try:
            def preprocess_query(cypher_query):
                # Remove labels and index numbers from node identifiers
                cleaned_query = re.sub(r'\(\w+:\w+\)', '()', cypher_query)
                # Tokenize the query
                tokens = word_tokenize(cleaned_query)
                # Remove stopwords and stem tokens
                stop_words = set(stopwords.words('english'))
                stemmer = PorterStemmer()
                filtered_tokens = [stemmer.stem(word) for word in tokens if word.lower() not in stop_words]
                return " ".join(filtered_tokens)

            # Preprocess both Cypher queries
            preprocessed_query1 = preprocess_query(query1)
            preprocessed_query2 = preprocess_query(query2)

            # Calculate TF-IDF vectors for the preprocessed queries
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([preprocessed_query1, preprocessed_query2])

            # Calculate cosine similarity between the two vectors
            cosine_sim = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])

            # Similarity score between the queries
            similarity_score = cosine_sim[0][0]
        except:
            similarity_score = 0

    return similarity_score

def results_similarity(results1, results2):
    """
    Compare the results of two Cypher queries.
    :param results1: list: The results of the first Cypher query.
    :param results2: list: The results of the second Cypher query.
    :return: bool: True if the results are similar, False otherwise.

    """
    if results2 == None:
        return False
    if len(results1) != len(results2):
        return False
    else:
        for idx, result in enumerate(results1):
            if tuple(result.values()) != tuple(results2[idx].values()):
                return False
    return True



def jaccard_similarity(list1, list2):
    """
    Calculate the Jaccard Similarity between two lists of complex objects.
    :param list1: list: The first list of complex objects.
    :param list2: list: The second list of complex objects.
    :return: float: The Jaccard Similarity between the two lists.
    """
    # Convert the complex results to sets of unique identifiers (e.g., node IDs)
    set1 = {item['id'] for item in str(list1)}
    set2 = {item['id'] for item in list2}

    # Calculate the Jaccard Similarity
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union
# Define the Streamlit app


def main(property_keys_path='data/property_keys.json',schema_path='data/schema.json',graph_path='data/graph', load_data=''):

    with open(graph_path+ '/template_description.json') as h:
        description_data = json.load(h)

    # set default values
    additional_instructions = ""
    raw_description_ea = 0
    sperate_description_ea = 0
    simple_description_ea = 0
    example_description_ea = 0

    raw_description_er = 0
    sperate_description_er = 0
    simple_description_er = 0
    example_description_er = 0

    raw_description_query_similarity = 0
    sperate_description_query_similarity = 0
    simple_description_query_similarity = 0
    example_description_query_similarity = 0


    raw_description_results = {}
    sperate_description_results = {}
    simple_description_results = {}
    example_description_results = {}

    template_results = {}

    # for idx,[gold_query, descriptions] in enumerate(description_data.items()):
    if not load_data:
        idx = 0
    else:
        with open(load_data) as f:
            load_results = json.load(f)
        idx = load_results['idx'] + 1

        raw_description_results = load_results['raw'][0]
        sperate_description_results = load_results['seperate'][0]
        simple_description_results = load_results['simple'][0]
        example_description_results = load_results['example'][0]

        raw_description_ea = load_results['raw'][1]
        sperate_description_ea = load_results['seperate'][1]
        simple_description_ea = load_results['simple'][1]
        example_description_ea = load_results['example'][1]

        raw_description_er = load_results['raw'][2]
        sperate_description_er = load_results['seperate'][2]
        simple_description_er = load_results['simple'][2]
        example_description_er = load_results['example'][2]

        raw_description_query_similarity = load_results['raw'][3]
        sperate_description_query_similarity = load_results['seperate'][3]
        simple_description_query_similarity = load_results['simple'][3]
        example_description_query_similarity = load_results['example'][3]


    while idx < len(description_data):
        gold_query, descriptions = list(description_data.items())[idx]
        template_id = descriptions[1][0]

        description = descriptions[1][0]

        time.sleep(3)
        raw_describtion_generate_query = generate_cypher_query_raw(description, additional_instructions)
        time.sleep(3)
        sperate_describtion_generate_query = generate_cypher_query_seperate(description, additional_instructions)
        time.sleep(3)
        simple_describtion_generate_query = generate_cypher_query_simple(description, additional_instructions)
        time.sleep(3)
        example_describtion_generate_query = generate_cypher_query_example_1(description, additional_instructions)

        # metrics
        ## compare similarity to gold_query
        raw_describtion_similarity_score = similarity(gold_query, raw_describtion_generate_query)
        sperate_describtion_similarity_score = similarity(gold_query, sperate_describtion_generate_query)
        simple_describtion_similarity_score = similarity(gold_query, simple_describtion_generate_query)
        example_describtion_similarity_score = similarity(gold_query, example_describtion_generate_query)

        raw_description_query_similarity = raw_description_query_similarity + raw_describtion_similarity_score
        sperate_description_query_similarity = sperate_description_query_similarity + sperate_describtion_similarity_score
        simple_description_query_similarity = simple_description_query_similarity + simple_describtion_similarity_score
        example_description_query_similarity = example_description_query_similarity + example_describtion_similarity_score

        gold_query_results = neo4j_client.check_and_execute_cypher_query(gold_query)
        if gold_query_results[0] in ['None', None]:
            print("wrong gold query results")
            idx = idx + 1
            continue
        raw_describtion_generate_query_results = neo4j_client.check_and_execute_cypher_query(raw_describtion_generate_query)
        sperate_describtion_generate_query_results = neo4j_client.check_and_execute_cypher_query(sperate_describtion_generate_query)
        simple_describtion_generate_query_results = neo4j_client.check_and_execute_cypher_query(simple_describtion_generate_query)
        example_describtion_generate_query_results = neo4j_client.check_and_execute_cypher_query(example_describtion_generate_query)


        ## Execution Rate (ER)
        raw_description_er = raw_description_er + raw_describtion_generate_query_results[1]
        sperate_description_er = sperate_description_er + sperate_describtion_generate_query_results[1]
        simple_description_er = simple_description_er + simple_describtion_generate_query_results[1]
        example_description_er = example_description_er + example_describtion_generate_query_results[1]

        ## Execution accuracy (EA)
        raw_description_output_ea = results_similarity(gold_query_results[0], raw_describtion_generate_query_results[0])
        sperate_description_output_ea = results_similarity(gold_query_results[0], sperate_describtion_generate_query_results[0])
        simple_description_output_ea = results_similarity(gold_query_results[0], simple_describtion_generate_query_results[0])
        example_description_output_ea = results_similarity(gold_query_results[0], example_describtion_generate_query_results[0])

        raw_description_ea = raw_description_ea + raw_description_output_ea
        sperate_description_ea = sperate_description_ea + sperate_description_output_ea
        simple_description_ea = simple_description_ea + simple_description_output_ea
        example_description_ea = example_description_ea + example_description_output_ea

        raw_description_results[idx] = [template_id,gold_query, raw_describtion_generate_query, raw_describtion_similarity_score, raw_describtion_generate_query_results[1], raw_description_output_ea]
        sperate_description_results[idx] = [template_id,gold_query, sperate_describtion_generate_query, sperate_describtion_similarity_score, sperate_describtion_generate_query_results[1], sperate_description_output_ea]
        simple_description_results[idx] = [template_id,gold_query, simple_describtion_generate_query, simple_describtion_similarity_score, simple_describtion_generate_query_results[1], simple_description_output_ea]
        example_description_results[idx] = [template_id,gold_query, example_describtion_generate_query, example_describtion_similarity_score, example_describtion_generate_query_results[1], example_description_output_ea]

        save_results = {'idx': idx,
                        'raw': [raw_description_results,raw_description_ea, raw_description_er, raw_description_query_similarity],
                        'seperate': [sperate_description_results, sperate_description_ea, sperate_description_er, sperate_description_query_similarity],
                        'simple': [simple_description_results, simple_description_ea, simple_description_er, simple_description_query_similarity],
                        'example':[example_description_results, example_description_ea, example_description_er, example_description_query_similarity]
                        }

        print(f"Processed {idx} out of {len(description_data)}")

        if idx % 10 == 0 and idx != 0:
            if not os.path.exists('data/results'):
                os.mkdir('data/results')
            save_path = 'data/results/results' + str(idx) + '_' + time.strftime("%Y%m%d_%H%M%S") + '.json'
            with open(save_path, 'w') as f:
                json.dump(save_results, f)

        idx = idx + 1

    for idx in list(raw_description_results.keys()):
        idx = str(idx)
        templated_id = raw_description_results[idx][0]

        raw_description_similarity_score_idx = raw_description_results[idx][3]
        sperate_description_similarity_score_idx = sperate_description_results[idx][3]
        simple_description_similarity_score_idx = simple_description_results[idx][3]
        example_description_similarity_score_idx = example_description_results[idx][3]

        raw_description_er_idx = raw_description_results[idx][4]
        sperate_description_er_idx = sperate_description_results[idx][4]
        simple_description_er_idx = simple_description_results[idx][4]
        example_description_er_idx = example_description_results[idx][4]

        raw_description_ea_idx = raw_description_results[idx][5]
        sperate_description_ea_idx = sperate_description_results[idx][5]
        simple_description_ea_idx = simple_description_results[idx][5]
        example_description_ea_idx = example_description_results[idx][5]

        if templated_id not in template_results:
            template_results[templated_id] = {
                "raw_description": [],
                "sperate_description": [],
                "simple_description": [],
                "example_description": [],
            }

        template_results[templated_id]["simple_description"].append({
            "query similarity": simple_description_similarity_score_idx,
            "execution rate": simple_description_er_idx,
            "execution accuracy": simple_description_ea_idx
        })
        template_results[templated_id]["raw_description"].append({
            "query similarity": raw_description_similarity_score_idx,
            "execution rate": raw_description_er_idx,
            "execution accuracy": raw_description_ea_idx
        })
        template_results[templated_id]["sperate_description"].append({
            "query similarity": sperate_description_similarity_score_idx,
            "execution rate": sperate_description_er_idx,
            "execution accuracy": sperate_description_ea_idx
        })
        template_results[templated_id]["example_description"].append({
            "query similarity": example_description_similarity_score_idx,
            "execution rate": example_description_er_idx,
            "execution accuracy": example_description_ea_idx
        })

    # results in total
    valid_count = len(raw_description_results)
    raw_description_results['total'] = {"query similarity": raw_description_query_similarity/valid_count,
                                        "execution rate": raw_description_er/valid_count,
                                        "execution accuracy": raw_description_ea/valid_count}
    sperate_description_results['total'] = {"query similarity": sperate_description_query_similarity/valid_count,
                                            "execution rate": sperate_description_er/valid_count,
                                            "execution accuracy": sperate_description_ea/valid_count}
    simple_description_results['total'] = {"query similarity": simple_description_query_similarity/valid_count,
                                              "execution rate": simple_description_er/valid_count,
                                                "execution accuracy": simple_description_ea/valid_count}
    example_description_results['total'] = {"query similarity": example_description_query_similarity/valid_count,
                                                "execution rate": example_description_er/valid_count,
                                                "execution accuracy": example_description_ea/valid_count}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("property_keys_path", nargs='?', default='data/graph/property_keys.json',
                        help="path to Neo4j schema file in JSON format")
    parser.add_argument("schema_path", nargs='?', default='data/graph/schema.json',
                        help="path to Neo4j schema file in JSON format")
    parser.add_argument("graph_path", nargs='?', default='data/graph/',
                        help="path to Neo4j graph files folder")
    parser.add_argument("--load_data", nargs='?', default='/Users/bailanhe/PycharmProjects/siemens/gitlab/query-generator/data/results/results270_20231105_131543.json', help="path to load data")
    args = parser.parse_args()
    main(args.property_keys_path,args.schema_path,args.graph_path,load_data=args.load_data)
    print("Final")
