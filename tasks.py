from crewai import Task
from agents import (
    user_input_agent,
    api_integration_agent,
    data_processing_agent,
    geospatial_agent,
    response_agent,
    error_handling_agent
)


# User Input Validation Task
validation_task = Task(
    description="""
    Validate User Input for Train Status Query:
    1. Check if train number is exactly 5 digits using regex pattern
    2. Validate date format (YYYY-MM-DD) if provided
    3. Ensure date is not in the past and not more than 120 days in future
    4. Set default date to today if not provided
    5. Return validation results with clear error messages if invalid
    
    Use the TrainValidationTool to perform validation checks.
    Pass the input as a JSON string containing train_number and optional date.
    
    Input: train_number (string), date (optional string)
    Output: JSON string with validation status, cleaned train_number, and date
    """,
    agent=user_input_agent,
    expected_output="JSON string containing: {'valid': bool, 'train_number': str, 'date': str} or {'valid': False, 'error': str}"
)


# API Data Retrieval Task  
api_retrieval_task = Task(
    description="""
    Fetch Live Train Status Data from Railway APIs:
    1. Use validated train number and date from previous task
    2. Make API call to railway service with proper error handling
    3. Handle API rate limits and caching (5-minute cache)
    4. Use mock data if no API key is configured
    5. Return structured API response or error information
    
    Use the RailwayAPITool to fetch train status data.
    Pass the validation result from the previous task as input.
    
    Input: Validation result from validation_task (JSON string)
    Output: JSON string with train status data including train_number, train_name, current_station, coordinates, timings, and upcoming_stations
    """,
    agent=api_integration_agent,
    expected_output="JSON string with train status data including train_number, train_name, current_station, coordinates, timings, and upcoming_stations",
    dependencies=[validation_task]
)


# Data Processing Task
data_processing_task = Task(
    description="""
    Process and Structure Raw API Data:
    1. Extract key train information (number, name, current station, location)
    2. Calculate delay in minutes from scheduled vs actual times
    3. Determine status category (On Time, Slightly Delayed, Delayed, Significantly Delayed)
    4. Structure location data with coordinates
    5. Process next stations list
    6. Add reliability metrics and status emojis
    7. Handle missing or malformed data gracefully
    
    Use the DataProcessingTool to transform raw API data.
    Pass the API response from the previous task as input.
    
    Input: Raw API response data from api_retrieval_task (JSON string)
    Output: JSON string with structured dictionary containing processed train status information
    """,
    agent=data_processing_agent,
    expected_output="JSON string with structured data including status, delay_minutes, current_location, next_stations, and reliability_score",
    dependencies=[api_retrieval_task]
)


# Geospatial Calculation Task
geospatial_task = Task(
    description="""
    Perform Geospatial Calculations (Optional):
    1. Extract current coordinates from processed data
    2. Calculate distances using Haversine formula if target coordinates available
    3. Determine bearing/direction between coordinates
    4. Estimate speed if time difference data is available
    5. Provide proximity information and travel estimates
    6. Handle coordinate validation and error cases
    
    Use the GeospatialTool for mathematical calculations.
    This task only runs if valid coordinates are available.
    Extract coordinates from the processed data and format as JSON input.
    
    Input: Coordinates extracted from processed data (JSON string with current_lat, current_lon, optional target coordinates)
    Output: JSON string with distance, bearing, speed, and direction information
    """,
    agent=geospatial_agent,
    expected_output="JSON string with geospatial calculations including distance_km, bearing_degrees, direction, and optional speed_kmh",
    dependencies=[data_processing_task]
)


# Response Generation Task
response_generation_task = Task(
    description="""
    Generate User-Friendly Response for Train Status:
    1. Create human-readable summary of train status with emojis
    2. Include relevant status indicators and formatting
    3. Mention delays, current location, and next stops clearly
    4. Provide clear status categories with appropriate emojis
    5. Add reliability scores and helpful context
    6. Handle error cases with constructive messages
    7. Include data source information when using mock data
    
    Use the ResponseGeneratorTool to create the final response.
    Pass the processed data from the data_processing_task as input.
    
    Input: Processed train status data from data_processing_task (JSON string)
    Output: JSON string with formatted response message, success status, and summary data
    """,
    agent=response_agent,
    expected_output="JSON string with formatted response message, success status, and structured summary data",
    dependencies=[data_processing_task, geospatial_task]
)


