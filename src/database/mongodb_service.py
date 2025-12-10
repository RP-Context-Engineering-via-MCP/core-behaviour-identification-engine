"""MongoDB database service for CBIE system"""
from typing import List, Optional, Dict, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
import logging

from src.config import settings
from src.models.schemas import (
    BehaviorModel, 
    PromptModel, 
    CoreBehaviorProfile,
    ClusterModel
)

logger = logging.getLogger(__name__)


class MongoDBService:
    """Service for MongoDB operations"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        
    def connect(self):
        """Establish MongoDB connection"""
        try:
            self.client = MongoClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_database]
            
            # Create indexes
            self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {settings.mongodb_database}")
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def _create_indexes(self):
        """Create necessary indexes for collections"""
        try:
            # Behaviors collection indexes (using observation_id now)
            self.db.behaviors.create_index("observation_id", unique=True)
            self.db.behaviors.create_index("user_id")
            self.db.behaviors.create_index("session_id")
            
            # Prompts collection indexes
            self.db.prompts.create_index("prompt_id", unique=True)
            self.db.prompts.create_index("user_id")
            self.db.prompts.create_index("timestamp")
            
            # Core behavior profiles indexes
            self.db.core_behavior_profiles.create_index("user_id", unique=True)
            self.db.core_behavior_profiles.create_index("generated_at")
            
            # Clusters collection indexes
            self.db.clusters.create_index("cluster_id", unique=True)
            self.db.clusters.create_index("user_id")
            
            logger.info("Database indexes created successfully")
        except PyMongoError as e:
            logger.warning(f"Error creating indexes: {e}")
    
    # Behavior CRUD operations
    
    def insert_behavior(self, behavior: BehaviorModel) -> bool:
        """Insert a behavior document"""
        try:
            self.db.behaviors.insert_one(behavior.model_dump())
            return True
        except PyMongoError as e:
            logger.error(f"Error inserting behavior: {e}")
            return False
    
    def insert_behaviors_bulk(self, behaviors: List[BehaviorModel]) -> bool:
        """Insert multiple behaviors"""
        try:
            docs = [b.model_dump() for b in behaviors]
            self.db.behaviors.insert_many(docs)
            return True
        except PyMongoError as e:
            logger.error(f"Error bulk inserting behaviors: {e}")
            return False
    
    def get_behavior(self, behavior_id: str) -> Optional[Dict]:
        """Get a behavior by ID"""
        try:
            return self.db.behaviors.find_one({"behavior_id": behavior_id})
        except PyMongoError as e:
            logger.error(f"Error fetching behavior: {e}")
            return None
    
    def get_behaviors_by_user(self, user_id: str) -> List[Dict]:
        """Get all behaviors for a user"""
        try:
            return list(self.db.behaviors.find({"user_id": user_id}))
        except PyMongoError as e:
            logger.error(f"Error fetching behaviors for user: {e}")
            return []
    
    def update_behavior(self, behavior_id: str, updates: Dict[str, Any]) -> bool:
        """Update a behavior document"""
        try:
            result = self.db.behaviors.update_one(
                {"behavior_id": behavior_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error updating behavior: {e}")
            return False
    
    def delete_behavior(self, behavior_id: str) -> bool:
        """Delete a behavior document"""
        try:
            result = self.db.behaviors.delete_one({"behavior_id": behavior_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error deleting behavior: {e}")
            return False
    
    # Prompt CRUD operations
    
    def insert_prompt(self, prompt: PromptModel) -> bool:
        """Insert a prompt document"""
        try:
            self.db.prompts.insert_one(prompt.model_dump())
            return True
        except PyMongoError as e:
            logger.error(f"Error inserting prompt: {e}")
            return False
    
    def insert_prompts_bulk(self, prompts: List[PromptModel]) -> bool:
        """Insert multiple prompts"""
        try:
            docs = [p.model_dump() for p in prompts]
            self.db.prompts.insert_many(docs)
            return True
        except PyMongoError as e:
            logger.error(f"Error bulk inserting prompts: {e}")
            return False
    
    def get_prompt(self, prompt_id: str) -> Optional[Dict]:
        """Get a prompt by ID"""
        try:
            return self.db.prompts.find_one({"prompt_id": prompt_id})
        except PyMongoError as e:
            logger.error(f"Error fetching prompt: {e}")
            return None
    
    def get_prompts_by_ids(self, prompt_ids: List[str]) -> List[Dict]:
        """Get multiple prompts by IDs"""
        try:
            return list(self.db.prompts.find({"prompt_id": {"$in": prompt_ids}}))
        except PyMongoError as e:
            logger.error(f"Error fetching prompts by IDs: {e}")
            return []
    
    def get_prompts_by_user(self, user_id: str) -> List[Dict]:
        """Get all prompts for a user"""
        try:
            return list(self.db.prompts.find({"user_id": user_id}).sort("timestamp", ASCENDING))
        except PyMongoError as e:
            logger.error(f"Error fetching prompts for user: {e}")
            return []
    
    # Core Behavior Profile CRUD operations
    
    def insert_profile(self, profile: CoreBehaviorProfile) -> bool:
        """Insert or update a core behavior profile"""
        try:
            self.db.core_behavior_profiles.replace_one(
                {"user_id": profile.user_id},
                profile.model_dump(),
                upsert=True
            )
            return True
        except PyMongoError as e:
            logger.error(f"Error inserting profile: {e}")
            return False
    
    def get_profile(self, user_id: str) -> Optional[Dict]:
        """Get a core behavior profile by user ID"""
        try:
            return self.db.core_behavior_profiles.find_one({"user_id": user_id})
        except PyMongoError as e:
            logger.error(f"Error fetching profile: {e}")
            return None
    
    def update_profile_archetype(self, user_id: str, archetype: str) -> bool:
        """Update the archetype field of a profile"""
        try:
            result = self.db.core_behavior_profiles.update_one(
                {"user_id": user_id},
                {"$set": {"archetype": archetype}}
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error updating archetype: {e}")
            return False
    
    # Cluster CRUD operations
    
    def insert_cluster(self, cluster: ClusterModel) -> bool:
        """Insert a cluster document"""
        try:
            self.db.clusters.insert_one(cluster.model_dump())
            return True
        except PyMongoError as e:
            logger.error(f"Error inserting cluster: {e}")
            return False
    
    def insert_clusters_bulk(self, clusters: List[ClusterModel]) -> bool:
        """Insert multiple clusters"""
        try:
            docs = [c.model_dump() for c in clusters]
            self.db.clusters.insert_many(docs)
            return True
        except PyMongoError as e:
            logger.error(f"Error bulk inserting clusters: {e}")
            return False
    
    def get_clusters_by_user(self, user_id: str) -> List[Dict]:
        """Get all clusters for a user"""
        try:
            return list(self.db.clusters.find({"user_id": user_id}))
        except PyMongoError as e:
            logger.error(f"Error fetching clusters for user: {e}")
            return []
    
    def delete_clusters_by_user(self, user_id: str) -> bool:
        """Delete all clusters for a user"""
        try:
            self.db.clusters.delete_many({"user_id": user_id})
            return True
        except PyMongoError as e:
            logger.error(f"Error deleting clusters: {e}")
            return False


# Global MongoDB service instance
mongodb_service = MongoDBService()
