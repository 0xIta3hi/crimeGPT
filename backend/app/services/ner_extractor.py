"""
ner_extractor.py
A module that uses spaCy (en_core_web_lg) to extract persons, locations,
offense keywords, and raw entities from narrative texts.
"""

import spacy
from typing import Any

# Load the large English NLP pipeline
nlp = spacy.load("en_core_web_lg")

# Hardcoded keyword list as specified by requirements
KEYWORDS = [
    "murder", "killed", "assault", "theft", "stolen", 
    "robbery", "kidnap", "rape", "extortion", "hack", 
    "fraud", "forge", "riot"
]

# Mapping token lemmas to the exact hardcoded keywords to handle inflections (e.g. stole -> stolen, killing -> killed)
LEMMA_TO_KEYWORD = {
    "murder": "murder",
    "kill": "killed",
    "killed": "killed",
    "assault": "assault",
    "theft": "theft",
    "stolen": "stolen",
    "steal": "stolen",
    "robbery": "robbery",
    "kidnap": "kidnap",
    "rape": "rape",
    "extortion": "extortion",
    "hack": "hack",
    "fraud": "fraud",
    "forge": "forge",
    "riot": "riot"
}

def extract_entities(narrative: str) -> dict[str, Any]:
    """
    Analyzes the input narrative using spaCy and extracts named entities and criminal keywords.
    
    Args:
        narrative (str): The crime narrative or FIR text.
        
    Returns:
        dict: A structured dictionary containing:
            - persons: list of person names (PERSON label)
            - locations: list of location names (GPE + LOC labels)
            - offense_keywords: list of matched keywords signalling criminal activity
            - raw_entities: list of all (text, label) tuples found by spaCy
    """
    doc = nlp(narrative)
    
    persons = []
    locations = []
    raw_entities = []
    
    # Extract spaCy named entities
    for ent in doc.ents:
        raw_entities.append((ent.text, ent.label_))
        if ent.label_ == "PERSON":
            persons.append(ent.text)
        elif ent.label_ in ("GPE", "LOC"):
            locations.append(ent.text)
            
    # Deduplicate keeping order
    persons = list(dict.fromkeys(persons))
    locations = list(dict.fromkeys(locations))
    
    # Extract offense keywords from verbs and nouns (with fallback/inflection matching)
    offense_keywords = []
    for token in doc:
        token_text_lower = token.text.lower()
        token_lemma_lower = token.lemma_.lower()
        
        # Check POS to focus on verbs and nouns, while matching text/lemma against our lists
        if token.pos_ in ("NOUN", "VERB", "PROPN", "ADJ"):
            matched_kw = None
            if token_text_lower in KEYWORDS:
                matched_kw = token_text_lower
            elif token_lemma_lower in LEMMA_TO_KEYWORD:
                matched_kw = LEMMA_TO_KEYWORD[token_lemma_lower]
                
            if matched_kw:
                offense_keywords.append(matched_kw)
                
    offense_keywords = list(dict.fromkeys(offense_keywords))
    
    return {
        "persons": persons,
        "locations": locations,
        "offense_keywords": offense_keywords,
        "raw_entities": raw_entities
    }
