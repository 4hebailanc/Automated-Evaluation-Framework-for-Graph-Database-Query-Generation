# Description: This script processes the CSV file and loads the data into Neo4j
import csv
from neo4j import GraphDatabase

# Define your Neo4j connection details
neo4j_uri = "bolt://localhost:7689"
neo4j_username = "neo4j"
neo4j_password = "bailanhe"
driver = GraphDatabase.driver(uri = neo4j_uri , auth=(neo4j_username, neo4j_password))

# Define the CSV file path
csv_file = "/Users/bailanhe/PycharmProjects/siemens/open-query-generation/data/emdat.csv"

# Define the mapping for node labels
ignore_list = ["http://www.opengis.net/ont/geosparql#hasGeometry",
               "http://www.opengis.net/ont/geosparql#asWKT",
               "https://schema.coypu.org/global#hasGlideId"]

# Define the mapping for node labels and relation names
relation_mapping = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "TYPE",
    "https://schema.coypu.org/global#hasYear": "YEAR",
    "https://schema.coypu.org/global#hasAffectedRegion": "AFFECTED_REGION"
}

# Define the mapping for node properties
property_mapping = {
    "https://schema.coypu.org/global#hasStartDate": "START_DATE",
    "https://schema.coypu.org/global#hasEndDate": "END_DATE",
    "https://schema.coypu.org/global#hasLongitude": "LONGITUDE",
    "https://schema.coypu.org/global#hasLocation": "LOCATION",
    "https://schema.coypu.org/global#hasLatitude": "LATITUDE",
    "https://schema.coypu.org/global#hasAdminLevel": "ADMIN_LEVEL",
    "https://schema.coypu.org/global#hasCountryLocation": "COUNTRY_LOCATION"
}

# Define the mapping for node labels and relation names
# node_label_mapping = {
#     "http://www.w3.org/2000/01/rdf-schema#label": "Label"
# }

# Open the CSV file and process the data
with open(csv_file, 'r') as file:
    reader = csv.reader(file)
    for row in reader:

        # deal with the case where the object contains a comma
        if len(row) < 3:
            row = row[0].split(",", 2)
            if "\"" in row[2]:
                row[2] = row[2].replace("\"", "")

        # Extract the subject, relation, and object from the triplet
        subject = row[0].strip()
        relation = row[1].strip()
        object = row[2].strip()
        if relation in ignore_list:
            continue

        with driver.session() as session:
            session.run("MERGE (s {value: $subject}) "
                        "MERGE (o {value: $object}) ", subject=subject, object=object)

        # TODO: Add the node label
        if relation == "http://www.w3.org/2000/01/rdf-schema#label":
            with driver.session() as session:
                session.run("MATCH (n {value: $subject}) "
                            "SET n:`" + object + "`", subject=subject)

        if relation in relation_mapping:
            type = relation_mapping.get(relation, "Unknown")
            with driver.session() as session:
                session.run("MATCH (s {value: $subject}) "
                            "MATCH (o {value: $object}) "
                            "MERGE (s)-[:" + type + "]->(o)", subject=subject, object=object)

        elif relation in property_mapping:
            property_name = property_mapping.get(relation)
            if relation == "https://schema.coypu.org/global#hasCountryLocation":
                object = object.split("/")[-1]
            with driver.session() as session:
                session.run("MATCH (s {value: $subject}) "
                            "SET s." + property_name.lower() + " = $object", subject=subject, object=object)

# Close the Neo4j driver
driver.close()
