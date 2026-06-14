#!/usr/bin/env python
"""
seed_data.py
A standalone script to seed Neo4j with BNS 2023 sections, landmark Indian judgments,
and relationships (INTERPRETS, CROSS_REFERENCES).
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
logger = logging.getLogger("crimegpt.seed_data")

# Exactly 20 BNS sections covering the 10 required categories
bns_sections = [
    # 1. Murder
    {
        "section_id": "103(1)",
        "section_number": "103(1)",
        "title": "Punishment for Murder",
        "text": "Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.",
        "description": "Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.",
        "punishment": "Death penalty or imprisonment for life, and fine",
        "offense_category": "murder"
    },
    {
        "section_id": "103(2)",
        "section_number": "103(2)",
        "title": "Group Murder",
        "text": "Punishment for murder committed by a group of five or more persons on grounds of race, caste, community, sex, place of birth, language, personal belief or any other similar ground.",
        "description": "Punishment for murder committed by a group of five or more persons on grounds of race, caste, community, sex, place of birth, language, personal belief or any other similar ground.",
        "punishment": "Death penalty or life imprisonment or imprisonment for seven years or more, and fine",
        "offense_category": "murder"
    },
    # 2. Assault
    {
        "section_id": "115(1)",
        "section_number": "115(1)",
        "title": "Voluntarily Causing Hurt",
        "text": "Whoever does any act with the intention of thereby causing hurt to any person, or with the knowledge that he is likely thereby to cause hurt, commits voluntarily causing hurt.",
        "description": "Whoever does any act with the intention of thereby causing hurt to any person, or with the knowledge that he is likely thereby to cause hurt, commits voluntarily causing hurt.",
        "punishment": "Imprisonment up to one year, or fine up to ten thousand rupees, or both",
        "offense_category": "assault"
    },
    {
        "section_id": "117(1)",
        "section_number": "117(1)",
        "title": "Voluntarily Causing Grievous Hurt",
        "text": "Whoever voluntarily causes hurt, if the hurt which he intends to cause or knows himself to be likely to cause is grievous hurt, commits voluntarily causing grievous hurt.",
        "description": "Whoever voluntarily causes hurt, if the hurt which he intends to cause or knows himself to be likely to cause is grievous hurt, commits voluntarily causing grievous hurt.",
        "punishment": "Imprisonment up to seven years, and fine",
        "offense_category": "assault"
    },
    # 3. Theft
    {
        "section_id": "303(2)",
        "section_number": "303(2)",
        "title": "Theft",
        "text": "Whoever commits theft shall be punished with imprisonment for a term which may extend to three years, or with fine, or with both.",
        "description": "Whoever commits theft shall be punished with imprisonment for a term which may extend to three years, or with fine, or with both.",
        "punishment": "Imprisonment up to three years, or fine, or both, or community service for first conviction under five thousand rupees",
        "offense_category": "theft"
    },
    {
        "section_id": "305",
        "section_number": "305",
        "title": "Theft in Dwelling House, etc.",
        "text": "Whoever commits theft in any building, tent or vessel, which building, tent or vessel is used as a human dwelling, or for the custody of property, commits theft in dwelling house.",
        "description": "Whoever commits theft in any building, tent or vessel, which building, tent or vessel is used as a human dwelling, or for the custody of property, commits theft in dwelling house.",
        "punishment": "Imprisonment up to seven years, and fine",
        "offense_category": "theft"
    },
    # 4. Robbery
    {
        "section_id": "309(4)",
        "section_number": "309(4)",
        "title": "Robbery",
        "text": "In all robbery there is either theft or extortion committed under threat of instant death, hurt, or wrongful restraint.",
        "description": "In all robbery there is either theft or extortion committed under threat of instant death, hurt, or wrongful restraint.",
        "punishment": "Rigorous imprisonment up to ten years, and fine; if committed on highway between sunset and sunrise, up to fourteen years",
        "offense_category": "robbery"
    },
    {
        "section_id": "310(1)",
        "section_number": "310(1)",
        "title": "Dacoity",
        "text": "When five or more persons conjointly commit or attempt to commit a robbery, they are said to commit dacoity.",
        "description": "When five or more persons conjointly commit or attempt to commit a robbery, they are said to commit dacoity.",
        "punishment": "Imprisonment for life, or rigorous imprisonment up to ten years, and fine",
        "offense_category": "robbery"
    },
    # 5. Kidnapping
    {
        "section_id": "137(2)",
        "section_number": "137(2)",
        "title": "Kidnapping",
        "text": "Whoever kidnaps any person from India or from lawful guardianship shall be punished with imprisonment up to seven years, and fine.",
        "description": "Whoever kidnaps any person from India or from lawful guardianship shall be punished with imprisonment up to seven years, and fine.",
        "punishment": "Imprisonment up to seven years, and fine",
        "offense_category": "kidnapping"
    },
    {
        "section_id": "140",
        "section_number": "140",
        "title": "Kidnapping or Abducting in Order to Murder",
        "text": "Whoever kidnaps or abducts any person in order that such person may be murdered or so disposed of as to be put in danger of being murdered.",
        "description": "Whoever kidnaps or abducts any person in order that such person may be murdered or so disposed of as to be put in danger of being murdered.",
        "punishment": "Rigorous imprisonment up to ten years, and fine",
        "offense_category": "kidnapping"
    },
    # 6. Cybercrime
    {
        "section_id": "318(4)",
        "section_number": "318(4)",
        "title": "Cheating and Dishonestly Inducing Delivery of Property",
        "text": "Whoever cheats and thereby dishonestly induces the person deceived to deliver any property, including online cyber frauds.",
        "description": "Whoever cheats and thereby dishonestly induces the person deceived to deliver any property, including online cyber frauds.",
        "punishment": "Imprisonment up to seven years, and fine",
        "offense_category": "cybercrime"
    },
    {
        "section_id": "319(2)",
        "section_number": "319(2)",
        "title": "Cheating by Personation Using Computer Resource",
        "text": "A person is said to cheat by personation if he cheats by pretending to be some other person, including online identity theft.",
        "description": "A person is said to cheat by personation if he cheats by pretending to be some other person, including online identity theft.",
        "punishment": "Imprisonment up to five years, or fine, or both",
        "offense_category": "cybercrime"
    },
    # 7. Sexual Offenses
    {
        "section_id": "64(1)",
        "section_number": "64(1)",
        "title": "Punishment for Rape",
        "text": "Whoever commits rape shall be punished with rigorous imprisonment for a term which shall not be less than ten years, but which may extend to life.",
        "description": "Whoever commits rape shall be punished with rigorous imprisonment for a term which shall not be less than ten years, but which may extend to life.",
        "punishment": "Rigorous imprisonment for not less than ten years, extending to life, and fine",
        "offense_category": "sexual offenses"
    },
    {
        "section_id": "74",
        "section_number": "74",
        "title": "Assault or Criminal Force to Woman with Intent to Outrage her Modesty",
        "text": "Whoever assaults or uses criminal force to any woman, intending to outrage or knowing it to be likely that he will thereby outrage her modesty.",
        "description": "Whoever assaults or uses criminal force to any woman, intending to outrage or knowing it to be likely that he will thereby outrage her modesty.",
        "punishment": "Imprisonment from one to five years, and fine",
        "offense_category": "sexual offenses"
    },
    # 8. Forgery
    {
        "section_id": "336(1)",
        "section_number": "336(1)",
        "title": "Forgery",
        "text": "Whoever makes any false document or false electronic record with intent to cause damage or injury to the public or any person.",
        "description": "Whoever makes any false document or false electronic record with intent to cause damage or injury to the public or any person.",
        "punishment": "Imprisonment up to two years, or fine, or both",
        "offense_category": "forgery"
    },
    {
        "section_id": "338",
        "section_number": "338",
        "title": "Forgery of Valuable Security, Will, etc.",
        "text": "Whoever forges a document which purports to be a valuable security or a will, or an authority to adopt a son.",
        "description": "Whoever forges a document which purports to be a valuable security or a will, or an authority to adopt a son.",
        "punishment": "Imprisonment up to ten years, and fine",
        "offense_category": "forgery"
    },
    # 9. Extortion
    {
        "section_id": "308(2)",
        "section_number": "308(2)",
        "title": "Extortion",
        "text": "Whoever commits extortion by putting any person in fear of injury and thereby inducing them to deliver up property.",
        "description": "Whoever commits extortion by putting any person in fear of injury and thereby inducing them to deliver up property.",
        "punishment": "Imprisonment up to seven years, or fine, or both",
        "offense_category": "extortion"
    },
    {
        "section_id": "308(5)",
        "section_number": "308(5)",
        "title": "Extortion by Threat of Accusation",
        "text": "Whoever commits extortion by putting any person in fear of an accusation of having committed an offense punishable with death or life imprisonment.",
        "description": "Whoever commits extortion by putting any person in fear of an accusation of having committed an offense punishable with death or life imprisonment.",
        "punishment": "Imprisonment up to ten years, and fine",
        "offense_category": "extortion"
    },
    # 10. Unlawful Assembly
    {
        "section_id": "189(2)",
        "section_number": "189(2)",
        "title": "Unlawful Assembly",
        "text": "Being a member of an unlawful assembly of five or more persons with a common object to commit an offense or disrupt public order.",
        "description": "Being a member of an unlawful assembly of five or more persons with a common object to commit an offense or disrupt public order.",
        "punishment": "Imprisonment up to six months, or fine, or both",
        "offense_category": "unlawful assembly"
    },
    {
        "section_id": "191(2)",
        "section_number": "191(2)",
        "title": "Rioting",
        "text": "Whoever is guilty of rioting by using force or violence while being a member of an unlawful assembly.",
        "description": "Whoever is guilty of rioting by using force or violence while being a member of an unlawful assembly.",
        "punishment": "Imprisonment up to two years, or fine, or both",
        "offense_category": "unlawful assembly"
    }
]

# Exactly 5 landmark Indian judgments
judgments = [
    {
        "citation": "AIR 1980 SC 898",
        "court": "Supreme Court of India",
        "year": 1980,
        "ratio_decidendi": "The death penalty should only be awarded in the rarest of rare cases.",
        "keywords": ["death penalty", "rarest of rare", "murder", "sentencing guidelines", "constitutional validity"]
    },
    {
        "citation": "AIR 1962 SC 605",
        "court": "Supreme Court of India",
        "year": 1962,
        "ratio_decidendi": "The plea of sudden and grave provocation is not available when there is sufficient cooling-off time between the provocation and the act of murder.",
        "keywords": ["sudden and grave provocation", "murder", "jury trial", "mens rea"]
    },
    {
        "citation": "AIR 2015 SC 1523",
        "court": "Supreme Court of India",
        "year": 2015,
        "ratio_decidendi": "Section 66A of the Information Technology Act, 2000 is unconstitutional as it violates the right to freedom of speech and expression.",
        "keywords": ["freedom of speech", "electronic communication", "cyber law", "fundamental rights"]
    },
    {
        "citation": "AIR 2017 SC 4161",
        "court": "Supreme Court of India",
        "year": 2017,
        "ratio_decidendi": "The right to privacy is protected as an intrinsic part of the right to life and personal liberty under Article 21.",
        "keywords": ["right to privacy", "article 21", "fundamental rights", "surveillance", "data protection"]
    },
    {
        "citation": "AIR 2018 SC 4321",
        "court": "Supreme Court of India",
        "year": 2018,
        "ratio_decidendi": "Section 377 of the Indian Penal Code is unconstitutional to the extent that it criminalizes consensual sexual acts between adults in private.",
        "keywords": ["decriminalization", "consensual sex", "homosexuality", "right to privacy", "article 21"]
    }
]

# INTERPRETS relationships from Judgments to BNS Sections
interprets_relationships = [
    {"judgment_citation": "AIR 1980 SC 898", "bns_section_id": "103(1)"},
    {"judgment_citation": "AIR 1962 SC 605", "bns_section_id": "103(1)"},
    {"judgment_citation": "AIR 2015 SC 1523", "bns_section_id": "318(4)"},
    {"judgment_citation": "AIR 2017 SC 4161", "bns_section_id": "319(2)"},
    {"judgment_citation": "AIR 2018 SC 4321", "bns_section_id": "74"}
]

# CROSS_REFERENCES relationships between BNS Sections (exactly 5 pairs)
cross_references_relationships = [
    {"from_id": "103(1)", "to_id": "103(2)"},
    {"from_id": "115(1)", "to_id": "117(1)"},
    {"from_id": "303(2)", "to_id": "305"},
    {"from_id": "309(4)", "to_id": "310(1)"},
    {"from_id": "318(4)", "to_id": "319(2)"}
]

def seed_database(session) -> None:
    logger.info("Seeding BNS_Section nodes...")
    for section in bns_sections:
        query = """
        MERGE (b:BNS_Section {section_id: $section_id})
        ON CREATE SET 
            b.section_number = $section_number,
            b.title = $title,
            b.text = $text,
            b.description = $description,
            b.punishment = $punishment,
            b.offense_category = $offense_category
        ON MATCH SET 
            b.section_number = $section_number,
            b.title = $title,
            b.text = $text,
            b.description = $description,
            b.punishment = $punishment,
            b.offense_category = $offense_category
        """
        session.run(query, section)
    logger.info(f"Successfully seeded {len(bns_sections)} BNS_Section nodes.")

    logger.info("Seeding Judgment nodes...")
    for judgment in judgments:
        query = """
        MERGE (j:Judgment {citation: $citation})
        ON CREATE SET 
            j.court = $court,
            j.year = $year,
            j.ratio_decidendi = $ratio_decidendi,
            j.keywords = $keywords
        ON MATCH SET 
            j.court = $court,
            j.year = $year,
            j.ratio_decidendi = $ratio_decidendi,
            j.keywords = $keywords
        """
        session.run(query, judgment)
    logger.info(f"Successfully seeded {len(judgments)} Judgment nodes.")

    logger.info("Creating INTERPRETS relationships...")
    for rel in interprets_relationships:
        query = """
        MATCH (j:Judgment {citation: $judgment_citation})
        MATCH (b:BNS_Section {section_id: $bns_section_id})
        MERGE (j)-[r:INTERPRETS]->(b)
        """
        session.run(query, rel)
    logger.info(f"Successfully created {len(interprets_relationships)} INTERPRETS relationships.")

    logger.info("Creating CROSS_REFERENCES relationships...")
    for rel in cross_references_relationships:
        query = """
        MATCH (b1:BNS_Section {section_id: $from_id})
        MATCH (b2:BNS_Section {section_id: $to_id})
        MERGE (b1)-[r:CROSS_REFERENCES]->(b2)
        """
        session.run(query, rel)
    logger.info(f"Successfully created {len(cross_references_relationships)} CROSS_REFERENCES relationships.")

def main() -> None:
    logger.info("Connecting to Neo4j database...")
    neo4j_client.connect()
    
    with neo4j_client.get_session() as session:
        seed_database(session)
        
        # Query total nodes and edges created for the final summary printing
        total_nodes = session.run("MATCH (n) WHERE n:BNS_Section OR n:Judgment RETURN count(n) as count").single()["count"]
        total_edges = session.run("MATCH ()-[r:INTERPRETS|CROSS_REFERENCES]->() RETURN count(r) as count").single()["count"]
        
        print("\n" + "="*50)
        print("SEEDING SUMMARY")
        print("="*50)
        print(f"Total nodes created/updated: {total_nodes}")
        print(f"Total edges created/updated: {total_edges}")
        print("="*50 + "\n")
        
    logger.info("Neo4j Database Seeding completed successfully.")

if __name__ == "__main__":
    main()
