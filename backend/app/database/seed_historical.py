#!/usr/bin/env python
"""
seed_historical.py
A standalone script to seed Neo4j with 50 mock historical cases
designed to guarantee target patterns for the CrimeGPT Insight Engine.
"""

import os
import sys
import uuid
import logging
from datetime import datetime, timedelta

# Set up paths for relative/direct execution imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # backend/
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

from backend.app.database.neo4j_client import neo4j_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("crimegpt.seed_historical")

# Target location data (5 distinct locations)
LOCATIONS = [
    {
        "location_id": "LOC-HIST-1",
        "name": "Navrangpura Police Jurisdiction",
        "address": "Navrangpura, Ahmedabad",
        "latitude": 23.0338,
        "longitude": 72.5638
    },
    {
        "location_id": "LOC-HIST-2",
        "name": "Satellite Police Jurisdiction",
        "address": "Satellite, Ahmedabad",
        "latitude": 23.0305,
        "longitude": 72.5178
    },
    {
        "location_id": "LOC-HIST-3",
        "name": "Vastrapur Police Jurisdiction",
        "address": "Vastrapur, Ahmedabad",
        "latitude": 23.0350,
        "longitude": 72.5293
    },
    {
        "location_id": "LOC-HIST-4",
        "name": "Ghatlodia Police Jurisdiction",
        "address": "Ghatlodia, Ahmedabad",
        "latitude": 23.0645,
        "longitude": 72.5401
    },
    {
        "location_id": "LOC-HIST-5",
        "name": "Kalupur Police Jurisdiction",
        "address": "Kalupur, Ahmedabad",
        "latitude": 23.0301,
        "longitude": 72.5971
    }
]

# Target Officer data (4 distinct officers)
OFFICERS = [
    {"badge_id": "BADGE-1001", "name": "Officer Patel"},
    {"badge_id": "BADGE-1002", "name": "Officer Shah"},
    {"badge_id": "BADGE-1003", "name": "Officer Mehta"},
    {"badge_id": "BADGE-1004", "name": "Officer Joshi"}
]

def clean_slate_historical(session) -> None:
    """
    Cleans up all Case-related nodes (Case, Person, CanonicalPerson, Officer, Location, Evidence, Document)
    without touching the core BNS_Section and Judgment knowledge base.
    """
    logger.info("Cleaning existing case files, entities, and evidence from the database...")
    query = """
    MATCH (n)
    WHERE NOT n:BNS_Section AND NOT n:Judgment
    DETACH DELETE n
    """
    session.run(query)
    logger.info("Database cleaned successfully.")

