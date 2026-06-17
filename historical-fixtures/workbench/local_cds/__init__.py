"""Local CDS pipeline: decon (OpenMed NER) + search (pluggable) + synth (MedGemma).

Goal #1: Local model + local decon + websearch + strong prompt → fast + high quality.

Pipeline:
  query (with PHI)
    → OpenMed PHI-NER masks identifiers
    → search backend (Exa / Brave / Tavily) returns medical-domain snippets
    → MedGemma synthesizes with ws5-style prompt + citations
"""
