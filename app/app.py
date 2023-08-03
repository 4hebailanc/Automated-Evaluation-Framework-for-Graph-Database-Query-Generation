import sys
sys.path.append('./')

import argparse
import json
import streamlit as st
from src.chatgpt_client import ChatGPTClient
from src.neo4j_client import Neo4jClient
from neo4j import GraphDatabase

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


# Define the Streamlit app
def main(schema_path='data/schema.json'):
    # Load the schema
    with open('data/schema.json') as f:
        schema = json.load(f)
    with open('data/property_keys.json') as g:
        property_keys = json.load(g)

        # Set the title of the app
    st.title("Neo4j Query Generator")

    # Add custom CSS to the app
    st.markdown(
        """        
        <style>        
            body {        
                background-color: #FFFFFF;        
            }        
            h1 {        
                color: #009999;        
            }        
        </style>        
        """,
        unsafe_allow_html=True
    )

    # Add a text input for the natural language description
    description = st.text_input("Enter a natural language description of your query:")

    # Add a text input for additional instructions
    additional_instructions = st.text_input("Enter additional instructions for the query:")

    # Add a button to generate the Cypher query
    if st.button("Generate Query"):
        # Generate the Cypher query and the step-by-step explanation
        generated_query = generate_cypher_query(description, additional_instructions, schema, property_keys)

        # Print the generated Cypher query
        st.write("Generated Cypher query:")
        st.code(generated_query, language="cypher")

        # Add a text input for the Cypher query
    cypher_query = st.text_input("Enter a Cypher query:")

    # Add a button to execute the Cypher query
    if st.button("Execute Query"):
        # If a Cypher query has been entered, execute it against the Neo4j graph
        if cypher_query:
            result = neo4j_client.execute_cypher_query(cypher_query)
            st.write("Query result:")
            st.write(result)

            # Add a button to clear the input fields
    if st.button("Clear"):
        description = ""
        additional_instructions = ""
        cypher_query = ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("schema_path", nargs='?', default='data/schema.json',
                        help="path to Neo4j schema file in JSON format")
    args = parser.parse_args()

    main(args.schema_path)
