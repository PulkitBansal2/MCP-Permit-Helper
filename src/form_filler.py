from docxtpl import DocxTemplate
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import os

class FormFiller:
    """Fills Word document templates with project data"""
    
    def __init__(self, templates_dir: str, output_dir: str):
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def fill_permit(
        self, 
        template_name: str, 
        permit_id: str,
        permit_name: str,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fill a permit form with project data
        
        Args:
            template_name: Name of the template file
            permit_id: ID of the permit
            permit_name: Human-readable name of the permit
            project_data: Dictionary containing project information
            
        Returns:
            Dictionary with success status and output file path
        """
        template_path = self.templates_dir / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        # Load template
        doc = DocxTemplate(template_path)
        
        # Prepare data with automatic date fields
        fill_data = {
            **project_data,
            'permitDate': datetime.now().strftime('%m/%d/%Y'),
            'applicationDate': datetime.now().strftime('%m/%d/%Y'),
            'currentDate': datetime.now().strftime('%m/%d/%Y'),
            'year': datetime.now().year
        }
        
        # Render template with data
        doc.render(fill_data)
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_filename = f"{permit_id}-permit-{timestamp}.docx"
        output_path = self.output_dir / output_filename
        
        # Save filled document
        doc.save(output_path)
        
        return {
            'success': True,
            'permitName': permit_name,
            'outputFile': output_filename,
            'outputPath': str(output_path.absolute()),
            'message': f'{permit_name} has been filled and saved'
        }
    
    def validate_required_fields(
        self, 
        project_data: Dict[str, Any], 
        required_fields: list
    ) -> Dict[str, Any]:
        """
        Validate that all required fields are present in project data
        
        Returns:
            Dictionary with validation result
        """
        missing_fields = [
            field for field in required_fields 
            if field not in project_data or not project_data[field]
        ]
        
        return {
            'valid': len(missing_fields) == 0,
            'missingFields': missing_fields
        }