from langchain_core.tools import BaseTool
from typing import Dict, List, Optional, Tuple, Any, Union
from crewai_tools import SerperDevTool
import re
import json
import requests
from datetime import datetime, timedelta
import math
import time
import os


from langchain_core.tools import BaseTool
from typing import Dict, List, Optional, Any, Union
import re
import json
from datetime import datetime, timedelta
from pydantic import BaseModel, Field


class TrainValidationInput(BaseModel):
    """Input schema for train validation tool"""
    train_number: str = Field(description="5-digit train number")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")


class TrainValidationTool(BaseTool):
    name: str = "train_validation_tool"
    description: str = """
    Validates train numbers and dates for Indian Railways.
    Input should be a JSON string with 'train_number' (5 digits) and optional 'date' (YYYY-MM-DD).
    Returns validation result with standardized format.
    """
    
    # Add input schema for better CrewAI compatibility
    args_schema: type[BaseModel] = TrainValidationInput
    
    def _run(self, train_number: str, date: Optional[str] = None) -> str:
        """
        Run the validation tool with direct parameters
        """
        try:
            # Clean and validate train number
            train_number = str(train_number).strip()
            
            # Validate train number (5 digits)
            train_pattern = r'^[0-9]{5}$'
            if not re.match(train_pattern, train_number):
                return self._format_error("Train number must be exactly 5 digits")
            
            # Validate date if provided
            if date:
                try:
                    date = str(date).strip()
                    parsed_date = datetime.strptime(date, "%Y-%m-%d")
                    if parsed_date.date() < datetime.now().date():
                        return self._format_error("Date cannot be in the past")
                    # Check if date is too far in future (120 days)
                    max_future_date = datetime.now().date() + timedelta(days=120)
                    if parsed_date.date() > max_future_date:
                        return self._format_error("Date cannot be more than 120 days in the future")
                except ValueError:
                    return self._format_error("Invalid date format. Use YYYY-MM-DD")
            else:
                # Set default date to today
                date = datetime.now().strftime("%Y-%m-%d")
            
            # Return success result
            result = {
                "valid": True,
                "train_number": train_number,
                "date": date,
                "message": f"Train {train_number} validated successfully for {date}"
            }
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            return self._format_error(f"Validation error: {str(e)}")
    
    def _format_error(self, error_message: str) -> str:
        """Format error response consistently"""
        result = {
            "valid": False,
            "error": error_message,
            "train_number": None,
            "date": None
        }
        return json.dumps(result, ensure_ascii=False)
    
    # Alternative method for string input (legacy support)
    def run(self, input_data: Union[str, dict]) -> str:
        """
        Alternative run method for backward compatibility
        """
        try:
            # Parse input - handle both string and dict formats
            if isinstance(input_data, str):
                try:
                    parsed_data = json.loads(input_data)
                except json.JSONDecodeError:
                    # If not JSON, try to extract train number from string
                    train_match = re.search(r'\b\d{5}\b', input_data)
                    if train_match:
                        parsed_data = {"train_number": train_match.group(0)}
                    else:
                        return self._format_error("Could not parse train number from input")
            else:
                parsed_data = input_data
            
            # Ensure we have a dictionary to work with
            if not isinstance(parsed_data, dict):
                return self._format_error("Invalid input format")
            
            train_number = parsed_data.get("train_number", "")
            date = parsed_data.get("date")
            
            return self._run(train_number, date)
            
        except Exception as e:
            return self._format_error(f"Input parsing error: {str(e)}")


# Additional fix: Create a CrewAI-compatible wrapper if needed
class CrewAITrainValidationTool(BaseTool):
    """CrewAI-specific wrapper for train validation"""
    name: str = "train_validation_tool"
    description: str = "Validates train numbers and dates. Pass train_number and optional date."
    
    def _run(self, input_string: str) -> str:
        """CrewAI compatible run method"""
        validation_tool = TrainValidationTool()
        return validation_tool.run(input_string)
    
    async def _arun(self, input_string: str) -> str:
        """Async version for CrewAI compatibility"""
        return self._run(input_string)


