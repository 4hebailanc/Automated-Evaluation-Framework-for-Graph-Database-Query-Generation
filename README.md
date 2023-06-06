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