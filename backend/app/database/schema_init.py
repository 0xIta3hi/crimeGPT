#!/usr/bin/env python
"""
schema_init.py
A standalone script to initialize the Neo4j schema for CrimeGPT.
Drops existing constraints and indexes, then creates uniqueness constraints
and indexes for required node labels with property descriptions in comments.
"""

import os
import sys
import logging

# Set up paths for relative/direct execution imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # backend/
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

from backend.app.database.neo4j_client import neo4j_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("crimegpt.schema_init")

def drop_existing_constraints_and_indexes(session) -> None:
    """
    Drops all existing constraints and indexes in the database to ensure a clean slate.
    """
    logger.info("Starting database clean slate drop phase...")
    
    # 1. Drop constraints
    try:
        constraints = session.run("SHOW CONSTRAINTS").data()
        for c in constraints:
            name = c.get("name")
            if name:
                try:
                    session.run(f"DROP CONSTRAINT {name}")
                    print(f"Dropped constraint: {name}")
                except Exception as e:
                    print(f"Warning: Failed to drop constraint {name}: {e}")
    except Exception as e:
        print(f"Warning: Failed to query constraints via SHOW CONSTRAINTS: {e}")

    # 2. Drop indexes
    try:
        indexes = session.run("SHOW INDEXES").data()
        for idx in indexes:
            name = idx.get("name")
            if name:
                # Skip indexes managed by constraints or system lookup indexes
                if idx.get("owningConstraint") or idx.get("type") == "LOOKUP":
                    continue
                try:
                    session.run(f"DROP INDEX {name}")
                    print(f"Dropped index: {name}")
                except Exception as e:
                    print(f"Warning: Failed to drop index {name}: {e}")
    except Exception as e:
        print(f"Warning: Failed to query indexes via SHOW INDEXES: {e}")

    logger.info("Drop phase complete.")

def create_uniqueness_constraint(session, name: str, label: str, property_name: str) -> None:
    """
    Creates a uniqueness constraint using modern Neo4j 4.4+ syntax with a legacy fallback.
    """
    try:
        session.run(f"CREATE CONSTRAINT {name} FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE")
        print(f"Created uniqueness constraint: {name} on {label}({property_name})")
    except Exception as e:
        try:
            # Fallback to pre-4.4 syntax
            session.run(f"CREATE CONSTRAINT {name} ON (n:{label}) ASSERT n.{property_name} IS UNIQUE")
            print(f"Created uniqueness constraint (legacy syntax): {name} on {label}({property_name})")
        except Exception as e_inner:
            logger.error(f"Failed to create uniqueness constraint {name} on {label}({property_name}): {e_inner}")
            raise e_inner

def create_range_index(session, name: str, label: str, property_name: str) -> None:
    """
    Creates a range index using modern Neo4j syntax with a legacy fallback.
    """
    try:
        session.run(f"CREATE INDEX {name} FOR (n:{label}) ON (n.{property_name})")
        print(f"Created range index: {name} on {label}({property_name})")
    except Exception as e:
        try:
            # Fallback to pre-4.4 syntax
            session.run(f"CREATE INDEX ON :{label}({property_name})")
            print(f"Created range index (legacy syntax) on {label}({property_name})")
        except Exception as e_inner:
            logger.warning(f"Could not create range index {name} on {label}({property_name}): {e_inner}")