def seed_historical_cases(session) -> None:
    # Base date: 2026-06-15
    base_date = datetime(2026, 6, 15)

    logger.info("Seeding 50 historical cases...")
    for i in range(1, 51):
        case_id = f"HIST-CASE-{i:02d}"
        fir_number = f"FIR-HIST-{i:02d}"
        ps_code = f"PS-GJ-AMD-{i:02d}"
        
        # 1. Determine status
        status = "open" if i % 2 != 0 else "closed"

        # 2. Determine location and date_filed (Location cluster criteria)
        # Navrangpura (Index 0) must appear most frequently.
        # Let's map i <= 14 (14 cases) to Navrangpura, and others to 1-4.
        if i <= 14:
            location = LOCATIONS[0]
            # Must be filed within last 90 days
            days_ago = (i * 5) % 90 + 1
        else:
            location = LOCATIONS[(i % 4) + 1]
            # Filed within last 180 days
            days_ago = (i * 3.5) % 180 + 1
            
        date_filed = (base_date - timedelta(days=int(days_ago))).strftime("%Y-%m-%d")

        # 3. Determine modus operandi and offense category (MO pattern criteria)
        # 6 cases with category "theft" having modus_operandi "snatch_and_run" (Cases 22 to 27)
        if 22 <= i <= 27:
            offense_category = "theft"
            modus_operandi = "snatch_and_run"
            rag_sections = ["303(2)"]
        else:
            modus_operandi = None
            # Cycle through other categories
            cat_idx = i % 5
            if cat_idx == 0:
                offense_category = "murder"
                rag_sections = ["103(1)"]
            elif cat_idx == 1:
                offense_category = "assault"
                rag_sections = ["115(1)"]
            elif cat_idx == 2:
                offense_category = "theft"
                rag_sections = ["303(2)"]
            elif cat_idx == 3:
                offense_category = "robbery"
                rag_sections = ["309(4)"]
            else:
                offense_category = "kidnapping"
                rag_sections = ["137(2)"]

        # Create the Case node
        case_query = """
        CREATE (c:Case {
            case_id: $case_id,
            fir_number: $fir_number,
            ps_code: $ps_code,
            date_filed: $date_filed,
            status: $status,
            modus_operandi: $modus_operandi,
            offense_category: $offense_category,
            rag_sections: $rag_sections
        })
        """
        session.run(case_query, {
            "case_id": case_id,
            "fir_number": fir_number,
            "ps_code": ps_code,
            "date_filed": date_filed,
            "status": status,
            "modus_operandi": modus_operandi,
            "offense_category": offense_category,
            "rag_sections": rag_sections
        })

        # 4. Officer link
        officer = OFFICERS[i % 4]
        officer_query = """
        MERGE (o:Officer {badge_id: $badge_id})
        ON CREATE SET o.name = $name
        WITH o
        MATCH (c:Case {case_id: $case_id})
        CREATE (o)-[:INVESTIGATING]->(c)
        """
        session.run(officer_query, {
            "badge_id": officer["badge_id"],
            "name": officer["name"],
            "case_id": case_id
        })

        # 5. Location link
        location_query = """
        MERGE (l:Location {address: $address})
        ON CREATE SET 
            l.location_id = $location_id, 
            l.name = $name, 
            l.latitude = $latitude, 
            l.longitude = $longitude
        WITH l
        MATCH (c:Case {case_id: $case_id})
        CREATE (c)-[:OCCURRED_AT]->(l)
        """
        session.run(location_query, {
            "address": location["address"],
            "location_id": location["location_id"],
            "name": location["name"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "case_id": case_id
        })

        # 6. Accused Person & Entity Resolution (Recidivism pattern criteria)
        # Recidivist 1 (Aadhar: AADHAR-RECID-1) in cases 1, 2, 3
        # Recidivist 2 (Aadhar: AADHAR-RECID-2) in cases 4, 5, 6
        # Recidivist 3 (Aadhar: AADHAR-RECID-3) in cases 7, 8, 9
        if 1 <= i <= 3:
            name = ["Ramesh Patel", "Ramu Snatcher", "Ramesh Bhai"][i - 1]
            aadhar_hash = "AADHAR-RECID-1"
        elif 4 <= i <= 6:
            name = ["Suresh Shah", "Suryo", "Suresh Kumar"][i - 4]
            aadhar_hash = "AADHAR-RECID-2"
        elif 7 <= i <= 9:
            name = ["Alok Mehta", "Alloo", "Alok Sharma"][i - 7]
            aadhar_hash = "AADHAR-RECID-3"
        else:
            name = f"Accused Person {i:02d}"
            aadhar_hash = f"AADHAR-HIST-{i:02d}"

        person_canonical_id = str(uuid.uuid4())
        person_query = """
        MATCH (c:Case {case_id: $case_id})
        CREATE (p:Person {
            canonical_id: $person_canonical_id,
            name: $name,
            case_id: $case_id,
            role: "accused",
            aadhar_hash: $aadhar_hash
        })
        CREATE (p)-[:ACCUSED_IN]->(c)
        
        WITH p
        MERGE (cp:CanonicalPerson {aadhar_hash: $aadhar_hash})
        ON CREATE SET 
            cp.case_count = 1,
            cp.aliases = [$name],
            cp.case_ids = [$case_id],
            cp.first_seen_case = $case_id
        ON MATCH SET
            cp.case_count = cp.case_count + 1,
            cp.aliases = case when not $name in cp.aliases then cp.aliases + $name else cp.aliases end,
            cp.case_ids = case when not $case_id in cp.case_ids then cp.case_ids + $case_id else cp.case_ids end
        
        CREATE (p)-[:RESOLVES_TO]->(cp)
        """
        session.run(person_query, {
            "case_id": case_id,
            "person_canonical_id": person_canonical_id,
            "name": name,
            "aadhar_hash": aadhar_hash
        })

        # 7. Evidence link (Shared evidence criteria)
        # GJ-01 black Honda Activa in cases 18, 19, 20, 21
        if 18 <= i <= 21:
            evidence_desc = "Honda Activa, Black, GJ-01"
            evidence_type = "Vehicle"
        else:
            evidence_desc = f"Seized evidence item cataloged for case {case_id}"
            evidence_type = "Physical"

        evidence_id = str(uuid.uuid4())
        evidence_query = """
        MATCH (c:Case {case_id: $case_id})
        CREATE (e:Evidence {
            evidence_id: $evidence_id,
            description: $description,
            type: $type
        })
        CREATE (e)-[:SEIZED_IN]->(c)
        """
        session.run(evidence_query, {
            "case_id": case_id,
            "evidence_id": evidence_id,
            "description": evidence_desc,
            "type": evidence_type
        })

    logger.info("Successfully seeded all 50 historical cases.")

def print_summary(session) -> None:
    total_cases = session.run("MATCH (c:Case) RETURN count(c) as count").single()["count"]
    total_persons = session.run("MATCH (p:Person) RETURN count(p) as count").single()["count"]
    total_canonical = session.run("MATCH (cp:CanonicalPerson) RETURN count(cp) as count").single()["count"]
    total_evidence = session.run("MATCH (e:Evidence) RETURN count(e) as count").single()["count"]
    total_locations = session.run("MATCH (l:Location) RETURN count(l) as count").single()["count"]
    cross_case = session.run("MATCH (cp:CanonicalPerson) WHERE cp.case_count > 1 RETURN count(cp) as count").single()["count"]

    print("\n" + "="*50)
    print("HISTORICAL SEEDING SUMMARY")
    print("="*50)
    print(f"Total Cases created: {total_cases}")
    print(f"Total Persons created: {total_persons}")
    print(f"Total CanonicalPersons created: {total_canonical}")
    print(f"Total Evidence nodes created: {total_evidence}")
    print(f"Total Location nodes created: {total_locations}")
    print(f"Cross-case CanonicalPersons (case_count > 1): {cross_case}")
    print("="*50 + "\n")

def main() -> None:
    logger.info("Connecting to Neo4j database...")
    neo4j_client.connect()
    
    with neo4j_client.get_session() as session:
        # Step 1: Clean slate for case nodes
        clean_slate_historical(session)
        
        # Step 2: Seed cases and links
        seed_historical_cases(session)
        
        # Step 3: Print summary
        print_summary(session)
        
    logger.info("Historical database seeding completed successfully.")

if __name__ == "__main__":
    main()
