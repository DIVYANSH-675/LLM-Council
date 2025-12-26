"""
Rubric Loader - Centralized rubric management for the council
Loads and provides access to rubric configurations
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class RubricLoader:
    """
    Loads and manages rubric configurations from YAML.
    Provides helper methods for accessing dimensions and weights.
    """
    
    def __init__(self, config_path: str = "config/rubric.yaml"):
        """
        Initialize rubric loader.
        
        Args:
            config_path: Path to rubric YAML config
        """
        self.config_path = Path(config_path)
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Rubric config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)
    
    def get_rubric(self, rubric_name: str) -> Dict[str, Any]:
        """
        Get a specific rubric by name.
        
        Args:
            rubric_name: Name of rubric (e.g., 'factuality_rubric')
            
        Returns:
            Rubric configuration dict
        """
        if rubric_name not in self._config:
            raise KeyError(f"Rubric '{rubric_name}' not found")
        return self._config[rubric_name]
    
    def get_factuality_rubric(self) -> Dict[str, Any]:
        """Get the factuality rubric"""
        return self.get_rubric('factuality_rubric')
    
    def get_safety_rubric(self) -> Dict[str, Any]:
        """Get the safety rubric"""
        return self.get_rubric('safety_rubric')
    
    def get_dimensions(self, rubric_name: str) -> Dict[str, Dict]:
        """
        Get dimensions for a rubric.
        
        Returns:
            Dict mapping dimension name to config
        """
        rubric = self.get_rubric(rubric_name)
        return rubric.get('dimensions', {})
    
    def get_weights(self, rubric_name: str) -> Dict[str, float]:
        """
        Get weights for each dimension in a rubric.
        
        Returns:
            Dict mapping dimension name to weight
        """
        dims = self.get_dimensions(rubric_name)
        return {name: config.get('weight', 0.25) for name, config in dims.items()}
    
    def validate_weights(self, rubric_name: str) -> bool:
        """
        Check if weights sum to approximately 1.0.
        
        Returns:
            True if valid
        """
        weights = self.get_weights(rubric_name)
        total = sum(weights.values())
        return abs(total - 1.0) < 0.01
    
    def get_all_rubric_names(self) -> List[str]:
        """Get list of all rubric names"""
        return list(self._config.keys())
    
    def calculate_weighted_score(
        self, 
        rubric_name: str, 
        scores: Dict[str, float]
    ) -> float:
        """
        Calculate weighted score using rubric weights.
        
        Args:
            rubric_name: Which rubric to use
            scores: Dict of dimension -> score (0-10)
            
        Returns:
            Weighted average score (0-10)
        """
        weights = self.get_weights(rubric_name)
        
        total = 0.0
        total_weight = 0.0
        
        for dim, weight in weights.items():
            if dim in scores:
                total += scores[dim] * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return total / total_weight


# Singleton instance for convenience
_loader_instance: Optional[RubricLoader] = None


def get_rubric_loader(config_path: str = "config/rubric.yaml") -> RubricLoader:
    """Get or create singleton rubric loader"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = RubricLoader(config_path)
    return _loader_instance
