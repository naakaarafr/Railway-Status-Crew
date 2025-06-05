from crewai import Crew, Process
from config import config
from agents import (
    user_input_agent,
    api_integration_agent,
    data_processing_agent,
    geospatial_agent,
    response_agent,
    error_handling_agent
)
from tasks import (
    validation_task,
    api_retrieval_task,
    data_processing_task,
    geospatial_task,
    response_generation_task,
    error_handling_task
)
import json
import logging
from datetime import datetime
import re


class RailwayStatusCrew:
    """
    Railway Status Crew for handling live train status queries using Gemini AI
    """
    
    def __init__(self):
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Display configuration status
        config.display_status()
        self.crew = self._create_crew()
    
    def _create_crew(self):
        """Create and configure the railway status crew with Gemini LLM"""
        
        return Crew(
            agents=[
                user_input_agent,
                api_integration_agent,
                data_processing_agent,
                geospatial_agent,
                response_agent,
                error_handling_agent
            ],
            tasks=[
                validation_task,
                api_retrieval_task,
                data_processing_task,
                geospatial_task,
                response_generation_task
            ],
            process=Process.sequential,
            verbose=True,
            memory=False,  # Disable memory to avoid external dependencies
            max_rpm=30,  # Rate limiting for API calls
            max_execution_time=120,  # Increased timeout for better reliability
            full_output=True,  # Get complete execution details
            step_callback=self._step_callback  # Optional callback for monitoring
        )
    
    def _step_callback(self, step_output):
        """Optional callback to monitor crew execution steps"""
        try:
            if hasattr(step_output, 'task') and hasattr(step_output, 'agent'):
                task_desc = str(step_output.task.description).split(':')[0] if step_output.task.description else "Unknown Task"
                agent_role = str(step_output.agent.role) if step_output.agent.role else "Unknown Agent"
                print(f"🔄 Completed: {task_desc} by {agent_role}")
        except Exception as e:
            self.logger.warning(f"Step callback error: {e}")
    
    def _sanitize_input(self, value):
        """Sanitize input to prevent string quote issues"""
        if isinstance(value, str):
            # Remove extra quotes and strip whitespace
            cleaned = value.strip().strip('"').strip("'")
            # Handle escaped quotes
            cleaned = cleaned.replace('\\"', '"').replace("\\'", "'")
            return cleaned
        return value
    
    def _prepare_inputs_as_dict(self, train_number, date):
        """Prepare inputs as a plain dictionary (no JSON serialization)"""
        return {
            "train_number": str(train_number),
            "date": str(date) if date else None,
            "request_id": f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        }
    
    def _validate_train_number(self, train_number):
        """Validate train number format"""
        if not train_number:
            return False, "Train number is required"
        
        # Clean the train number
        clean_number = self._sanitize_input(str(train_number))
        
        # Check if it's a valid 5-digit number
        if not clean_number.isdigit():
            return False, "Train number must contain only digits"
        
        if len(clean_number) != 5:
            return False, "Train number must be exactly 5 digits"
        
        return True, clean_number
    
    def _validate_date(self, date):
        """Validate date format"""
        if not date:
            return True, None  # Date is optional
        
        # Clean the date
        clean_date = self._sanitize_input(str(date))
        
        try:
            # Try to parse the date
            parsed_date = datetime.strptime(clean_date, "%Y-%m-%d")
            return True, clean_date
        except ValueError:
            return False, "Date must be in YYYY-MM-DD format"
    
    def get_train_status(self, train_number: str, date: str = None):
        """
        Get live train status for the given train number and date
        
        Args:
            train_number (str): 5-digit train number
            date (str, optional): Date in YYYY-MM-DD format
            
        Returns:
            dict: Train status information with success indicator
        """
        print(f"🚂 Processing train status request for Train {train_number}")
        if date:
            print(f"📅 Date: {date}")
        
        try:
            # Validate inputs
            is_valid_train, train_result = self._validate_train_number(train_number)
            if not is_valid_train:
                return {
                    "success": False,
                    "error": "validation_error",
                    "message": train_result,
                    "details": {"field": "train_number", "value": train_number}
                }
            
            is_valid_date, date_result = self._validate_date(date)
            if not is_valid_date:
                return {
                    "success": False,
                    "error": "validation_error",
                    "message": date_result,
                    "details": {"field": "date", "value": date}
                }
            
            # Prepare inputs as plain dictionary (avoid JSON serialization issues)
            inputs = self._prepare_inputs_as_dict(train_result, date_result)
            print(f"🔍 Prepared inputs: {inputs}")
            
            # Execute the crew with error handling
            print("⚡ Starting crew execution...")
            try:
                result = self.crew.kickoff(inputs=inputs)
                print("✅ Crew execution completed")
            except Exception as crew_error:
                print(f"❌ Crew execution failed: {str(crew_error)}")
                return self._handle_execution_error(str(crew_error), inputs)
            
            # Process the result
            try:
                processed_result = self._process_crew_result(result)
                print("✅ Result processing completed successfully")
                return processed_result
            except Exception as process_error:
                print(f"❌ Result processing failed: {str(process_error)}")
                return {
                    "success": False,
                    "error": "result_processing_error",
                    "message": f"Failed to process crew result: {str(process_error)}",
                    "raw_result": str(result)[:500]  # Truncate for safety
                }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Unexpected error: {error_msg}")
            self.logger.error(f"Unexpected error in get_train_status: {error_msg}")
            
            return {
                "success": False,
                "error": "unexpected_error",
                "message": f"An unexpected error occurred: {error_msg}",
                "details": {"train_number": train_number, "date": date}
            }
    
    def _handle_execution_error(self, error_message, original_inputs):
        """Handle execution errors with simplified approach"""
        try:
            print(f"🔧 Handling execution error: {error_message}")
            
            # Prepare simple error inputs as dictionary (no JSON)
            error_inputs = {
                "error_type": "execution_error",
                "error_message": str(error_message),
                "original_train_number": original_inputs.get("train_number", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
            
            # Try a simplified error handling approach
            try:
                # Create a minimal error crew
                error_crew = Crew(
                    agents=[error_handling_agent],
                    tasks=[error_handling_task],
                    verbose=False,
                    memory=False,
                    max_execution_time=30,
                    process=Process.sequential
                )
                
                error_result = error_crew.kickoff(inputs=error_inputs)
                
                return {
                    "success": False,
                    "error": "execution_error",
                    "error_message": error_message,
                    "error_details": self._extract_simple_result(error_result),
                    "message": "System error occurred. Please try again with a valid train number."
                }
                
            except Exception as error_crew_error:
                print(f"⚠️ Error crew also failed: {str(error_crew_error)}")
                # Return simple error response without error crew
                return self._create_fallback_error_response(error_message, original_inputs)
            
        except Exception as nested_error:
            nested_msg = str(nested_error)
            self.logger.error(f"Critical error in error handling: {nested_msg}")
            return self._create_fallback_error_response(error_message, original_inputs)
    
    def _create_fallback_error_response(self, error_message, original_inputs):
        """Create a simple fallback error response"""
        return {
            "success": False,
            "error": "system_error",
            "error_message": error_message,
            "message": f"Unable to process train status for train {original_inputs.get('train_number', 'unknown')}. Please verify the train number is a valid 5-digit number and try again.",
            "suggestions": [
                "Ensure train number is exactly 5 digits",
                "Check if the train number exists in the railway system",
                "Try again after a few moments",
                "Verify your internet connection"
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_simple_result(self, result):
        """Extract result in simple format without complex JSON parsing"""
        try:
            if hasattr(result, 'raw'):
                return str(result.raw)
            elif hasattr(result, 'output'):
                return str(result.output)
            else:
                return str(result)
        except Exception:
            return "Unable to extract result"
    
    def _process_crew_result(self, result):
        """Process and format the crew execution result with simplified approach"""
        try:
            # Extract raw data
            if hasattr(result, 'raw'):
                raw_data = result.raw
            elif hasattr(result, 'output'):
                raw_data = result.output
            else:
                raw_data = result
            
            # Handle different data types simply
            if isinstance(raw_data, dict):
                processed_data = raw_data
                message = raw_data.get("message", "Train status retrieved successfully")
            elif isinstance(raw_data, str):
                # Try to parse as JSON, but don't fail if it doesn't work
                try:
                    parsed_data = json.loads(raw_data)
                    if isinstance(parsed_data, dict):
                        processed_data = parsed_data
                        message = parsed_data.get("message", raw_data)
                    else:
                        processed_data = {"response": raw_data}
                        message = raw_data
                except json.JSONDecodeError:
                    # If JSON parsing fails, treat as plain text
                    processed_data = {"response": raw_data}
                    message = raw_data
            else:
                processed_data = {"response": str(raw_data)}
                message = str(raw_data)
            
            return {
                "success": True,
                "data": processed_data,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
                
        except Exception as e:
            error_msg = f"Result processing failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "error": "processing_error",
                "error_message": error_msg,
                "raw_result": str(result)[:500],  # Truncate for safety
                "timestamp": datetime.now().isoformat()
            }
    
    def get_crew_info(self):
        """Get information about the crew configuration"""
        try:
            return {
                "crew_name": "Railway Status Crew",
                "llm_model": "Gemini 2.0 Flash",
                "agents_count": len(self.crew.agents),
                "tasks_count": len(self.crew.tasks),
                "process": self.crew.process.value if hasattr(self.crew.process, 'value') else str(self.crew.process),
                "agents": [
                    {
                        "role": agent.role,
                        "goal": agent.goal,
                        "tools": [tool.name for tool in agent.tools] if agent.tools else []
                    }
                    for agent in self.crew.agents
                ],
                "tasks": [
                    {
                        "description": task.description.split('\n')[1].strip() if '\n' in task.description else task.description,
                        "agent": task.agent.role if task.agent else "Unassigned"
                    }
                    for task in self.crew.tasks
                ],
                "configuration": {
                    "max_rpm": getattr(self.crew, 'max_rpm', 'Not set'),
                    "max_execution_time": getattr(self.crew, 'max_execution_time', 'Not set'),
                    "memory_enabled": getattr(self.crew, 'memory', False),
                    "verbose": getattr(self.crew, 'verbose', False)
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": f"Failed to get crew info: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def health_check(self):
        """Perform a health check on the crew and its components"""
        health_status = {
            "crew_status": "healthy",
            "llm_connection": False,
            "agents_status": [],
            "tools_status": [],
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test LLM connection with proper error handling
            test_llm = config.get_llm()
            if test_llm:
                try:
                    test_response = test_llm.invoke("test connection")
                    health_status["llm_connection"] = True
                except Exception as llm_error:
                    health_status["issues"].append(f"LLM connection failed: {str(llm_error)}")
            else:
                health_status["issues"].append("LLM configuration not found")
            
            # Check each agent
            for agent in self.crew.agents:
                agent_health = {
                    "role": agent.role,
                    "status": "healthy",
                    "tools_count": len(agent.tools) if agent.tools else 0,
                    "has_goal": bool(agent.goal),
                    "has_backstory": bool(getattr(agent, 'backstory', None))
                }
                health_status["agents_status"].append(agent_health)
                
                # Check agent tools
                if agent.tools:
                    for tool in agent.tools:
                        tool_health = {
                            "name": getattr(tool, 'name', 'Unknown'),
                            "status": "healthy",
                            "type": type(tool).__name__
                        }
                        health_status["tools_status"].append(tool_health)
                        
        except Exception as e:
            health_status["crew_status"] = "unhealthy"
            health_status["issues"].append(f"Health check failed: {str(e)}")
            self.logger.error(f"Health check error: {str(e)}")
        
        return health_status
    
    def get_supported_operations(self):
        """Get list of supported operations"""
        return {
            "primary_operations": [
                "get_train_status",
                "validate_train_number",
                "fetch_live_data",
                "calculate_delays",
                "generate_user_response"
            ],
            "utility_operations": [
                "health_check",
                "get_crew_info",
                "error_handling"
            ],
            "supported_inputs": {
                "train_number": "5-digit string (required)",
                "date": "YYYY-MM-DD format (optional, defaults to today)"
            },
            "input_validation": {
                "train_number": "Must be exactly 5 digits",
                "date": "Must be valid date in YYYY-MM-DD format"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def test_simple_crew_execution(self, train_number="12622"):
        """Test crew execution with minimal complexity"""
        print(f"🧪 Testing simple crew execution with train {train_number}")
        
        # Create minimal inputs
        test_inputs = {
            "train_number": str(train_number),
            "test_mode": True,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Try to execute just the validation task
            print("Testing validation task...")
            validation_crew = Crew(
                agents=[user_input_agent],
                tasks=[validation_task],
                verbose=True,
                memory=False,
                max_execution_time=60,
                process=Process.sequential
            )
            
            result = validation_crew.kickoff(inputs=test_inputs)
            
            return {
                "success": True,
                "test_result": self._extract_simple_result(result),
                "message": "Simple crew execution test completed successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Simple crew execution test failed",
                "suggestions": [
                    "Check agent configurations",
                    "Verify task definitions",
                    "Check LLM connectivity",
                    "Review input format"
                ]
            }


# Factory function to create crew instance
def create_railway_crew():
    """Factory function to create a new railway crew instance"""
    try:
        return RailwayStatusCrew()
    except Exception as e:
        print(f"❌ Failed to create railway crew: {str(e)}")
        raise


# Utility function for quick status check
def quick_status_check(train_number: str, date: str = None):
    """Quick utility function to get train status"""
    try:
        crew = create_railway_crew()
        return crew.get_train_status(train_number, date)
    except Exception as e:
        return {
            "success": False,
            "error": "initialization_error",
            "message": f"Failed to initialize crew: {str(e)}"
        }


# Example usage and testing
if __name__ == "__main__":
    print("🚂 Railway Status Crew - Powered by Gemini AI")
    print("=" * 50)
    
    try:
        # Create crew instance
        railway_crew = create_railway_crew()
        
        # Display crew information
        print("\n📊 Crew Information:")
        crew_info = railway_crew.get_crew_info()
        if "error" not in crew_info:
            print(f"Model: {crew_info['llm_model']}")
            print(f"Agents: {crew_info['agents_count']}")
            print(f"Tasks: {crew_info['tasks_count']}")
        else:
            print(f"Error getting crew info: {crew_info['error']}")
        
        # Perform health check
        print("\n🏥 Health Check:")
        health = railway_crew.health_check()
        print(f"Status: {health['crew_status']}")
        print(f"LLM Connection: {'✅' if health['llm_connection'] else '❌'}")
        
        if health['issues']:
            print("Issues found:")
            for issue in health['issues']:
                print(f"  ⚠️ {issue}")
        
        # Test simple crew execution first
        print("\n🧪 Testing Simple Crew Execution:")
        simple_test = railway_crew.test_simple_crew_execution()
        if simple_test["success"]:
            print("✅ Simple execution test passed")
        else:
            print("❌ Simple execution test failed")
            print(f"Error: {simple_test['error']}")
        
        # Show supported operations
        print("\n⚙️ Supported Operations:")
        operations = railway_crew.get_supported_operations()
        for op in operations['primary_operations']:
            print(f"  • {op}")
        
        # Example query with proper validation
        print("\n🔍 Testing with example query...")
        test_train_number = "12622"
        print(f"Query: Train {test_train_number} for today")
        
        result = railway_crew.get_train_status(test_train_number)
        
        if result["success"]:
            print("✅ Query successful!")
            print(f"Response: {result.get('message', 'No message')}")
        else:
            print("❌ Query failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Message: {result.get('message', 'No message')}")
            if "suggestions" in result:
                print("Suggestions:")
                for suggestion in result["suggestions"]:
                    print(f"  • {suggestion}")
            
    except Exception as e:
        print(f"❌ Initialization failed: {str(e)}")
        print("Please check your configuration and API keys.")
        print("\nTroubleshooting tips:")
        print("1. Verify your Gemini API key is set correctly")
        print("2. Check that all required modules are imported")
        print("3. Ensure your agents and tasks are properly configured")
        print("4. Check network connectivity for API calls")
        print("5. Run the simple crew execution test first")