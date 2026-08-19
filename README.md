Drone Forensic Framework

**A Configurable Forensic Framework Using OCR-Based Adaptive Grid Slicing Architecture for Extracting Encrypted Flight Evidence from Potensic Atom 2 Drone**

---

Author

DODZI GBORDZI
MSc. Cyber Security and Digital Forensics  
Kwame Nkrumah University of Science and Technology (KNUST)

Overview

This framework extracts flight evidence from Potensic Atom 2 drones by processing PTD1 remote controller screenshots using Optical Character Recognition (OCR). It bypasses encrypted FC.fc2 log files by treating the screen as an evidentiary source.

Key Features

Adaptive Grid Slicing Architecture (AGSA) — 5-stage OCR pipeline for flight data extraction
SHA-256 Integrity Verification — Cryptographic hashing for all evidence files
Per-row Hashing** — Individual SHA-256 hashes for each flight record
Dual-Track Cross-Validation — Compares OCR data against SD card EXIF metadata
JSON-Driven Configuration — Add new drone support without code changes
GPS EXIF Extraction — Recovers geospatial evidence from JPEG files
CSV Export with Row Hashing — Forensically sound data export

Installation

Step 1: Clone or Download

```bash
git clone https://github.com/dodziofficial/drone-forensic-framework.git
cd drone-forensic-framework