// Verify labels
CALL db.labels() YIELD label RETURN label ORDER BY label;

// Verify relationship types
CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType;

// Count core nodes
MATCH (m:Movie) RETURN count(m) AS movies;
MATCH (p:Person) RETURN count(p) AS people;

// Inspect sample movies
MATCH (m:Movie) RETURN m LIMIT 5;

// Inspect sample people
MATCH (p:Person) RETURN p LIMIT 5;

// Inspect relationships
MATCH (p:Person)-[r]->(m:Movie) RETURN p, r, m LIMIT 10;