# Helper function to create the tool instance
def create_train_validation_tool():
    """Factory function to create the appropriate tool instance"""
    try:
        # Try to import CrewAI to check if we're in a CrewAI environment
        import crewai
        return CrewAITrainValidationTool()
    except ImportError:
        # Fall back to standard LangChain tool
        return TrainValidationTool()


class RailwayAPITool(BaseTool):
    name: str = "railway_api_tool" 
    description: str = "Fetches live train status using web search. Input: validation result as JSON string"
    
    # Class-level cache
    cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
    cache_timeout: int = 300  # 5 minutes
    
    def _run(self, input_data: str) -> str:
        try:
            # Parse input - be more defensive about the parsing
            if isinstance(input_data, str):
                try:
                    # Try to parse as JSON - fix the "valid" parsing issue
                    cleaned_input = input_data.strip()
                    
                    # Handle case where input is double-quoted JSON string
                    # Simplified parsing that handles the 'valid' key issue
                    try:
                        parsed_data = json.loads(cleaned_input)
                    except json.JSONDecodeError:
                        # If direct parsing fails, try removing outer quotes
                        if cleaned_input.startswith('"') and cleaned_input.endswith('"'):
                            try:
                                parsed_data = json.loads(cleaned_input[1:-1])
                            except json.JSONDecodeError:
                                # Last resort - try to extract train number
                                train_match = re.search(r'\b\d{5}\b', input_data)
                                if train_match:
                                    parsed_data = {"train_number": train_match.group(0), "valid": True}
                                else:
                                    return json.dumps({"error": "Could not parse input data"})
                        else:
                            return json.dumps({"error": "Invalid JSON format"})
                except json.JSONDecodeError as e:
                    # If JSON parsing fails, try to extract train number directly
                    train_match = re.search(r'\b\d{5}\b', input_data)
                    if train_match:
                        parsed_data = {"train_number": train_match.group(0), "valid": True}
                    else:
                        return json.dumps({"error": f"Could not parse input data or extract train number. JSON error: {str(e)}"})
            else:
                parsed_data = input_data if isinstance(input_data, dict) else {}
            
            # Handle validation result format
            if "valid" in parsed_data:
                # This is a validation result
                if not parsed_data.get("valid", False):
                    error_msg = parsed_data.get("error", "Invalid input from validation")
                    return json.dumps({"error": error_msg})
                train_number = parsed_data.get("train_number", "")
                date = parsed_data.get("date")
            else:
                # Direct input format - extract what we can
                train_number = str(parsed_data.get("train_number", "")).strip()
                date = parsed_data.get("date")
            
            if not train_number:
                return json.dumps({"error": "Train number is required"})
            
            # Validate train number format again as a safety check
            if not re.match(r'^[0-9]{5}$', train_number):
                return json.dumps({"error": "Invalid train number format - must be 5 digits"})
            
            cache_key = f"{train_number}_{date or 'today'}"
            
            # Check cache first
            if cache_key in self.__class__.cache:
                cached_data, timestamp = self.__class__.cache[cache_key]
                if time.time() - timestamp < self.cache_timeout:
                    cached_data["source"] = "cache"
                    return json.dumps(cached_data)
            
            # Try to get search tool
            try:
                search_tool = SerperDevTool()
                
                # Use Serper to search for train status
                search_query = f"train {train_number} live status running status current location indian railway"
                if date and date != datetime.now().strftime("%Y-%m-%d"):
                    search_query += f" {date}"
                
                search_results = search_tool._run(search_query)
                
                # Process search results to extract train information
                train_data = self._extract_train_info(search_results, train_number)
                
                # Cache the response
                self.__class__.cache[cache_key] = (train_data, time.time())
                train_data["source"] = "web_search"
                
                return json.dumps(train_data)
                
            except Exception as search_error:
                # Fallback to mock data if search fails
                mock_data = self._get_mock_data(train_number, date, f"Search failed: {str(search_error)}")
                return json.dumps(mock_data)
                
        except Exception as e:
            # Return mock data if everything fails
            mock_data = self._get_mock_data(
                train_number if 'train_number' in locals() and train_number else "00000", 
                date if 'date' in locals() else None, 
                f"API tool failed: {str(e)}"
            )
            return json.dumps(mock_data)
    
    def _extract_train_info(self, search_results: Union[str, Dict], train_number: str) -> Dict[str, Any]:
        """Extract train information from search results"""
        try:
            # Parse search results
            if isinstance(search_results, str):
                try:
                    results_data = json.loads(search_results)
                except json.JSONDecodeError:
                    results_data = {"organic": []}
            else:
                results_data = search_results if isinstance(search_results, dict) else {"organic": []}
            
            # Initialize train info
            train_info = {
                "train_number": train_number,
                "train_name": f"Train {train_number}",
                "current_station": "Information not available",
                "current_lat": 0.0,
                "current_lon": 0.0,
                "scheduled_arrival": None,
                "actual_arrival": None,
                "upcoming_stations": [],
                "last_updated": datetime.now().isoformat(),
                "data_source": "web_search"
            }
            
            # Extract information from search results
            organic_results = results_data.get("organic", [])
            
            for result in organic_results[:5]:  # Check first 5 results
                if not isinstance(result, dict):
                    continue
                    
                title = result.get("title", "").lower()
                snippet = result.get("snippet", "").lower()
                
                # Extract train name if found
                if train_number in title and "train" in title:
                    train_info["train_name"] = result.get("title", "").replace(train_number, "").strip()
                
                # Look for status keywords
                if any(keyword in snippet for keyword in ["running", "departed", "arrived", "delayed", "on time"]):
                    # Try to extract current station
                    station_match = re.search(r'(?:at|from|departed|arrived)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|\.)', snippet)
                    if station_match:
                        train_info["current_station"] = station_match.group(1).strip()
                    
                    # Look for delay information
                    delay_match = re.search(r'(\d+)\s*(?:min|minute|hr|hour).*(?:late|delay)', snippet)
                    if delay_match:
                        delay_minutes = int(delay_match.group(1))
                        if "hr" in snippet or "hour" in snippet:
                            delay_minutes *= 60
                        # Set mock arrival times based on delay
                        now = datetime.now()
                        train_info["scheduled_arrival"] = now.isoformat()
                        train_info["actual_arrival"] = (now + timedelta(minutes=delay_minutes)).isoformat()
            
            return train_info
            
        except Exception as e:
            return self._get_mock_data(train_number, None, f"Data extraction failed: {str(e)}")
    
    def _get_mock_data(self, train_number: str, date: str = None, error_context: str = "") -> Dict[str, Any]:
        """Generate mock data when real data is not available"""
        mock_stations = [
            "New Delhi", "Mumbai Central", "Chennai Central", "Kolkata",
            "Bangalore City", "Hyderabad", "Pune", "Ahmedabad", "Jaipur",
            "Lucknow", "Kanpur", "Nagpur", "Bhopal", "Indore", "Surat"
        ]
        
        import random
        current_station = random.choice(mock_stations)
        delay_minutes = random.randint(0, 45)  # Random delay 0-45 minutes
        
        now = datetime.now()
        
        return {
            "train_number": str(train_number),
            "train_name": f"Express Train {train_number}",
            "current_station": current_station,
            "current_lat": random.uniform(8.0, 37.0),  # India latitude range
            "current_lon": random.uniform(68.0, 97.0),  # India longitude range
            "scheduled_arrival": now.isoformat(),
            "actual_arrival": (now + timedelta(minutes=delay_minutes)).isoformat(),
            "upcoming_stations": random.sample(mock_stations, 3),
            "last_updated": now.isoformat(),
            "data_source": "mock_data",
            "note": f"Using mock data - {error_context}" if error_context else "Using mock data for demonstration"
        }


