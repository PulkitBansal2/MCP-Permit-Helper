import asyncio
import json
import sys
import traceback
from pathlib import Path
from typing import Any
from datetime import datetime

# logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("Starting Permit MCP Server...")

try:
    from mcp.server.models import InitializationOptions
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    from mcp.server.stdio import stdio_server
    logger.info("MCP imports successful")
except Exception as e:
    logger.error(f"Failed to import MCP: {e}")
    sys.exit(1)

try:
    from permit_matcher import PermitMatcher
    from form_filler import FormFiller
    logger.info("Local imports successful")
except Exception as e:
    logger.error(f"Failed to import local modules: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

# Setup paths
BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
RULES_FILE = BASE_DIR / "data" / "permit_rules.json"

logger.info(f"Base directory: {BASE_DIR}")
logger.info(f"Templates directory: {TEMPLATES_DIR}")
logger.info(f"Output directory: {OUTPUT_DIR}")
logger.info(f"Rules file: {RULES_FILE}")

# Verify paths exist
if not RULES_FILE.exists():
    logger.error(f"Rules file not found: {RULES_FILE}")
    sys.exit(1)

if not TEMPLATES_DIR.exists():
    logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

if not OUTPUT_DIR.exists():
    logger.info(f"Creating output directory: {OUTPUT_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize components
try:
    permit_matcher = PermitMatcher(str(RULES_FILE))
    form_filler = FormFiller(str(TEMPLATES_DIR), str(OUTPUT_DIR))
    logger.info("Components initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize components: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

# Create server instance
server = Server("permit-form-filler")
logger.info("Server instance created")

def _format_field_name(field):
    """Format field name for display"""
    # Add spaces before capitals
    field_name = ''.join([' ' + c if c.isupper() else c for c in field]).strip()
    # Capitalize first letter
    field_name = field_name[0].upper() + field_name[1:] if field_name else ''
    
    # Fix common field names
    replacements = {
        'Projectaddress': 'Project Address',
        'Ownername': 'Owner Name',
        'Ownerphone': 'Owner Phone',
        'Owneremail': 'Owner Email',
        'Contractorname': 'Contractor Name',
        'Contractorlicense': 'Contractor License',
        'Contractorphone': 'Contractor Phone',
        'Insurancepolicy': 'Insurance Policy',
        'Projectdescription': 'Project Description',
        'Worktype': 'Work Type',
        'Estimatedcost': 'Estimated Cost',
        'Startdate': 'Start Date',
        'Buildingarea': 'Building Area',
        'Electricianname': 'Electrician Name',
        'Electricianlicense': 'Electrician License',
        'Electricianphone': 'Electrician Phone',
        'Electriciancompany': 'Electrician Company',
        'Workdescription': 'Work Description',
        'Servicetype': 'Service Type',
        'Numcircuits': 'Number of Circuits',
        'Panelupgrade': 'Panel Upgrade',
        'Newservice': 'New Service',
        'Specialrequirements': 'Special Requirements',
        'Plumbername': 'Plumber Name',
        'Plumberlicense': 'Plumber License',
        'Plumberphone': 'Plumber Phone',
        'Plumbercompany': 'Plumber Company',
        'Waterconnection': 'Water Connection',
        'Sewerconnection': 'Sewer Connection',
        'Gaslines': 'Gas Lines',
        'Numfixtures': 'Number of Fixtures',
        'Waterheater': 'Water Heater',
        'Backflowprevention': 'Backflow Prevention',
        'Demolitionscope': 'Demolition Scope',
        'Salvageplan': 'Salvage Plan',
        'Wastedisposal': 'Waste Disposal',
        'Environmentalimpact': 'Environmental Impact',
        'Mitigationplan': 'Mitigation Plan'
    }
    
    for old, new in replacements.items():
        if old.lower() in field_name.lower():
            field_name = new
            break
    
    return field_name

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="identify_required_permits",
            description="Identifies which permits are needed based on project requirements",
            inputSchema={
                "type": "object",
                "properties": {
                    "projectDescription": {
                        "type": "string",
                        "description": "Description of the project work to be done"
                    },
                    "workTypes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of work types (e.g., ['construction', 'electrical work'])"
                    }
                },
                "required": ["projectDescription"]
            }
        ),
        types.Tool(
            name="preview_permit",
            description="Preview what data will be filled in a permit before saving. Shows all fields and their values.",
            inputSchema={
                "type": "object",
                "properties": {
                    "permitId": {
                        "type": "string",
                        "description": "ID of the permit to preview (e.g., 'building', 'electrical')"
                    },
                    "projectData": {
                        "type": "object",
                        "description": "Project information to preview"
                    }
                },
                "required": ["permitId", "projectData"]
            }
        ),
        types.Tool(
            name="preview_all_permits",
            description="Preview all required permits for a project at once. Shows what data will be in each permit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "projectDescription": {
                        "type": "string",
                        "description": "Description of the project"
                    },
                    "projectData": {
                        "type": "object",
                        "description": "Complete project information"
                    }
                },
                "required": ["projectDescription", "projectData"]
            }
        ),
        types.Tool(
            name="fill_permit_form",
            description="Fills out and saves a specific permit form with project data. Use after previewing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "permitId": {
                        "type": "string",
                        "description": "ID of the permit to fill (e.g., 'building', 'electrical')"
                    },
                    "projectData": {
                        "type": "object",
                        "description": "Project information to fill into the form",
                        "properties": {
                            "projectAddress": {"type": "string"},
                            "ownerName": {"type": "string"},
                            "ownerPhone": {"type": "string"},
                            "ownerEmail": {"type": "string"},
                            "contractorName": {"type": "string"},
                            "contractorLicense": {"type": "string"},
                            "contractorPhone": {"type": "string"},
                            "insurancePolicy": {"type": "string"},
                            "projectDescription": {"type": "string"},
                            "workType": {"type": "string"},
                            "estimatedCost": {"type": "string"},
                            "startDate": {"type": "string"},
                            "duration": {"type": "string"},
                            "buildingArea": {"type": "string"},
                            "stories": {"type": "string"},
                            "electricianName": {"type": "string"},
                            "electricianLicense": {"type": "string"},
                            "electricianPhone": {"type": "string"},
                            "electricianCompany": {"type": "string"},
                            "workDescription": {"type": "string"},
                            "serviceType": {"type": "string"},
                            "voltage": {"type": "string"},
                            "amperage": {"type": "string"},
                            "numCircuits": {"type": "string"},
                            "panelUpgrade": {"type": "string"},
                            "newService": {"type": "string"},
                            "specialRequirements": {"type": "string"},
                            "plumberName": {"type": "string"},
                            "plumberLicense": {"type": "string"},
                            "plumberPhone": {"type": "string"},
                            "plumberCompany": {"type": "string"},
                            "waterConnection": {"type": "string"},
                            "sewerConnection": {"type": "string"},
                            "gasLines": {"type": "string"},
                            "numFixtures": {"type": "string"},
                            "waterHeater": {"type": "string"},
                            "backflowPrevention": {"type": "string"}
                        }
                    }
                },
                "required": ["permitId", "projectData"]
            }
        ),
        types.Tool(
            name="fill_all_required_permits",
            description="Identifies and fills all required permits for a project in one go. Consider using preview_all_permits first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "projectDescription": {
                        "type": "string",
                        "description": "Description of the project"
                    },
                    "workTypes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional array of work types"
                    },
                    "projectData": {
                        "type": "object",
                        "description": "Complete project information"
                    }
                },
                "required": ["projectDescription", "projectData"]
            }
        ),
        types.Tool(
            name="list_available_permits",
            description="Lists all available permit types",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="validate_permit_data",
            description="Validates if project data contains all required fields for a specific permit",
            inputSchema={
                "type": "object",
                "properties": {
                    "permitId": {
                        "type": "string",
                        "description": "ID of the permit to validate"
                    },
                    "projectData": {
                        "type": "object",
                        "description": "Project data to validate"
                    }
                },
                "required": ["permitId", "projectData"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""
    
    try:
        if name == "identify_required_permits":
            project_description = arguments.get("projectDescription", "")
            work_types = arguments.get("workTypes", [])
            
            required_permits = permit_matcher.identify_permits(
                project_description, 
                work_types
            )
            
            result = {
                "requiredPermits": required_permits,
                "count": len(required_permits),
                "message": f"Found {len(required_permits)} required permit(s)" 
                           if required_permits 
                           else "No permits required based on description"
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "preview_permit":
            permit_id = arguments.get("permitId")
            project_data = arguments.get("projectData", {})
            
            # Get permit details
            permit = permit_matcher.get_permit_by_id(permit_id)
            if not permit:
                raise ValueError(f"Permit not found: {permit_id}")
            
            # Validate required fields
            validation = form_filler.validate_required_fields(
                project_data,
                permit['requiredFields']
            )
            
            # Build preview text
            preview_lines = []
            preview_lines.append("=" * 70)
            preview_lines.append(f"PERMIT PREVIEW: {permit['name']}")
            preview_lines.append("=" * 70)
            preview_lines.append("")
            
            # Add validation status
            if not validation['valid']:
                preview_lines.append("⚠️  WARNING: Missing Required Fields")
                preview_lines.append(f"   Missing: {', '.join([_format_field_name(f) for f in validation['missingFields']])}")
                preview_lines.append("")
            else:
                preview_lines.append("✓ All required fields present")
                preview_lines.append("")
            
            # Show all fields with values
            preview_lines.append("FIELD VALUES:")
            preview_lines.append("-" * 70)
            
            for field in permit['requiredFields']:
                value = project_data.get(field, '[NOT PROVIDED]')
                field_name = _format_field_name(field)
                
                # Mark missing fields
                if value == '[NOT PROVIDED]':
                    preview_lines.append(f"  ⚠️  {field_name:.<40} {value}")
                else:
                    preview_lines.append(f"  ✓  {field_name:.<40} {value}")
            
            preview_lines.append("-" * 70)
            preview_lines.append("")
            
            # Add additional fields that will be auto-filled
            preview_lines.append("AUTO-FILLED FIELDS:")
            preview_lines.append(f"  Application Date................ {datetime.now().strftime('%m/%d/%Y')}")
            preview_lines.append(f"  Permit Date..................... {datetime.now().strftime('%m/%d/%Y')}")
            preview_lines.append("")
            
            preview_lines.append("=" * 70)
            
            if validation['valid']:
                preview_lines.append("")
                preview_lines.append("✓ This permit is ready to be saved.")
                preview_lines.append("  Use 'fill_permit_form' to save it, or provide updated data if needed.")
            else:
                preview_lines.append("")
                preview_lines.append("⚠️  This permit is missing required fields.")
                preview_lines.append("  Please provide the missing data before saving.")
            
            preview_text = "\n".join(preview_lines)
            
            return [types.TextContent(
                type="text",
                text=preview_text
            )]
        
        elif name == "preview_all_permits":
            project_description = arguments.get("projectDescription", "")
            project_data = arguments.get("projectData", {})
            
            # Identify required permits
            required_permits = permit_matcher.identify_permits(project_description)
            
            if not required_permits:
                return [types.TextContent(
                    type="text",
                    text="No permits required for this project description."
                )]
            
            # Build comprehensive preview
            preview_lines = []
            preview_lines.append("=" * 70)
            preview_lines.append("PREVIEW: ALL REQUIRED PERMITS")
            preview_lines.append("=" * 70)
            preview_lines.append("")
            preview_lines.append(f"Total Permits Required: {len(required_permits)}")
            preview_lines.append("")
            
            for i, permit_info in enumerate(required_permits, 1):
                permit = permit_matcher.get_permit_by_id(permit_info['id'])
                
                preview_lines.append(f"\n{'#' * 70}")
                preview_lines.append(f"PERMIT {i}: {permit['name']}")
                preview_lines.append(f"{'#' * 70}\n")
                
                # Validate
                validation = form_filler.validate_required_fields(
                    project_data,
                    permit['requiredFields']
                )
                
                if validation['valid']:
                    preview_lines.append("✓ Status: READY TO SAVE")
                else:
                    preview_lines.append("⚠️  Status: MISSING FIELDS")
                    preview_lines.append(f"   Missing: {', '.join([_format_field_name(f) for f in validation['missingFields']])}")
                
                preview_lines.append("")
                preview_lines.append("Required Fields:")
                
                for field in permit['requiredFields']:
                    value = project_data.get(field, '[NOT PROVIDED]')
                    field_name = _format_field_name(field)
                    
                    if value == '[NOT PROVIDED]':
                        preview_lines.append(f"  ⚠️  {field_name:.<40} {value}")
                    else:
                        preview_lines.append(f"  ✓  {field_name:.<40} {value}")
            
            preview_lines.append("\n" + "=" * 70)
            preview_lines.append("\nNEXT STEPS:")
            preview_lines.append("  1. Review the data above")
            preview_lines.append("  2. Provide any missing information")
            preview_lines.append("  3. Use 'fill_all_required_permits' to save all permits")
            preview_lines.append("     OR use 'fill_permit_form' to save individual permits")
            
            return [types.TextContent(
                type="text",
                text="\n".join(preview_lines)
            )]
        
        elif name == "fill_permit_form":
            permit_id = arguments.get("permitId")
            project_data = arguments.get("projectData", {})
            
            # Get permit details
            permit = permit_matcher.get_permit_by_id(permit_id)
            if not permit:
                raise ValueError(f"Permit not found: {permit_id}")
            
            # Validate required fields
            validation = form_filler.validate_required_fields(
                project_data, 
                permit['requiredFields']
            )
            
            if not validation['valid']:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "Missing required fields",
                        "missingFields": validation['missingFields'],
                        "permitName": permit['name']
                    }, indent=2)
                )]
            
            # Fill the form
            result = form_filler.fill_permit(
                permit['template'],
                permit['id'],
                permit['name'],
                project_data
            )
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "fill_all_required_permits":
            project_description = arguments.get("projectDescription", "")
            work_types = arguments.get("workTypes", [])
            project_data = arguments.get("projectData", {})
            
            # Identify required permits
            required_permits = permit_matcher.identify_permits(
                project_description, 
                work_types
            )
            
            if not required_permits:
                return [types.TextContent(
                    type="text",
                    text="No permits required for this project"
                )]
            
            # Fill all required permits
            results = []
            for permit_info in required_permits:
                try:
                    permit = permit_matcher.get_permit_by_id(permit_info['id'])
                    
                    # Validate fields
                    validation = form_filler.validate_required_fields(
                        project_data,
                        permit['requiredFields']
                    )
                    
                    if not validation['valid']:
                        results.append({
                            "success": False,
                            "permitId": permit['id'],
                            "permitName": permit['name'],
                            "error": "Missing required fields",
                            "missingFields": validation['missingFields']
                        })
                        continue
                    
                    # Fill permit
                    result = form_filler.fill_permit(
                        permit['template'],
                        permit['id'],
                        permit['name'],
                        project_data
                    )
                    results.append(result)
                    
                except Exception as e:
                    results.append({
                        "success": False,
                        "permitId": permit_info['id'],
                        "error": str(e)
                    })
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "totalPermits": len(results),
                    "results": results,
                    "message": "All required permits have been processed"
                }, indent=2)
            )]
        
        elif name == "list_available_permits":
            permits = permit_matcher.list_all_permits()
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "permits": permits,
                    "count": len(permits)
                }, indent=2)
            )]
        
        elif name == "validate_permit_data":
            permit_id = arguments.get("permitId")
            project_data = arguments.get("projectData", {})
            
            permit = permit_matcher.get_permit_by_id(permit_id)
            if not permit:
                raise ValueError(f"Permit not found: {permit_id}")
            
            validation = form_filler.validate_required_fields(
                project_data,
                permit['requiredFields']
            )
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "permitId": permit_id,
                    "permitName": permit['name'],
                    "valid": validation['valid'],
                    "missingFields": validation['missingFields'],
                    "requiredFields": permit['requiredFields']
                }, indent=2)
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Main entry point for the server"""
    try:
        logger.info("Starting stdio server...")
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server streams established")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="permit-form-filler",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    )
                )
            )
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        logger.info("Running main async loop...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())

        sys.exit(1)
