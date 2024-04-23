# Automated Evaluation Framework for Graph Database Query Generation
## Overview
This project "An Automated Evaluation Framework for Graph Database Query Generation Leveraging Large Language Models," 
is designed to streamline the process of evaluating graph database query generation using large 
language models. By automating various aspects of query generation and evaluation, 
this framework aims to enhance the efficiency and accuracy of graph database query development.

## Components
### 1. chatgpt_client.py
This file provides the necessary login information for accessing the ChatGPT API. ChatGPT is utilized within the framework 
to generate natural language queries based on given parameters and templates.

### 2. neo4j_client.py
neo4j_client.py contains the login information required to connect to a Neo4j graph database. 
Neo4j is a popular choice for graph databases due to its powerful querying capabilities and scalability.

### 3. design_template.json
design_template.json serves as the raw data template for query generation. 
This file contains the structure and specifications required for generating queries. 
Users can customize this template according to their specific graph database schema and requirements.

### 4. data_preparation.py
The data_preparation.py script is responsible for preparing the data required for query generation. 
It processes the raw data template (design_template.json) and transforms it into a format suitable for input into the 
query generation process.

### 5. query_generation.py
query_generation.py is the main script of the framework. 
It utilizes the processed data from data_preparation.py and leverages the ChatGPT model to generate natural language queries. 
These queries are then executed against the Neo4j database, and the results are evaluated based on predefined metrics.

## Getting Started
To utilize this framework, follow these steps:

1. Ensure you have [conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html) installed on your system.
2. Create a new Python 3.11 environment using conda by running the following command in your terminal:
```bash
conda create -n graph_query_env python=3.11
```
3. Activate the newly created environment:
```bash
conda activate graph_query_env
```
4. Install the required dependencies listed in requirements.txt by running:
```bash
pip install -r requirements.txt
```
5. Provide the necessary login credentials in chatgpt_client.py and neo4j_client.py.
6. Customize the design_template.json file according to your graph database schema.
7. Run data_preparation.py to prepare the data for query generation.
8. Execute query_generation.py to generate and evaluate queries against your Neo4j database.
