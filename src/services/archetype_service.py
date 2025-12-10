"""
Archetype Service for CBIE System
Generates behavioral archetype labels using Azure OpenAI LLM
"""
from typing import List, Optional
import logging
from openai import AzureOpenAI

from src.config import settings

logger = logging.getLogger(__name__)


class ArchetypeService:
    """Service for generating behavioral archetypes using LLM"""
    
    def __init__(self):
        self.client: Optional[AzureOpenAI] = None
        # Using a GPT model for completion - adjust deployment name as needed
        self.model = "gpt-4.1-mini"  # Or your Azure deployment name
        
    def connect(self):
        """Initialize Azure OpenAI client"""
        try:
            self.client = AzureOpenAI(
                api_key=settings.openai_api_key,
                api_version=settings.openai_api_version,
                azure_endpoint=settings.openai_api_base
            )
            logger.info(f"Connected to Azure OpenAI for archetype generation")
        except Exception as e:
            logger.error(f"Failed to connect to Azure OpenAI: {e}")
            raise
    
    def generate_archetype(
        self,
        canonical_behaviors: List[str],
        user_id: Optional[str] = None
    ) -> str:
        """
        Generate behavioral archetype label from canonical behaviors
        
        Args:
            canonical_behaviors: List of behavior text strings
            user_id: Optional user ID for logging
            
        Returns:
            str: Archetype label (e.g., "Visual Learner")
        """
        try:
            if not canonical_behaviors:
                logger.warning("No behaviors provided for archetype generation")
                return "Unknown"
            
            # Create prompt
            prompt = self._create_archetype_prompt(canonical_behaviors)
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in behavioral psychology and user profiling. "
                                   "Your task is to analyze user behaviors and assign a concise, "
                                   "descriptive archetype label."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            archetype = response.choices[0].message.content.strip()
            
            # Clean up the response (remove quotes, extra punctuation)
            archetype = archetype.strip('"\'.,')
            
            logger.info(
                f"Generated archetype for user {user_id}: '{archetype}' "
                f"from {len(canonical_behaviors)} behaviors"
            )
            
            return archetype
            
        except Exception as e:
            logger.error(f"Error generating archetype: {e}")
            return "Unknown"
    
    def _create_archetype_prompt(self, behaviors: List[str]) -> str:
        """
        Create prompt for LLM archetype generation
        
        Args:
            behaviors: List of behavior text strings
            
        Returns:
            str: Formatted prompt
        """
        behaviors_text = "\n".join([f"- {behavior}" for behavior in behaviors])
        
        prompt = f"""Given the following user behaviors:

{behaviors_text}

Classify the user into a single, concise behavioral archetype. 
The archetype should be a descriptive label (2-4 words) that captures the essence of these behaviors.

Examples of good archetypes: "Visual Learner", "Detail-Oriented Analyst", "Quick Reference Seeker", "Hands-On Experimenter"

Return ONLY the archetype label, nothing else."""
        
        return prompt
    
    def generate_archetype_with_context(
        self,
        canonical_behaviors: List[str],
        user_statistics: dict,
        user_id: Optional[str] = None
    ) -> str:
        """
        ⚠️ POTENTIALLY UNUSED - Check if called in cluster-centric pipeline ⚠️
        
        Generate archetype with additional context about user statistics
        
        STATUS: This enhanced version may not be used. The cluster pipeline might only use
        generate_archetype() without the statistics context.
        
        Args:
            canonical_behaviors: List of behavior text strings
            user_statistics: Dict with statistics (total_behaviors, days_active, etc.)
            user_id: Optional user ID for logging
            
        Returns:
            str: Archetype label
        """
        try:
            if not canonical_behaviors:
                return "Unknown"
            
            # Enhanced prompt with statistics
            behaviors_text = "\n".join([f"- {behavior}" for behavior in canonical_behaviors])
            
            stats_text = ""
            if user_statistics:
                stats_text = f"\n\nUser activity context:\n"
                if "total_behaviors_analyzed" in user_statistics:
                    stats_text += f"- Total behaviors: {user_statistics['total_behaviors_analyzed']}\n"
                if "analysis_time_span_days" in user_statistics:
                    stats_text += f"- Active for: {user_statistics['analysis_time_span_days']:.0f} days\n"
                if "total_prompts_analyzed" in user_statistics:
                    stats_text += f"- Total interactions: {user_statistics['total_prompts_analyzed']}\n"
            
            prompt = f"""Given the following user behaviors:

{behaviors_text}
{stats_text}

Classify the user into a single, concise behavioral archetype that captures their learning or interaction style.

Return ONLY the archetype label (2-4 words), nothing else."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in behavioral psychology and user profiling."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            archetype = response.choices[0].message.content.strip().strip('"\'.,')
            
            logger.info(f"Generated contextual archetype for user {user_id}: '{archetype}'")
            
            return archetype
            
        except Exception as e:
            logger.error(f"Error generating contextual archetype: {e}")
            return "Unknown"
    
    def generate_concise_label(self, behavior_texts: List[str]) -> str:
        """
        Generate a single canonical label from multiple behavior text observations.
        Sends ONLY the behavior texts (minimal tokens) to get a concise output.
        
        Args:
            behavior_texts: List of behavior text strings from cluster
            
        Returns:
            str: Concise canonical label (max 8 words)
        """
        if not behavior_texts:
            return "Unknown Behavior"
        
        # Single behavior: just return it
        if len(behavior_texts) == 1:
            return behavior_texts[0]
        
        # Deduplicate and limit to top 10 to save tokens
        unique_texts = list(set(behavior_texts))[:10]
        
        # Create minimal prompt (token-efficient)
        variations_text = "\n".join([f"- {t}" for t in unique_texts])
        
        prompt = (
            f"These are different observations of the same user behavior pattern:\n\n"
            f"{variations_text}\n\n"
            f"Create ONE concise label (max 6 words) that best represents this pattern. "
            f"Be specific and descriptive.\n\nLabel:"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise behavioral analyst. Generate concise labels only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for consistency
                max_tokens=20     # Strict limit to force brevity
            )
            
            label = response.choices[0].message.content.strip().strip('"\'.,')
            
            # Validate: If too long or empty, use fallback
            if not label or len(label.split()) > 8:
                return max(unique_texts, key=len)  # Longest is usually most descriptive
            
            logger.info(f"Generated concise label: '{label}' from {len(behavior_texts)} observations")
            return label
            
        except Exception as e:
            logger.error(f"Error generating concise label: {e}")
            # Fallback: Return longest text
            return max(unique_texts, key=len)
    
    def generate_cluster_name(
        self,
        wording_variations: List[str],
        cluster_size: int,
        tier: str
    ) -> str:
        """
        Generate a concise descriptive name for a behavior cluster
        
        Args:
            wording_variations: Different phrasings of behaviors in the cluster
            cluster_size: Number of observations in the cluster
            tier: Cluster tier (PRIMARY, SECONDARY, NOISE)
            
        Returns:
            str: Concise cluster name (3-6 words)
        """
        try:
            if not wording_variations:
                return "Unnamed Cluster"
            
            # Limit variations to avoid token overflow
            variations_sample = wording_variations[:5]
            variations_text = "\n".join(f"- {v}" for v in variations_sample)
            
            prompt = f"""Analyze these related user behaviors and create a concise, descriptive name:

{variations_text}

Cluster info:
- Size: {cluster_size} observations
- Importance: {tier}

Generate a SHORT descriptive name (3-6 words) that captures the common theme. Use clear, professional language.

Examples of good names:
- "Visual Learning Preference"
- "Detail-Oriented Communication"
- "Practical Application Focus"

Return ONLY the name, nothing else."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing behavioral patterns and creating clear, concise labels."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=30
            )
            
            cluster_name = response.choices[0].message.content.strip().strip('"\'.,')
            
            # Validate length (fallback if too long)
            if len(cluster_name.split()) > 8:
                # Use first meaningful variation as fallback
                cluster_name = variations_sample[0].title()
            
            logger.info(f"Generated cluster name: '{cluster_name}'")
            
            return cluster_name
            
        except Exception as e:
            logger.error(f"Error generating cluster name: {e}")
            # Fallback to first variation
            return wording_variations[0].title() if wording_variations else "Unnamed Cluster"


# Global archetype service instance
archetype_service = ArchetypeService()
