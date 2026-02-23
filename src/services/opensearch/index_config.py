"""
MediGuard AI — OpenSearch index mapping for medical document chunks.

Includes a medical synonym analyzer and KNN vector field for hybrid search.
"""

MEDICAL_CHUNKS_MAPPING: dict = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 256,
        },
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "filter": {
                "medical_synonyms": {
                    "type": "synonym",
                    "synonyms": [
                        "diabetes mellitus, DM, diabetes",
                        "HbA1c, glycated hemoglobin, hemoglobin A1c, A1c",
                        "glucose, blood sugar, blood glucose",
                        "LDL, low density lipoprotein, bad cholesterol",
                        "HDL, high density lipoprotein, good cholesterol",
                        "WBC, white blood cells, leukocytes",
                        "RBC, red blood cells, erythrocytes",
                        "MCV, mean corpuscular volume",
                        "BP, blood pressure",
                        "CRP, C-reactive protein",
                        "ALT, alanine aminotransferase, SGPT",
                        "AST, aspartate aminotransferase, SGOT",
                        "TSH, thyroid stimulating hormone",
                        "BMI, body mass index",
                        "anemia, anaemia",
                        "thrombocytopenia, low platelets",
                        "thalassemia, thalassaemia",
                    ],
                }
            },
            "analyzer": {
                "medical_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "medical_synonyms",
                        "stop",
                        "snowball",
                    ],
                }
            },
        },
    },
    "mappings": {
        "properties": {
            # ── Text fields ────────────────────────────────────────
            "chunk_text": {
                "type": "text",
                "analyzer": "medical_analyzer",
            },
            "title": {"type": "text", "analyzer": "medical_analyzer"},
            "section_title": {"type": "text"},
            "abstract": {"type": "text", "analyzer": "medical_analyzer"},
            # ── Keyword / filterable ───────────────────────────────
            "document_id": {"type": "keyword"},
            "document_type": {"type": "keyword"},  # guideline, research, reference
            "condition_tags": {"type": "keyword"},  # diabetes, anemia, …
            "biomarkers_mentioned": {"type": "keyword"},  # Glucose, HbA1c, …
            "source_file": {"type": "keyword"},
            "page_number": {"type": "integer"},
            "chunk_index": {"type": "integer"},
            "publication_year": {"type": "integer"},
            # ── Vector (KNN) ───────────────────────────────────────
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {"ef_construction": 256, "m": 48},
                },
            },
            # ── Timestamps ─────────────────────────────────────────
            "indexed_at": {"type": "date"},
        }
    },
}