class GeospatialTool(BaseTool):
    name: str = "geospatial_tool"
    description: str = "Calculates distances, speeds, and directions using pure math. Input: coordinates as JSON string"
    
    def _run(self, input_data: str) -> str:
        try:
            # Parse input
            if isinstance(input_data, str):
                try:
                    # Handle potential escaping issues similar to RailwayAPITool
                    cleaned_input = input_data.strip()
                    if cleaned_input.startswith('"') and cleaned_input.endswith('"'):
                        cleaned_input = cleaned_input[1:-1]
                    cleaned_input = cleaned_input.replace('\\"', '"').replace("\\'", "'")
                    
                    parsed_data = json.loads(cleaned_input)
                except json.JSONDecodeError:
                    return json.dumps({"error": "Could not parse input data"})
            else:
                parsed_data = input_data
            
            if not isinstance(parsed_data, dict):
                return json.dumps({"error": "Invalid input format"})
            
            # Extract coordinates - handle nested structures
            if "current_location" in parsed_data:
                location = parsed_data["current_location"]
                current_lat = location.get("lat", 0)
                current_lon = location.get("lon", 0)
            else:
                current_lat = parsed_data.get("current_lat", 0)
                current_lon = parsed_data.get("current_lon", 0)
            
            target_lat = parsed_data.get("target_lat")
            target_lon = parsed_data.get("target_lon")
            
            # Basic coordinate validation
            if not (-90 <= current_lat <= 90) or not (-180 <= current_lon <= 180):
                return json.dumps({"error": "Invalid current coordinates"})
            
            result = {
                "current_coordinates": {
                    "lat": current_lat,
                    "lon": current_lon
                }
            }
            
            # Calculate distance and bearing if target coordinates are provided
            if target_lat is not None and target_lon is not None:
                if not (-90 <= target_lat <= 90) or not (-180 <= target_lon <= 180):
                    return json.dumps({"error": "Invalid target coordinates"})
                
                distance_km = self._haversine_distance(current_lat, current_lon, target_lat, target_lon)
                bearing_deg = self._calculate_bearing(current_lat, current_lon, target_lat, target_lon)
                direction = self._bearing_to_direction(bearing_deg)
                
                result.update({
                    "target_coordinates": {
                        "lat": target_lat,
                        "lon": target_lon
                    },
                    "distance_km": round(distance_km, 2),
                    "bearing_degrees": round(bearing_deg, 1),
                    "direction": direction
                })
            
            # Add coordinate region information
            region_info = self._get_region_info(current_lat, current_lon)
            result["region_info"] = region_info
            
            return json.dumps(result)
            
        except Exception as e:
            return json.dumps({"error": f"Geospatial calculation failed: {str(e)}"})
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing between two points"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        # Normalize to 0-360 degrees
        return (bearing_deg + 360) % 360
    
    def _bearing_to_direction(self, bearing: float) -> str:
        """Convert bearing to compass direction"""
        directions = [
            "North", "North-Northeast", "Northeast", "East-Northeast",
            "East", "East-Southeast", "Southeast", "South-Southeast",
            "South", "South-Southwest", "Southwest", "West-Southwest",
            "West", "West-Northwest", "Northwest", "North-Northwest"
        ]
        
        index = round(bearing / 22.5) % 16
        return directions[index]
    
    def _get_region_info(self, lat: float, lon: float) -> dict:
        """Get basic region information based on coordinates"""
        region_info = {
            "hemisphere": "Northern" if lat >= 0 else "Southern",
            "longitude_zone": "Eastern" if lon >= 0 else "Western"
        }
        
        # Basic Indian subcontinent check
        if 6 <= lat <= 37 and 68 <= lon <= 97:
            region_info["region"] = "Indian Subcontinent"
            
            # Rough state identification for India
            if 8 <= lat <= 13 and 76 <= lon <= 80:
                region_info["likely_state"] = "Tamil Nadu/Karnataka"
            elif 19 <= lat <= 24 and 72 <= lon <= 75:
                region_info["likely_state"] = "Maharashtra"
            elif 28 <= lat <= 31 and 76 <= lon <= 78:
                region_info["likely_state"] = "Delhi/Haryana"
            elif 22 <= lat <= 26 and 88 <= lon <= 92:
                region_info["likely_state"] = "West Bengal"
        
        return region_info


