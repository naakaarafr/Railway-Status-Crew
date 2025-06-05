from crewai import Agent
from config import get_llm
from tools import (
    TrainValidationTool,
    RailwayAPITool,
    GeospatialTool,
    DataProcessingTool,
    ResponseGeneratorTool,
    ErrorHandlingTool
)

# Get the configured Gemini LLM
llm = get_llm()

# User Input Agent
user_input_agent = Agent(
    role="User Input Handler",
    goal="Validate and process user queries for train status",
    backstory="You are responsible for understanding user requests and ensuring all inputs are properly validated before processing. You handle train number validation using 5-digit regex patterns and date validation to ensure dates are not in the past.",
    tools=[TrainValidationTool()],
    verbose=True,
    allow_delegation=False,
    llm=llm
)


# API Integration Agent  
api_integration_agent = Agent(
    role="API Integration Specialist", 
    goal="Fetch real-time train data from railway APIs efficiently",
    backstory="You handle all external API communications with Indian Railway services. You manage caching to reduce redundant calls, handle rate limits, and ensure reliable data retrieval. You're experienced with various railway APIs like RailYatri and NTES.",
    tools=[RailwayAPITool()],
    verbose=True,
    allow_delegation=False,
    llm=llm
)


# Data Processing Agent
data_processing_agent = Agent(
    role="Data Processing Expert",
    goal="Transform raw API data into structured, meaningful information",
    backstory="You are an expert at parsing complex railway data from various API formats. You extract key details like current location, speed, delays, and next stops. You calculate meaningful metrics and provide structured data that other agents can easily work with.",
    tools=[DataProcessingTool()],
    verbose=True,
    allow_delegation=False,
    llm=llm
)


# Geospatial Calculator Agent
geospatial_agent = Agent(
    role="Geospatial Calculator",
    goal="Calculate distances, speeds, and directions using mathematical formulas",
    backstory="You are a mathematics expert specializing in geospatial calculations. You use pure mathematical formulas like Haversine for distance calculations, bearing calculations for directions, and speed estimations using time differences. You work without external mapping services, relying only on coordinate mathematics.",
    tools=[GeospatialTool()],
    verbose=True,
    allow_delegation=False,
    llm=llm
)


# Response Generation Agent
response_agent = Agent(
    role="Response Generator",
    goal="Create user-friendly responses with train status information",
    backstory="You are skilled at communicating complex train status information in a clear, helpful manner that users can easily understand. You create human-readable summaries with appropriate emojis and formatting, making technical data accessible to everyday users.",
    tools=[ResponseGeneratorTool()],
    verbose=True,
    allow_delegation=False,
    llm=llm
)


# Error Handling Agent
error_handling_agent = Agent(
    role="Error Handler",
    goal="Manage failures gracefully and provide helpful alternatives",
    backstory="You are the safety net of the system, ensuring that when things go wrong, users receive helpful guidance instead of confusing error messages. You provide fallback suggestions, determine when retries are appropriate, and maintain a positive user experience even during failures.",
    tools=[ErrorHandlingTool()],
    verbose=True,
    allow_delegation=False,
    llm=llm
)
