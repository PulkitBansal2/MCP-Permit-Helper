import json
from typing import List, Dict, Any
from pathlib import Path

class PermitMatcher:
    """Identifies required permits based on project requirements"""
    
    def __init__(self, rules_file: str):
        self.rules_file = Path(rules_file)
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load permit rules from JSON file"""
        with open(self.rules_file, 'r') as f:
            return json.load(f)
    
    def identify_permits(
        self, 
        project_description: str, 
        work_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify required permits based on project description and work types
        
        Args:
            project_description: Description of the project work
            work_types: Optional list of work type keywords
            
        Returns:
            List of required permits with their details
        """
        if work_types is None:
            work_types = []
        
        # Combine all search text
        search_text = f"{project_description} {' '.join(work_types)}".lower()
        
        required_permits = []
        
        for permit in self.rules['permits']:
            # Check if any trigger matches
            matches = any(
                trigger.lower() in search_text 
                for trigger in permit['triggers']
            )
            
            if matches:
                required_permits.append({
                    'id': permit['id'],
                    'name': permit['name'],
                    'template': permit['template'],
                    'requiredFields': permit['requiredFields']
                })
        
        return required_permits
    
    def get_permit_by_id(self, permit_id: str) -> Dict[str, Any]:
        """Get permit details by ID"""
        for permit in self.rules['permits']:
            if permit['id'] == permit_id:
                return permit
        return None
    
    def list_all_permits(self) -> List[Dict[str, Any]]:
        """List all available permits"""
        return [
            {
                'id': permit['id'],
                'name': permit['name'],
                'triggers': permit['triggers']
            }
            for permit in self.rules['permits']
        ]