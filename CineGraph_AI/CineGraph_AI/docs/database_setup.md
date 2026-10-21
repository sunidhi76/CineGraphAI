# Database setup

## AuraDB

1. Create a Neo4j AuraDB instance.
2. Copy the Bolt/Neo4j URI and credentials into `.env`.
3. Open Neo4j Workspace/Browser for the instance.
4. Load the official Neo4j Movies sample graph using the sample-data workflow available for your Neo4j version.
5. Run `database/setup_queries.cypher` to verify labels, relationships, and records.

## Local Neo4j

1. Install and start Neo4j Desktop or Neo4j Server.
2. Create a database and record its Bolt URI, username and password.
3. Load the Movies sample graph into that database.
4. Put the connection values in `.env`.
5. Run the setup queries.

Creating the database and loading the sample dataset are separate steps. CineGraph AI does not bundle the database or silently create it.
