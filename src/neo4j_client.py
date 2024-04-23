from neo4j import GraphDatabase


class Neo4jClient:
    """
        This module provides a Neo4jClient class that allows the user to connect to a Neo4j database and execute
        Cypher queries.
    """

    def __init__(self, uri, user, password, database):
        """
        Constructor for Neo4jClient class.

        Args:
        uri (str): The URI of the Neo4j database.
        user (str): The username to authenticate with the Neo4j database.
        password (str): The password to authenticate with the Neo4j database.
        database (str): The name of the database to connect to.
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database

    def _connect_to_neo4j(self):
        """
        Establishes a connection to the Neo4j database.

        Returns:
        driver: A driver object representing the Neo4j database connection.
        """
        with GraphDatabase.driver(self.uri, auth=(self.user, self.password)) as driver:
            driver.verify_connectivity()
        return driver

    def execute_cypher_query(self, cypher_query):
        """
        Executes a Cypher query against the Neo4j database.

        Args:
        cypher_query (str): The Cypher query to execute.

        Returns:
        records: A list of dictionaries representing the query results.
        """
        driver = self._connect_to_neo4j()
        with driver.session(database=self.database) as session:
            result = session.run(cypher_query).data()
            records = [record for record in result]
        driver.close()
        return records

    def check_and_execute_cypher_query(self, cypher_query):
        """
        Executes a Cypher query against the Neo4j database.

        Args:
        cypher_query (str): The Cypher query to execute.

        Returns:
        records: A list of dictionaries representing the query results.
        """

        try:
            driver = self._connect_to_neo4j()
            with (driver.session(database=self.database) as session):
                result = session.run(cypher_query).data()
                records = [record for record in result]
            driver.close()
            executable = True
        except:
            records = 'None'
            executable = False

        return ([records,executable])
