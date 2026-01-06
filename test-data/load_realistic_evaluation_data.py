"""
Script to load realistic evaluation test data into databases
- Loads 6 diverse user personas from test-data/realistic_evaluation_set/
- Prompts saved to MongoDB
- Behaviors vectorized and saved to Qdrant
"""
import json
import logging
import sys
import os
import time
from pathlib import Path
from typing import List, Dict

# Add project root to path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Change working directory to project root to find .env file
os.chdir(project_root)

from src.database.mongodb_service import MongoDBService
from src.database.qdrant_service import QdrantService
from src.services.embedding_service import EmbeddingService
from src.models.schemas import BehaviorObservation, PromptModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_json_file(filepath: str) -> List[Dict]:
    """Load data from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} records from {filepath}")
        return data
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return []


def save_prompts_to_mongodb(prompts_data: List[Dict], mongo_service: MongoDBService) -> bool:
    """Save prompts to MongoDB with duplicate handling"""
    try:
        # Convert to PromptModel objects
        prompts = [PromptModel(**prompt_data) for prompt_data in prompts_data]
        
        logger.info(f"Attempting to save {len(prompts)} prompts to MongoDB...")
        
        # Try bulk insert first
        success = mongo_service.insert_prompts_bulk(prompts)
        
        if success:
            logger.info(f"✓ Successfully saved {len(prompts)} prompts to MongoDB")
            return True
        else:
            # Bulk insert failed, try individual inserts
            logger.warning(f"Bulk insert failed, trying individual inserts...")
            
            inserted_count = 0
            duplicate_count = 0
            error_count = 0
            
            for prompt in prompts:
                try:
                    result = mongo_service.insert_prompts_bulk([prompt])
                    if result:
                        inserted_count += 1
                except Exception as single_error:
                    error_msg = str(single_error)
                    if 'E11000' in error_msg or 'duplicate key' in error_msg:
                        duplicate_count += 1
                    else:
                        error_count += 1
                        if error_count <= 3:  # Only log first 3 errors
                            logger.error(f"Error inserting prompt {prompt.prompt_id}: {single_error}")
            
            logger.info(f"✓ Inserted {inserted_count} prompts, skipped {duplicate_count} duplicates, {error_count} errors")
            return inserted_count > 0
        
    except Exception as e:
        logger.error(f"Error saving prompts: {e}")
        return False


def save_behaviors_to_qdrant(
    behaviors_data: List[Dict], 
    qdrant_service: QdrantService, 
    embedding_service: EmbeddingService
) -> bool:
    """Vectorize behaviors and save complete data to Qdrant with batch processing"""
    try:
        # Extract behavior texts for vectorization
        behavior_texts = [b['behavior_text'] for b in behaviors_data]
        
        logger.info(f"Generating embeddings for {len(behavior_texts)} behaviors...")
        
        # Generate embeddings
        embeddings = embedding_service.generate_embeddings_batch(behavior_texts)
        
        if not embeddings:
            logger.error("Failed to generate embeddings")
            return False
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Prepare behaviors for Qdrant - map confidence → extraction_confidence, add missing fields
        qdrant_behaviors = []
        for b in behaviors_data:
            qdrant_behavior = b.copy()
            # Map confidence field to extraction_confidence (Qdrant expects this name)
            qdrant_behavior['extraction_confidence'] = b.get('confidence', b.get('credibility', 0.80))
            # Add decay_rate if missing (required by schema)
            if 'decay_rate' not in qdrant_behavior:
                qdrant_behavior['decay_rate'] = 0.01
            # Add timestamp if missing (use last_seen)
            if 'timestamp' not in qdrant_behavior:
                qdrant_behavior['timestamp'] = b.get('last_seen', int(time.time()))
            qdrant_behaviors.append(qdrant_behavior)
        
        # Batch processing to avoid payload size limits (33MB max)
        # Process in batches of 100 behaviors to stay well under the limit
        batch_size = 100
        total_batches = (len(embeddings) + batch_size - 1) // batch_size
        
        logger.info(f"Processing {len(embeddings)} behaviors in {total_batches} batches...")
        
        for i in range(0, len(embeddings), batch_size):
            batch_num = (i // batch_size) + 1
            end_idx = min(i + batch_size, len(embeddings))
            
            batch_embeddings = embeddings[i:end_idx]
            batch_behaviors = qdrant_behaviors[i:end_idx]
            
            logger.info(f"  Batch {batch_num}/{total_batches}: Inserting {len(batch_embeddings)} behaviors...")
            
            success = qdrant_service.insert_behaviors_with_embeddings(
                embeddings=batch_embeddings,
                behaviors=batch_behaviors
            )
            
            if not success:
                logger.error(f"✗ Failed to save batch {batch_num}/{total_batches}")
                return False
            
            logger.info(f"  ✓ Batch {batch_num}/{total_batches} saved successfully")
        
        logger.info(f"✓ Successfully saved all {len(embeddings)} behaviors to Qdrant")
        return True
        
    except Exception as e:
        logger.error(f"Error saving behaviors: {e}")
        return False


def save_behaviors_to_mongodb(behaviors_data: List[Dict], mongo_service: MongoDBService) -> bool:
    """Save behaviors metadata to MongoDB with duplicate handling"""
    try:
        # Convert to BehaviorObservation format
        behavior_observations = []
        for b in behaviors_data:
            obs = BehaviorObservation(
                observation_id=b.get('behavior_id'),
                user_id=b.get('user_id', 'unknown'),
                behavior_text=b.get('behavior_text'),
                timestamp=b.get('last_seen', int(time.time())),
                prompt_id=b.get('prompt_history_ids', ['unknown'])[0] if b.get('prompt_history_ids') else 'unknown',
                session_id=b.get('session_id', 'unknown'),
                credibility=b.get('credibility', 0.75),
                clarity_score=b.get('clarity_score', b.get('credibility', 0.75)),
                extraction_confidence=b.get('confidence', b.get('credibility', 0.80)),
                decay_rate=0.01
            )
            behavior_observations.append(obs)
        
        logger.info(f"Attempting to save {len(behavior_observations)} behaviors to MongoDB...")
        
        # Try bulk insert first
        success = mongo_service.insert_behaviors_bulk(behavior_observations)
        
        if success:
            logger.info(f"✓ Successfully saved {len(behavior_observations)} behaviors to MongoDB")
            return True
        else:
            # Bulk insert failed, try individual inserts
            logger.warning(f"Bulk insert failed, trying individual inserts...")
            
            inserted_count = 0
            duplicate_count = 0
            error_count = 0
            
            for obs in behavior_observations:
                try:
                    result = mongo_service.insert_behaviors_bulk([obs])
                    if result:
                        inserted_count += 1
                except Exception as single_error:
                    error_msg = str(single_error)
                    if 'E11000' in error_msg or 'duplicate key' in error_msg:
                        duplicate_count += 1
                    else:
                        error_count += 1
                        if error_count <= 3:  # Only log first 3 errors
                            logger.error(f"Error inserting behavior {obs.observation_id}: {single_error}")
            
            logger.info(f"✓ Inserted {inserted_count} behaviors, skipped {duplicate_count} duplicates, {error_count} errors")
            return inserted_count > 0
        
    except Exception as e:
        logger.error(f"Error saving behaviors to MongoDB: {e}")
        return False


def main():
    """Main execution function"""
    # Define directory path for realistic evaluation data
    base_dir = Path(__file__).parent / "realistic_evaluation_set"
    
    # Check if directory exists
    if not base_dir.exists():
        logger.error(f"Directory not found: {base_dir}")
        logger.error("Run realistic_data_generator.py first to create test data")
        return False
    
    # Load metadata
    metadata_file = base_dir / "test_dataset_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        logger.info("\n" + "="*80)
        logger.info("REALISTIC EVALUATION DATA LOADER")
        logger.info("="*80)
        logger.info(f"Dataset: {metadata.get('purpose', 'Unknown')}")
        logger.info(f"Generated: {metadata.get('generation_date', 'Unknown')}")
        logger.info(f"Users: {metadata.get('total_users', 0)}")
        logger.info("")
        for user in metadata.get('users', []):
            logger.info(f"  • {user['name']} ({user['user_id']}): {user['description']}")
    
    # Find all prompts and behaviors files
    prompts_files = sorted(base_dir.glob("prompts_user_*.json"))
    behaviors_files = sorted(base_dir.glob("behaviors_user_*.json"))
    
    if not prompts_files:
        logger.error(f"No prompts files found in {base_dir}")
        return False
    
    if not behaviors_files:
        logger.error(f"No behaviors files found in {base_dir}")
        return False
    
    logger.info(f"\nFound {len(prompts_files)} prompt files and {len(behaviors_files)} behavior files")
    
    # Load data from all JSON files
    logger.info("\n" + "="*80)
    logger.info("LOADING DATA FROM FILES")
    logger.info("="*80)
    
    all_prompts_data = []
    all_behaviors_data = []
    
    for prompts_file in prompts_files:
        logger.info(f"Loading {prompts_file.name}...")
        prompts_data = load_json_file(str(prompts_file))
        if prompts_data:
            user_id = prompts_file.stem.replace('prompts_', '')
            for prompt in prompts_data:
                if 'user_id' not in prompt or not prompt['user_id']:
                    prompt['user_id'] = user_id
            all_prompts_data.extend(prompts_data)
    
    for behaviors_file in behaviors_files:
        logger.info(f"Loading {behaviors_file.name}...")
        behaviors_data = load_json_file(str(behaviors_file))
        if behaviors_data:
            user_id = behaviors_file.stem.replace('behaviors_', '')
            for behavior in behaviors_data:
                behavior['user_id'] = user_id
            all_behaviors_data.extend(behaviors_data)
    
    if not all_prompts_data or not all_behaviors_data:
        logger.error("Failed to load data from files")
        return False
    
    logger.info(f"\n✓ Total loaded: {len(all_prompts_data)} prompts, {len(all_behaviors_data)} behaviors")
    
    # Initialize services
    logger.info("\n" + "="*80)
    logger.info("INITIALIZING DATABASE SERVICES")
    logger.info("="*80)
    
    mongo_service = MongoDBService()
    qdrant_service = QdrantService()
    embedding_service = EmbeddingService()
    
    try:
        # Connect to services
        logger.info("Connecting to MongoDB...")
        mongo_service.connect()
        logger.info("✓ Connected to MongoDB")
        
        logger.info("Connecting to Qdrant...")
        qdrant_service.connect()
        logger.info("✓ Connected to Qdrant")
        
        logger.info("Connecting to Azure OpenAI...")
        embedding_service.connect()
        logger.info("✓ Connected to Azure OpenAI")
        
        # Save prompts to MongoDB
        logger.info("\n" + "="*80)
        logger.info("SAVING PROMPTS TO MONGODB")
        logger.info("="*80)
        prompts_success = save_prompts_to_mongodb(all_prompts_data, mongo_service)
        
        # Save behaviors to Qdrant (with vectorization)
        logger.info("\n" + "="*80)
        logger.info("VECTORIZING AND SAVING BEHAVIORS TO QDRANT")
        logger.info("="*80)
        behaviors_qdrant_success = save_behaviors_to_qdrant(
            all_behaviors_data, 
            qdrant_service, 
            embedding_service
        )
        
        # Save behaviors to MongoDB
        logger.info("\n" + "="*80)
        logger.info("SAVING BEHAVIORS TO MONGODB")
        logger.info("="*80)
        behaviors_mongo_success = save_behaviors_to_mongodb(all_behaviors_data, mongo_service)
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("LOADING SUMMARY")
        logger.info("="*80)
        logger.info(f"Prompts → MongoDB:   {'✓ Success' if prompts_success else '✗ Failed'} ({len(all_prompts_data)} records)")
        logger.info(f"Behaviors → Qdrant:  {'✓ Success' if behaviors_qdrant_success else '✗ Failed'} ({len(all_behaviors_data)} records)")
        logger.info(f"Behaviors → MongoDB: {'✓ Success' if behaviors_mongo_success else '✗ Failed'} ({len(all_behaviors_data)} records)")
        
        # Per-user breakdown
        logger.info("\nPer-user breakdown:")
        user_ids = set(p['user_id'] for p in all_prompts_data)
        for user_id in sorted(user_ids):
            user_prompts = [p for p in all_prompts_data if p['user_id'] == user_id]
            user_behaviors = [b for b in all_behaviors_data if b.get('user_id') == user_id]
            logger.info(f"  {user_id}: {len(user_prompts)} prompts, {len(user_behaviors)} behaviors")
        
        all_success = prompts_success and behaviors_qdrant_success and behaviors_mongo_success
        
        if all_success:
            logger.info("\n" + "="*80)
            logger.info("✓ ALL DATA LOADED SUCCESSFULLY!")
            logger.info("="*80)
            logger.info("\nNext steps:")
            logger.info("  1. Run frequency baseline: python src/evaluation/run_comparison.py")
            logger.info("  2. Or test via API: POST /api/v1/analyze-behaviors-from-storage/<user_id>")
            return True
        else:
            logger.warning("\n" + "="*80)
            logger.warning("⚠ SOME OPERATIONS FAILED")
            logger.warning("="*80)
            logger.warning("Check logs above for details")
            return False
        
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        return False
    
    finally:
        # Disconnect services
        logger.info("\nDisconnecting from databases...")
        mongo_service.disconnect()
        qdrant_service.disconnect()
        logger.info("✓ Disconnected")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