# Error Handling Task
error_handling_task = Task(
    description="""
    Handle Errors and Provide Helpful Guidance:
    1. Identify error types (validation, api, network, processing, execution)
    2. Provide appropriate fallback suggestions based on error type
    3. Determine if retry is recommended for the specific error
    4. Generate helpful, user-friendly error messages
    5. Include specific suggestions for resolution
    6. Log error context for debugging purposes
    
    Use the ErrorHandlingTool to process error scenarios.
    This task can be triggered by any other task that encounters errors.
    Format the input as JSON string with error_type and error_message.
    
    Input: Error context as JSON string: {"error_type": "type", "error_message": "message"}
    Output: JSON string with error handling results including message, suggestions list, and retry_recommended boolean
    """,
    agent=error_handling_agent,
    expected_output="JSON string with error handling results including message, suggestions list, and retry_recommended boolean",
    dependencies=[]  # Can be triggered by any task that encounters errors
)


# Task execution order and dependencies
task_execution_order = [
    "validation_task",      # First: Validate input
    "api_retrieval_task",   # Second: Fetch data (depends on validation)
    "data_processing_task", # Third: Process data (depends on API)
    "geospatial_task",      # Fourth: Calculate distances (depends on processing)
    "response_generation_task" # Fifth: Generate response (depends on processing + geospatial)
]

# Task list for easy import and management
all_tasks = [
    validation_task,
    api_retrieval_task,
    data_processing_task,
    geospatial_task,
    response_generation_task,
    error_handling_task
]

# Main workflow tasks (excluding error handling which is triggered as needed)
main_workflow_tasks = [
    validation_task,
    api_retrieval_task,
    data_processing_task,
    geospatial_task,
    response_generation_task
]

# Error handling tasks (used when main workflow fails)
error_workflow_tasks = [
    error_handling_task
]

# Task metadata for monitoring and debugging
task_metadata = {
    "validation_task": {
        "category": "input_processing",
        "estimated_duration": "1-2 seconds",
        "dependencies": [],
        "tools_used": ["TrainValidationTool"],
        "input_format": "JSON string with train_number and optional date",
        "output_format": "JSON string with validation results"
    },
    "api_retrieval_task": {
        "category": "data_fetching",
        "estimated_duration": "3-10 seconds",
        "dependencies": ["validation_task"],
        "tools_used": ["RailwayAPITool"],
        "input_format": "Validation result from previous task",
        "output_format": "JSON string with train status data"
    },
    "data_processing_task": {
        "category": "data_transformation",
        "estimated_duration": "2-5 seconds",
        "dependencies": ["api_retrieval_task"],
        "tools_used": ["DataProcessingTool"],
        "input_format": "Raw API response from previous task",
        "output_format": "JSON string with processed train data"
    },
    "geospatial_task": {
        "category": "calculation",
        "estimated_duration": "1-3 seconds",
        "dependencies": ["data_processing_task"],
        "tools_used": ["GeospatialTool"],
        "input_format": "JSON string with coordinate data",
        "output_format": "JSON string with geospatial calculations"
    },
    "response_generation_task": {
        "category": "output_formatting",
        "estimated_duration": "1-2 seconds",
        "dependencies": ["data_processing_task", "geospatial_task"],
        "tools_used": ["ResponseGeneratorTool"],
        "input_format": "Processed data from data_processing_task",
        "output_format": "JSON string with formatted response"
    },
    "error_handling_task": {
        "category": "error_management",
        "estimated_duration": "1-2 seconds",
        "dependencies": [],
        "tools_used": ["ErrorHandlingTool"],
        "input_format": "JSON string with error_type and error_message",
        "output_format": "JSON string with error handling results"
    }
}

# Helper function to format error input for error handling task
def format_error_input(error_type: str, error_message: str) -> str:
    """Format error information for the ErrorHandlingTool"""
    import json
    return json.dumps({
        "error_type": error_type,
        "error_message": error_message
    })

# Helper function to format validation input
def format_validation_input(train_number: str, date: str = None) -> str:
    """Format validation input for the TrainValidationTool"""
    import json
    input_data = {"train_number": train_number}
    if date:
        input_data["date"] = date
    return json.dumps(input_data)

# Helper function to extract coordinates for geospatial task
def format_geospatial_input(processed_data: dict, target_lat: float = None, target_lon: float = None) -> str:
    """Format geospatial input for the GeospatialTool"""
    import json
    
    if isinstance(processed_data, str):
        import json
        processed_data = json.loads(processed_data)
    
    current_location = processed_data.get("current_location", {})
    
    geospatial_input = {
        "current_lat": current_location.get("lat", 0),
        "current_lon": current_location.get("lon", 0)
    }
    
    if target_lat and target_lon:
        geospatial_input["target_lat"] = target_lat
        geospatial_input["target_lon"] = target_lon
    
    return json.dumps(geospatial_input)
