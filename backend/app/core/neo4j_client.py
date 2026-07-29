"""
Neo4j Client — EnterpriseMind AI.

Singleton connection ke Neo4j graph database.
Lifecycle: connect pada first use, close saat shutdown.

Ref: GRAPH_PLAN.md §5.2
"""

import logging

from neo4j import GraphDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)

_driver = None


def get_neo4j() -> GraphDatabase.driver:
    global _driver
    if _driver is None:
        uri = settings.NEO4J_URI
        user = settings.NEO4J_USER
        password = settings.NEO4J_PASSWORD
        logger.info("Connecting to Neo4j: %s", uri)
        _driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_lifetime=3600,
            connection_timeout=10,
            max_connection_pool_size=5,
        )
        with _driver.session() as session:
            session.run("RETURN 1")
        logger.info("Neo4j connected successfully.")
    return _driver


async def close_neo4j():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("Neo4j connection closed.")


def verify_neo4j_health() -> bool:
    try:
        driver = get_neo4j()
        with driver.session() as session:
            result = session.run("MATCH (n:Entity) RETURN count(n) AS count")
            record = result.single()
            logger.info("Neo4j health OK: %d entities", record["count"] if record else 0)
        return True
    except Exception as e:
        logger.warning("Neo4j health check failed: %s", e)
        return False


def init_neo4j_schema():
    """Create constraints and indexes if they don't exist."""
    driver = get_neo4j()
    with driver.session() as session:
        session.run("CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
        session.run("CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)")
        session.run("CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)")
        logger.info("Neo4j schema initialized: constraints + indexes created.")