class DataProcessingTool(BaseTool):
    name: str = "data_processing_tool"
    description: str = "Processes raw train data into structured format. Input: raw train data as JSON string"
    
    def _run(self, input_data: str) -> str:
        try:
            # Parse input
            if isinstance(input_data, str):
                try:
                    # Handle potential escaping issues
                    cleaned_input = input_data.strip()
                    if cleaned_input.startswith('"') and cleaned_input.endswith('"'):
                        cleaned_input = cleaned_input[1:-1]
                    cleaned_input = cleaned_input.replace('\\"', '"').replace("\\'", "'")
                    
                    parsed_data = json.loads(cleaned_input)
                except json.JSONDecodeError:
                    return json.dumps({"error": "Could not parse input data"})
            else:
                parsed_data = input_data
            
            if not isinstance(parsed_data, dict):
                return json.dumps({"error": "Invalid input format"})
            
            # Check if this is an error response
            if "error" in parsed_data:
                return json.dumps({
                    "error": parsed_data["error"],
                    "processed": False
                })
            
            # Extract train information
            train_number = parsed_data.get("train_number", "Unknown")
            train_name = parsed_data.get("train_name", f"Train {train_number}")
            current_station = parsed_data.get("current_station", "Unknown Location")
            
            # Calculate delay
            delay_minutes = 0
            status_category = "Unknown"
            status_emoji = "🔍"
            
            scheduled_arrival = parsed_data.get("scheduled_arrival")
            actual_arrival = parsed_data.get("actual_arrival")
            
            if scheduled_arrival and actual_arrival:
                try:
                    scheduled_time = datetime.fromisoformat(scheduled_arrival.replace('Z', '+00:00'))
                    actual_time = datetime.fromisoformat(actual_arrival.replace('Z', '+00:00'))
                    
                    time_diff = actual_time - scheduled_time
                    delay_minutes = int(time_diff.total_seconds() / 60)
                    
                    # Determine status category
                    if delay_minutes <= 0:
                        status_category = "On Time"
                        status_emoji = "✅"
                    elif delay_minutes <= 15:
                        status_category = "Slightly Delayed"
                        status_emoji = "🟡"
                    elif delay_minutes <= 60:
                        status_category = "Delayed"
                        status_emoji = "🟠"
                    else:
                        status_category = "Significantly Delayed"
                        status_emoji = "🔴"
                        
                except Exception:
                    delay_minutes = 0
                    status_category = "Status Unknown"
                    status_emoji = "❓"
            
            # Process location data
            current_location = {
                "station": current_station,
                "lat": parsed_data.get("current_lat", 0.0),
                "lon": parsed_data.get("current_lon", 0.0)
            }
            
            # Process upcoming stations
            upcoming_stations = parsed_data.get("upcoming_stations", [])
            if not isinstance(upcoming_stations, list):
                upcoming_stations = []
            
            # Calculate reliability score
            reliability_score = self._calculate_reliability_score(parsed_data, delay_minutes)
            
            # Structure the processed data
            processed_data = {
                "train_info": {
                    "number": train_number,
                    "name": train_name
                },
                "status": {
                    "category": status_category,
                    "emoji": status_emoji,
                    "delay_minutes": delay_minutes,
                    "delay_text": self._format_delay_text(delay_minutes)
                },
                "current_location": current_location,
                "next_stations": upcoming_stations[:3],  # Limit to next 3 stations
                "timing": {
                    "scheduled_arrival": scheduled_arrival,
                    "actual_arrival": actual_arrival,
                    "last_updated": parsed_data.get("last_updated", datetime.now().isoformat())
                },
                "reliability_score": reliability_score,
                "data_source": parsed_data.get("data_source", "unknown"),
                "processed_at": datetime.now().isoformat()
            }
            
            # Add note if using mock data
            if parsed_data.get("note"):
                processed_data["note"] = parsed_data["note"]
            
            return json.dumps(processed_data)
            
        except Exception as e:
            return json.dumps({"error": f"Data processing failed: {str(e)}"})
    
    def _calculate_reliability_score(self, raw_data: dict, delay_minutes: int) -> float:
        """Calculate reliability score based on various factors"""
        score = 100.0
        
        # Deduct points for delays
        if delay_minutes > 0:
            score -= min(delay_minutes * 0.5, 30)  # Max 30 points deduction for delays
        
        # Deduct points if using mock data
        if raw_data.get("data_source") == "mock_data":
            score -= 20
        
        # Deduct points if location is unknown
        if raw_data.get("current_station") == "Information not available":
            score -= 15
        
        # Ensure score is between 0 and 100
        return max(0.0, min(100.0, round(score, 1)))
    
    def _format_delay_text(self, delay_minutes: int) -> str:
        """Format delay into human-readable text"""
        if delay_minutes <= 0:
            return "On time"
        elif delay_minutes < 60:
            return f"{delay_minutes} minutes late"
        else:
            hours = delay_minutes // 60
            minutes = delay_minutes % 60
            if minutes == 0:
                return f"{hours} hour{'s' if hours > 1 else ''} late"
            else:
                return f"{hours}h {minutes}m late"


