#!/usr/bin/env python
"""
test_patterns.py
Standalone test script to execute pattern detection scans and display findings
in the requested formatted output.
"""

import os
import sys

# Set up paths for relative/direct execution imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # backend/
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

from backend.app.database.neo4j_client import neo4j_client
from backend.app.services.pattern_queries import run_all_pattern_scans

def main() -> None:
    # Connect to Neo4j
    neo4j_client.connect()
    
    try:
        # Run pattern scans
        scan_results = run_all_pattern_scans()
        
        recidivism = scan_results.get("recidivism", [])
        locations = scan_results.get("location_clusters", [])
        evidence = scan_results.get("shared_evidence", [])
        mo_patterns = scan_results.get("mo_patterns", [])
        scanned_at = scan_results.get("scanned_at", "")
        
        print("\n=== PATTERN SCAN RESULTS ===\n")
        
        # 1. Recidivism
        print(f"[RECIDIVISM] Found {len(recidivism)} repeat offenders:")
        for r in recidivism:
            print(f"  - Aliases: {r.get('aliases', [])} | Cases: {r.get('case_count', 0)} | Case IDs: {r.get('case_ids', [])}")
            
        print()
        
        # 2. Location Clusters
        print(f"[LOCATION CLUSTERS] Found {len(locations)} hotspots:")
        for l in locations:
            print(f"  - Location: {l.get('location', '')} | Cases in 90 days: {l.get('case_count', 0)}")
            
        print()
        
        # 3. Shared Evidence
        print(f"[SHARED EVIDENCE] Found {len(evidence)} shared evidence signals:")
        for e in evidence:
            print(f"  - Description: {e.get('evidence_description', '')} | Linked Cases: {e.get('case_count', 0)}")
            
        print()
        
        # 4. MO Patterns
        print(f"[MO PATTERNS] Found {len(mo_patterns)} MO patterns:")
        for m in mo_patterns:
            print(f"  - MO: {m.get('modus_operandi', '')} | Category: {m.get('category', '')} | Cases: {m.get('case_count', 0)}")
            
        print()
        print(f"Scan completed at: {scanned_at}")
        
    except Exception as e:
        print(f"Error executing pattern scans test: {e}")
    finally:
        neo4j_client.close()

if __name__ == "__main__":
    main()