def main() -> None:
    logger.info("Connecting to Neo4j database...")
    neo4j_client.connect()
    
    with neo4j_client.get_session() as session:
        # Step 1: Clean slate drop
        drop_existing_constraints_and_indexes(session)
        
        # Step 2: Create constraints and indexes with full property sets commented
        
        # ==============================================================================
        # Node Label: Case
        # Full Property Set:
        #   - case_id: String (Unique identification for the case / FIR number)
        #   - title: String (Short summary title for the case file)
        #   - status: String (Case investigation status: e.g., Open, Under Investigation, Closed)
        #   - date_filed: String (ISO format date when the FIR/Case was registered)
        #   - description: String (Detailed textual description of the crime narrative)
        # ==============================================================================
        create_uniqueness_constraint(session, "case_id_unique", "Case", "case_id")
        print("Confirmation: Case.case_id uniqueness constraint setup verified.")
        
        # ==============================================================================
        # Node Label: Person
        # Full Property Set:
        #   - canonical_id: String (Unique identifier for the individual, e.g. national ID or system hash)
        #   - name: String (Full name of the person)
        #   - dob: String (Date of birth)
        #   - gender: String (Gender)
        #   - contact_number: String (Phone / contact details)
        #   - address: String (Residential address)
        # ==============================================================================
        create_uniqueness_constraint(session, "person_canonical_id_unique", "Person", "canonical_id")
        print("Confirmation: Person.canonical_id uniqueness constraint setup verified.")
        
        # ==============================================================================
        # Node Label: Officer
        # Full Property Set:
        #   - badge_id: String (Unique badge identifier of the officer)
        #   - name: String (Full name of the officer)
        #   - rank: String (Officer rank, e.g. inspector, deputy commissioner)
        #   - department: String (Department or station unit name)
        #   - contact_number: String (Official mobile or phone extension number)
        # ==============================================================================
        create_uniqueness_constraint(session, "officer_badge_id_unique", "Officer", "badge_id")
        print("Confirmation: Officer.badge_id uniqueness constraint setup verified.")
        
        # ==============================================================================
        # Node Label: BNS_Section
        # Full Property Set:
        #   - section_id: String (Unique BNS Section identifier, e.g., '103(1)')
        #   - section_number: String (Compatible string matching exact section number, e.g., '103')
        #   - title: String (Official title of the BNS section, e.g., 'Punishment for Murder')
        #   - text: String (One sentence description of the crime or provision)
        #   - description: String (Detailed description of the provision for compatibility)
        #   - punishment: String (Legal penalty / sentencing parameters defined)
        #   - offense_category: String (Assigned offense category, e.g., 'murder', 'theft')
        # ==============================================================================
        create_uniqueness_constraint(session, "bns_section_id_unique", "BNS_Section", "section_id")
        print("Confirmation: BNS_Section.section_id uniqueness constraint setup verified.")
        
        # ==============================================================================
        # Node Label: Judgment
        # Full Property Set:
        #   - citation: String (Unique citation code, e.g. 'AIR 1980 SC 898')
        #   - court: String (Issuing court, e.g. 'Supreme Court of India')
        #   - year: Integer (Year of delivery)
        #   - ratio_decidendi: String (One sentence legal principle established by the court)
        #   - keywords: List of Strings (Keywords for searching and categorization)
        # ==============================================================================
        create_uniqueness_constraint(session, "judgment_citation_unique", "Judgment", "citation")
        print("Confirmation: Judgment.citation uniqueness constraint setup verified.")
        
        # ==============================================================================
        # Node Label: Evidence
        # Full Property Set:
        #   - evidence_id: String (Unique cataloging code for the piece of evidence)
        #   - name: String (Name or short descriptor of the item)
        #   - type: String (Evidence type: Physical, Forensic, Digital, Documentary)
        #   - description: String (Condition, characteristics, and details of the evidence)
        #   - date_collected: String (Date when retrieved by investigators)
        #   - location_collected: String (Location descriptor where item was retrieved)
        # ==============================================================================
        create_range_index(session, "evidence_id_idx", "Evidence", "evidence_id")
        print("Confirmation: Evidence.evidence_id range index setup verified.")
        
        # ==============================================================================
        # Node Label: Location
        # Full Property Set:
        #   - location_id: String (Unique reference identifier for the place)
        #   - name: String (Name of place, landmark, or intersection)
        #   - address: String (Detailed street address)
        #   - latitude: Float (GPS Coordinate latitude)
        #   - longitude: Float (GPS Coordinate longitude)
        # ==============================================================================
        create_range_index(session, "location_id_idx", "Location", "location_id")
        print("Confirmation: Location.location_id range index setup verified.")
        
        # ==============================================================================
        # Node Label: Offense
        # Full Property Set:
        #   - offense_id: String (Unique tracking ID of the offense occurrence)
        #   - name: String (Name of crime occurrence, e.g. 'Robbery at Bank')
        #   - description: String (Incident description mapping to legal definitions)
        #   - category: String (Crime classification, e.g., 'robbery')
        # ==============================================================================
        create_range_index(session, "offense_id_idx", "Offense", "offense_id")
        print("Confirmation: Offense.offense_id range index setup verified.")
        
        # ==============================================================================
        # Node Label: Document
        # Full Property Set:
        #   - doc_id: String (Unique cataloging system code for the document)
        #   - name: String (Document filename or title, e.g., 'FIR_12_2026.pdf')
        #   - type: String (Type: FIR, Witness Statement, Forensic Report, Charge Sheet)
        #   - file_path: String (Local file path or URL storage location)
        #   - content_text: String (Text extracted via OCR/PDF parsing)
        # ==============================================================================
        create_range_index(session, "document_id_idx", "Document", "doc_id")
        print("Confirmation: Document.doc_id range index setup verified.")

        # ==============================================================================
        # Node Label: Insight
        # Full Property Set:
        #   - insight_id: String (uuid) (Unique identification for the insight)
        #   - type: String ("pattern_match" | "link_analysis" | "recidivism_flag" | "location_cluster" | "mo_pattern" | "shared_evidence")
        #   - severity: String ("low" | "medium" | "high" | "critical")
        #   - title: String (Short title for the insight)
        #   - description: String (Detailed textual description of the insight)
        #   - generated_at: String (ISO format datetime when the insight was generated)
        #   - read: Boolean (default false) (Indicates if the analyst has read the insight)
        #   - triggered_by: String ("scheduler" | "new_case_event" | "new_person_event")
        #   - analyst_feedback: String ("none" | "confirmed" | "false_positive") (default "none")
        #   - feedback_at: String (ISO format datetime of feedback, nullable)
        #   - auto_suppressed: Boolean (default false) (Set when analyst marks similar insight as false_positive)
        # ==============================================================================
        create_uniqueness_constraint(session, "insight_id_unique", "Insight", "insight_id")
        print("Confirmation: Insight.insight_id uniqueness constraint setup verified.")

        create_range_index(session, "insight_severity_idx", "Insight", "severity")
        print("Confirmation: Insight.severity range index setup verified.")

        create_range_index(session, "insight_generated_at_idx", "Insight", "generated_at")
        print("Confirmation: Insight.generated_at range index setup verified.")

        create_range_index(session, "insight_read_idx", "Insight", "read")
        print("Confirmation: Insight.read range index setup verified.")

        create_range_index(session, "insight_auto_suppressed_idx", "Insight", "auto_suppressed")
        print("Confirmation: Insight.auto_suppressed range index setup verified.")
        
    logger.info("Neo4j Schema Initialization completed successfully.")

if __name__ == "__main__":
    main()