class ResponseGeneratorTool(BaseTool):
    name: str = "response_generator_tool"
    description: str = "Generates user-friendly responses from processed train data. Input: processed data as JSON string"
    
    def _run(self, input_data: str) -> str:
        try:
            # Parse input
            if isinstance(input_data, str):
                try:
                    # Handle potential escaping issues
                    cleaned_input = input_data.strip()
                    if cleaned_input.startswith('"') and cleaned_input.endswith('"'):
                        cleaned_input = cleaned_input[1:-1]
                    cleaned_input = cleaned_input.replace('\\"', '"').replace("\\'", "'")
                    
                    parsed_data = json.loads(cleaned_input)
                except json.JSONDecodeError:
                    return json.dumps({"error": "Could not parse input data"})
            else:
                parsed_data = input_data
            
            if not isinstance(parsed_data, dict):
                return json.dumps({"error": "Invalid input format"})
            
            # Check if this is an error response
            if "error" in parsed_data:
                return json.dumps({
                    "success": False,
                    "message": f"❌ Error: {parsed_data['error']}",
                    "error": parsed_data["error"]
                })
            
            # Extract processed data
            train_info = parsed_data.get("train_info", {})
            status = parsed_data.get("status", {})
            current_location = parsed_data.get("current_location", {})
            next_stations = parsed_data.get("next_stations", [])
            timing = parsed_data.get("timing", {})
            reliability_score = parsed_data.get("reliability_score", 0)
            data_source = parsed_data.get("data_source", "unknown")
            
            # Generate main response message
            response_lines = []
            
            # Header with train info
            train_number = train_info.get("number", "Unknown")
            train_name = train_info.get("name", f"Train {train_number}")
            response_lines.append(f"🚂 **{train_name}** (#{train_number})")
            
            # Status line
            status_emoji = status.get("emoji", "🔍")
            status_category = status.get("category", "Unknown")
            delay_text = status.get("delay_text", "Status unknown")
            response_lines.append(f"{status_emoji} **Status:** {status_category}")
            response_lines.append(f"⏱️ **Timing:** {delay_text}")
            
            # Current location
            current_station = current_location.get("station", "Unknown location")
            response_lines.append(f"📍 **Current Location:** {current_station}")
            
            # Next stations if available
            if next_stations and len(next_stations) > 0:
                response_lines.append(f"🎯 **Upcoming Stations:** {', '.join(next_stations[:3])}")
            
            # Data reliability
            reliability_emoji = "🟢" if reliability_score >= 80 else "🟡" if reliability_score >= 60 else "🔴"
            response_lines.append(f"{reliability_emoji} **Reliability Score:** {reliability_score}%")
            
            # Data source info
            if data_source == "mock_data":
                response_lines.append("ℹ️ *Using demonstration data*")
            elif data_source == "cache":
                response_lines.append("💾 *Data from cache*")
            elif data_source == "web_search":
                response_lines.append("🌐 *Data from web search*")
            
            # Last updated
            last_updated = timing.get("last_updated")
            if last_updated:
                try:
                    update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    formatted_time = update_time.strftime("%H:%M on %Y-%m-%d")
                    response_lines.append(f"🕐 **Last Updated:** {formatted_time}")
                except Exception:
                    pass
            
            # Join all lines
            response_message = "\n".join(response_lines)
            
            # Create summary data
            summary_data = {
                "train": f"{train_name} (#{train_number})",
                "status": status_category,
                "delay": status.get("delay_minutes", 0),
                "location": current_station,
                "reliability": reliability_score,
                "data_source": data_source
            }
            
            # Add special note if available
            note = parsed_data.get("note")
            if note:
                response_message += f"\n\n📝 **Note:** {note}"
            
            return json.dumps({
                "success": True,
                "message": response_message,
                "summary": summary_data,
                "response_data": parsed_data
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"❌ Response generation failed: {str(e)}",
                "error": str(e)
            })


