"""
Rebuild LanceDB vector index from GraphRAG parquet files.

This script fixes the ID mismatch between entities.parquet/text_units.parquet/
community_reports.parquet and the LanceDB vector store. When the parquet files
and LanceDB were built from different indexing runs, their IDs don't match,
causing GraphRAG local_search to return empty context for every query.

The fix:
1. Read entity descriptions, text unit text, and community report content
   from parquet files
2. Generate embeddings using the same model (text-embedding-3-large)
3. Rebuild LanceDB tables with the correct IDs matching the parquet files

This is a general-purpose repair that works for any GraphRAG index,
regardless of language or domain.
"""
import os
import sys
import time
import shutil
import logging
import asyncio
from pathlib import Path

import pandas as pd
import numpy as np
import lancedb

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────
GRAPHRAG_ROOT = Path("./graphrag-index")
OUTPUT_DIR = GRAPHRAG_ROOT / "output"
LANCEDB_DIR = OUTPUT_DIR / "lancedb"

# Azure OpenAI embedding config (from settings.yaml)
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072
API_BASE = "https://ai-ragworkv2-vtgal6fjx3fcc.cognitiveservices.azure.com"
API_VERSION = "2024-02-15-preview"
API_KEY = "87dfca521e8c4009afbb64466c735076"

BATCH_SIZE = 100  # Azure OpenAI embedding batch limit


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings in batches using Azure OpenAI."""
    from openai import AzureOpenAI
    
    client = AzureOpenAI(
        api_key=API_KEY,
        api_version=API_VERSION,
        azure_endpoint=API_BASE,
    )
    
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        # Replace empty strings with a space (API rejects empty inputs)
        batch = [t if t.strip() else " " for t in batch]
        
        logger.info(f"  Embedding batch {i//BATCH_SIZE + 1}/{(len(texts)-1)//BATCH_SIZE + 1} ({len(batch)} texts)")
        resp = client.embeddings.create(input=batch, model=EMBEDDING_MODEL)
        batch_embs = [item.embedding for item in resp.data]
        all_embeddings.extend(batch_embs)
        
        # Respect rate limits
        if i + BATCH_SIZE < len(texts):
            time.sleep(0.5)
    
    return all_embeddings


def rebuild_entity_descriptions(db: lancedb.DBConnection, entities_df: pd.DataFrame):
    """Rebuild entity_description table from entities.parquet."""
    logger.info(f"=== Rebuilding entity_description ({len(entities_df)} entities) ===")
    
    # Prepare texts: use description, fall back to title
    texts = []
    ids = []
    for _, row in entities_df.iterrows():
        desc = str(row.get('description', '') or '')
        title = str(row.get('title', '') or '')
        text = desc if desc.strip() else title
        texts.append(text)
        ids.append(row['id'])
    
    logger.info(f"  Generating embeddings for {len(texts)} entity descriptions...")
    embeddings = get_embeddings(texts)
    
    # Build DataFrame for LanceDB
    lance_data = pd.DataFrame({
        'id': ids,
        'vector': [np.array(e, dtype=np.float32) for e in embeddings],
    })
    
    # Drop existing table and create new one
    table_name = "entity_description"
    if table_name in db.table_names():
        db.drop_table(table_name)
        logger.info(f"  Dropped old {table_name} table")
    
    db.create_table(table_name, data=lance_data)
    logger.info(f"  Created {table_name} with {len(lance_data)} rows")


def rebuild_text_units(db: lancedb.DBConnection, text_units_df: pd.DataFrame):
    """Rebuild text_unit_text table from text_units.parquet."""
    logger.info(f"=== Rebuilding text_unit_text ({len(text_units_df)} text units) ===")
    
    texts = []
    ids = []
    for _, row in text_units_df.iterrows():
        text = str(row.get('text', '') or '')
        texts.append(text[:8000])  # Truncate very long text units
        ids.append(row['id'])
    
    logger.info(f"  Generating embeddings for {len(texts)} text units...")
    embeddings = get_embeddings(texts)
    
    lance_data = pd.DataFrame({
        'id': ids,
        'vector': [np.array(e, dtype=np.float32) for e in embeddings],
    })
    
    table_name = "text_unit_text"
    if table_name in db.table_names():
        db.drop_table(table_name)
        logger.info(f"  Dropped old {table_name} table")
    
    db.create_table(table_name, data=lance_data)
    logger.info(f"  Created {table_name} with {len(lance_data)} rows")


def rebuild_community_reports(db: lancedb.DBConnection, reports_df: pd.DataFrame):
    """Rebuild community_full_content table from community_reports.parquet."""
    logger.info(f"=== Rebuilding community_full_content ({len(reports_df)} reports) ===")
    
    texts = []
    ids = []
    for _, row in reports_df.iterrows():
        content = str(row.get('full_content', '') or row.get('summary', '') or '')
        texts.append(content[:8000])
        ids.append(row['id'])
    
    logger.info(f"  Generating embeddings for {len(texts)} community reports...")
    embeddings = get_embeddings(texts)
    
    lance_data = pd.DataFrame({
        'id': ids,
        'vector': [np.array(e, dtype=np.float32) for e in embeddings],
    })
    
    table_name = "community_full_content"
    if table_name in db.table_names():
        db.drop_table(table_name)
        logger.info(f"  Dropped old {table_name} table")
    
    db.create_table(table_name, data=lance_data)
    logger.info(f"  Created {table_name} with {len(lance_data)} rows")


def main():
    t0 = time.time()
    
    # Load parquet files
    logger.info("Loading parquet files...")
    entities_df = pd.read_parquet(OUTPUT_DIR / "entities.parquet")
    text_units_df = pd.read_parquet(OUTPUT_DIR / "text_units.parquet")
    reports_df = pd.read_parquet(OUTPUT_DIR / "community_reports.parquet")
    
    logger.info(f"  Entities: {len(entities_df)}")
    logger.info(f"  Text units: {len(text_units_df)}")
    logger.info(f"  Community reports: {len(reports_df)}")
    
    # Backup existing LanceDB
    backup_dir = LANCEDB_DIR.parent / "lancedb_backup"
    if LANCEDB_DIR.exists():
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(LANCEDB_DIR, backup_dir)
        logger.info(f"  Backed up existing LanceDB to {backup_dir}")
    
    # Connect to LanceDB
    db = lancedb.connect(str(LANCEDB_DIR))
    logger.info(f"  Connected to LanceDB: {LANCEDB_DIR}")
    logger.info(f"  Existing tables: {db.table_names()}")
    
    # Rebuild all three tables
    rebuild_entity_descriptions(db, entities_df)
    rebuild_text_units(db, text_units_df)
    rebuild_community_reports(db, reports_df)
    
    # Verify
    logger.info("\n=== Verification ===")
    db2 = lancedb.connect(str(LANCEDB_DIR))
    for table_name in db2.table_names():
        tbl = db2.open_table(table_name)
        count = tbl.count_rows()
        logger.info(f"  {table_name}: {count} rows")
    
    # Verify ID overlap
    tbl = db2.open_table("entity_description")
    lance_ids = set(tbl.to_pandas()['id'].tolist())
    parquet_ids = set(entities_df['id'].tolist())
    overlap = len(lance_ids & parquet_ids)
    logger.info(f"\n  Entity ID overlap: {overlap}/{len(parquet_ids)} ({100*overlap/len(parquet_ids):.0f}%)")
    
    elapsed = time.time() - t0
    logger.info(f"\n✅ LanceDB rebuild complete in {elapsed:.1f}s")
    logger.info(f"  Backup at: {backup_dir}")


if __name__ == "__main__":
    main()
