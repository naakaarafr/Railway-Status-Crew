#!/usr/bin/env python3
"""
Railway Status Crew - Main Application
A CrewAI-powered system for fetching live train status using Google Gemini AI.
"""

import sys
import argparse
from datetime import datetime
from crew import create_railway_crew, quick_status_check


def print_banner():
    """Print application banner"""
    banner = """
    🚂 Railway Status Crew - Powered by Gemini AI
    =============================================
    Intelligent train status tracking using CrewAI
    """
    print(banner)


def print_help():
    """Print help information"""
    help_text = """
    Available Commands:
    
    1. Get Train Status:
       python main.py status <train_number> [date]
       Example: python main.py status 12345
       Example: python main.py status 12345 2024-12-25
    
    2. System Information:
       python main.py info
    
    3. Health Check:
       python main.py health
    
    4. Interactive Mode:
       python main.py interactive
    
    5. Quick Status (Utility):
       python main.py quick <train_number> [date]
    
    Train Number: Must be exactly 5 digits
    Date Format: YYYY-MM-DD (optional, defaults to today)
    """
    print(help_text)


def get_train_status_command(train_number, date=None):
    """Handle train status command"""
    print(f"🔍 Fetching status for Train {train_number}")
    if date:
        print(f"📅 Date: {date}")
    
    try:
        crew = create_railway_crew()
        result = crew.get_train_status(train_number, date)
        
        print("\n" + "="*50)
        if result["success"]:
            print("✅ SUCCESS")
            print(result["message"])
            
            # Display additional data if available
            if "data" in result and isinstance(result["data"], dict):
                data = result["data"]
                if "summary" in data:
                    summary = data["summary"]
                    print(f"\n📊 Summary:")
                    print(f"   Train: {summary.get('train', 'N/A')}")
                    print(f"   Status: {summary.get('status', 'N/A')}")
                    print(f"   Delay: {summary.get('delay', 0)} minutes")
                    print(f"   Location: {summary.get('location', 'N/A')}")
        else:
            print("❌ FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
            if "error_details" in result:
                details = result["error_details"]
                if isinstance(details, dict) and "suggestions" in details:
                    print("\n💡 Suggestions:")
                    for suggestion in details["suggestions"]:
                        print(f"   • {suggestion}")
        
        print("="*50)
        
    except Exception as e:
        print(f"❌ Application error: {str(e)}")
        return False
    
    return True


def system_info_command():
    """Handle system info command"""
    print("📊 System Information")
    print("-" * 30)
    
    try:
        crew = create_railway_crew()
        info = crew.get_crew_info()
        
        print(f"Crew Name: {info['crew_name']}")
        print(f"LLM Model: {info['llm_model']}")
        print(f"Agents: {info['agents_count']}")
        print(f"Tasks: {info['tasks_count']}")
        print(f"Process: {info['process']}")
        
        print(f"\n🤖 Agents:")
        for agent in info['agents']:
            print(f"   • {agent['role']}")
            print(f"     Goal: {agent['goal'][:50]}...")
            print(f"     Tools: {', '.join(agent['tools'])}")
            print()
        
        print(f"⚙️ Configuration:")
        config = info['configuration']
        for key, value in config.items():
            print(f"   {key}: {value}")
        
        # Show supported operations
        operations = crew.get_supported_operations()
        print(f"\n🔧 Supported Operations:")
        for op in operations['primary_operations']:
            print(f"   • {op}")
            
    except Exception as e:
        print(f"❌ Failed to get system info: {str(e)}")
        return False
    
    return True


def health_check_command():
    """Handle health check command"""
    print("🏥 System Health Check")
    print("-" * 25)
    
    try:
        crew = create_railway_crew()
        health = crew.health_check()
        
        print(f"Overall Status: {health['crew_status'].upper()}")
        print(f"LLM Connection: {'✅ Connected' if health['llm_connection'] else '❌ Failed'}")
        
        print(f"\n🤖 Agents Status:")
        for agent in health['agents_status']:
            print(f"   • {agent['role']}: {agent['status']} ({agent['tools_count']} tools)")
        
        print(f"\n🔧 Tools Status:")
        for tool in health['tools_status']:
            print(f"   • {tool['name']}: {tool['status']}")
        
        if health['issues']:
            print(f"\n⚠️ Issues Found:")
            for issue in health['issues']:
                print(f"   • {issue}")
        else:
            print(f"\n✅ No issues found")
            
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False
    
    return True


def interactive_mode():
    """Handle interactive mode"""
    print("🔄 Interactive Mode - Type 'quit' to exit")
    print("-" * 40)
    
    while True:
        try:
            train_input = input("\n🚂 Enter train number (5 digits): ").strip()
            
            if train_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            date_input = input("📅 Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
            date_value = date_input if date_input else None
            
            print("\n" + "-"*30)
            success = get_train_status_command(train_input, date_value)
            
            if not success:
                continue_choice = input("\n🔄 Try again? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    break
                    
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error in interactive mode: {str(e)}")
            continue


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Railway Status Crew - AI-powered train status tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('command', nargs='?', 
                       choices=['status', 'info', 'health', 'interactive', 'quick', 'help'],
                       help='Command to execute')
    parser.add_argument('train_number', nargs='?', help='5-digit train number')
    parser.add_argument('date', nargs='?', help='Date in YYYY-MM-DD format')
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Handle no arguments or help command
    if not args.command or args.command == 'help':
        print_help()
        return
    
    # Route to appropriate command handler
    try:
        if args.command == 'status':
            if not args.train_number:
                print("❌ Error: Train number is required for status command")
                print("Usage: python main.py status <train_number> [date]")
                return
            
            get_train_status_command(args.train_number, args.date)
            
        elif args.command == 'quick':
            if not args.train_number:
                print("❌ Error: Train number is required for quick command")
                return
            
            print("⚡ Quick Status Check...")
            result = quick_status_check(args.train_number, args.date)
            print(f"Result: {result}")
            
        elif args.command == 'info':
            system_info_command()
            
        elif args.command == 'health':
            health_check_command()
            
        elif args.command == 'interactive':
            interactive_mode()
            
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