class ErrorHandlingTool(BaseTool):
    name: str = "error_handling_tool"
    description: str = "Handles errors and provides helpful guidance. Input: error context as JSON string"
    
    def _run(self, input_data: str) -> str:
        try:
            # Parse input
            if isinstance(input_data, str):
                try:
                    # Handle potential escaping issues
                    cleaned_input = input_data.strip()
                    if cleaned_input.startswith('"') and cleaned_input.endswith('"'):
                        cleaned_input = cleaned_input[1:-1]
                    cleaned_input = cleaned_input.replace('\\"', '"').replace("\\'", "'")
                    
                    parsed_data = json.loads(cleaned_input)
                except json.JSONDecodeError:
                    # If we can't parse the error data, create a basic error response
                    parsed_data = {
                        "error_type": "parsing",
                        "error_message": "Could not parse error context"
                    }
            else:
                parsed_data = input_data if isinstance(input_data, dict) else {}
            
            error_type = parsed_data.get("error_type", "unknown")
            error_message = parsed_data.get("error_message", "Unknown error occurred")
            
            # Generate appropriate error response based on error type
            suggestions = []
            retry_recommended = False
            
            if error_type == "validation":
                suggestions = [
                    "Check that the train number is exactly 5 digits",
                    "Ensure date is in YYYY-MM-DD format",
                    "Verify that the date is not in the past",
                    "Try with today's date if no specific date is needed"
                ]
                retry_recommended = True
                
            elif error_type == "api" or error_type == "network":
                suggestions = [
                    "Check your internet connection",
                    "Try again in a few moments",
                    "The railway data service might be temporarily unavailable",
                    "Consider trying with a different train number"
                ]
                retry_recommended = True
                
            elif error_type == "processing":
                suggestions = [
                    "The train data might be incomplete",
                    "Try with a different train number",
                    "Check if the train number is correct",
                    "Some trains might not have real-time tracking"
                ]
                retry_recommended = True
                
            elif error_type == "execution":
                suggestions = [
                    "There was a system error during processing",
                    "Try the request again",
                    "If the problem persists, contact support",
                    "Check that all required services are running"
                ]
                retry_recommended = True
                
            else:
                suggestions = [
                    "An unexpected error occurred",
                    "Try the request again",
                    "Check your input parameters",
                    "Contact support if the problem persists"
                ]
                retry_recommended = False
            
            # Create error response
            error_response = {
                "error_type": error_type,
                "message": f"Error in {error_type}: {error_message}",
                "suggestions": suggestions,
                "retry_recommended": retry_recommended,
                "handled_at": datetime.now().isoformat()
            }
            
            return json.dumps(error_response)
            
        except Exception as e:
            # Fallback error handling
            return json.dumps({
                "error_type": "error_handler_failure",
                "message": f"Error handler itself failed: {str(e)}",
                "suggestions": [
                    "Critical system error occurred",
                    "Please contact technical support",
                    "Try restarting the application"
                ],
                "retry_recommended": False,
                "handled_at": datetime.now().isoformat()
            })
