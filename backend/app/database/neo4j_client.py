import logging
from typing import Optional, Any, Generator
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver, Session

from backend.app.config import settings

logger = logging.getLogger("crimegpt.database.neo4j")

class Neo4jClient:
    """
    A thread-safe Neo4j connection manager that handles driver lifecycle,
    connectivity checks, and session management.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Neo4jClient, cls).__new__(cls, *args, **kwargs)
            cls._instance._driver = None
        return cls._instance

    def __init__(self) -> None:
        # Avoid re-initialization if already initialized
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.uri = settings.NEO4J_URI
        self.username = settings.NEO4J_USERNAME
        self.password = settings.NEO4J_PASSWORD
        self.database = settings.NEO4J_DATABASE
        self._driver: Optional[Driver] = None
        self._initialized = True

    def connect(self) -> None:
        """
        Initializes the Neo4j driver and verifies connectivity.
        """
        if self._driver is not None:
            logger.info("Neo4j driver is already connected.")
            return

        try:
            logger.info(f"Connecting to Neo4j database at {self.uri}...")
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Verify connectivity with a simple ping query
            self.verify_connectivity()
            logger.info("Successfully connected to Neo4j database.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j database: {e}")
            self.close()
            raise e

    def verify_connectivity(self) -> None:
        """
        Checks connection to the Neo4j database by running a test query.
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver is not initialized. Call connect() first.")
        
        self._driver.verify_connectivity()

    def close(self) -> None:
        """
        Closes the Neo4j driver connection.
        """
        if self._driver:
            logger.info("Closing Neo4j driver connection...")
            try:
                self._driver.close()
            except Exception as e:
                logger.error(f"Error closing Neo4j driver: {e}")
            finally:
                self._driver = None

    @property
    def driver(self) -> Driver:
        """
        Returns the active driver instance.
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver is not connected. Call connect() first.")
        return self._driver

    @contextmanager
    def get_session(self, database: Optional[str] = None) -> Generator[Session, None, None]:
        """
        Context manager to retrieve a Neo4j session and ensure proper cleanup.
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver is not connected. Call connect() first.")
        
        target_db = database or self.database
        session = self._driver.session(database=target_db)
        try:
            yield session
        finally:
            session.close()

    def execute_read(self, query: str, parameters: Optional[dict[str, Any]] = None, database: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Executes a read transaction using the session context.
        """
        params = parameters or {}
        with self.get_session(database=database) as session:
            def work(tx):
                result = tx.run(query, **params)
                return [record.data() for record in result]
            return session.execute_read(work)

    def execute_write(self, query: str, parameters: Optional[dict[str, Any]] = None, database: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Executes a write transaction using the session context.
        """
        params = parameters or {}
        with self.get_session(database=database) as session:
            def work(tx):
                result = tx.run(query, **params)
                return [record.data() for record in result]
            return session.execute_write(work)

# Global connection client instance
neo4j_client = Neo4jClient()
