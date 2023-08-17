# Query Generator

## Getting started
 
This repository contains code for an automatic cypher query generator using large language models. The main idea behind this project is to enable the generation of cypher queries from natural language input.

## Installation
 
To install the necessary dependencies, please run: `pip install -r requirements.txt` 

## Usage

First specify the API credentials in the file [api_credentials](app/api_credentials.json). 

To find the relevant information:

* Navigate to https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/overview,
* Select "Azure OpenAI" in the menu on the left,
* In the list of subscriptions, select "OpenAI-aiattack-000898-westeurope-02",
* In the menu on the left, select "Keys and Endpoint".

To start the app, run: `streamlit run app.py`

This will launch the app in your default web browser.

## Output Files
* propertyKeys.json is in the format as below, where the key of the json is the nodes/edges and the values are the properties respectively to the nodes/edges
```
{
    "Supplier":["name","bp_name","ifa","duns","prewave_id","prewave_link","website"]
    ,"SUPPLIES_TO":["tier","edge_sources"]
} 
```
* propertiesQuantile.json is in the format as below, where the key of the json is the numeric properties of nodes/edges and the values are 25th, 50th, 75th quantile of the properties. Values may be null.
```
{
    "country_risk":[25,50,75],
    "sustainability_risk":[25,50,75]
}
```
* template.json is in the format as below, where the key is the general form of the cypher query and the first value is the general description of it, second to the ninth values are different variation of the query.
```
{
    "MATCH (n:node) RETURN n": [
        "Find all nodes and return all nodes.",
        "MATCH (n:SiemensPart) RETURN n",
        "MATCH (n:Branch) RETURN n",
        "MATCH (n:Smelter) RETURN n",
        "MATCH (n:BusinessPartner) RETURN n",
        "MATCH (n:BusinessScope) RETURN n",
        "MATCH (n:Country) RETURN n",
        "MATCH (n:Substance) RETURN n",
        "MATCH (n:Supplier) RETURN n",
        "MATCH (n:ManufacturerPart) RETURN n",
        "MATCH (n:Component) RETURN n"
    ]
}
```
* nodesRelations.json is in the format as below, where the key is the relationship/edge for the nodes and the nested key is the subject node and the corressponding values are the object nodes.
```
{
    "rel":{
        "sub1":["obj1","obj2"],
        "sub2":["obj3"]

    },
    "SUPPLIES_TO":{
        "Supplier":["Supplier","Smelter"],
        "Smelter":["Supplier"]
    }
}
```
* template_description.json is the result of the different promt for a cypher query, where the key is the query and the values are the result of no additional information given, give an example (context learing), and give schema accordingly

* nodestypes.txt is the list of all node types from the database.

## Reference
* https://neo4j.com/docs/cypher-manual/current/query-tuning/query-profile/
* https://docs.google.com/document/d/1gvKdDt9DjsTgN97vJ4tZwTDY4QsdVO4Qrr16TeSMPt0/edit?usp=sharing