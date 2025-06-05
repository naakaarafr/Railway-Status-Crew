# Railway Status Crew

Railway Status Crew is an AI-powered system designed to fetch live train status updates using Google Gemini AI and CrewAI. Developed by naakaarafr, this project leverages a crew of specialized AI agents to process user queries, fetch real-time data, perform geospatial calculations, and deliver user-friendly responses about train locations, delays, and upcoming stations.

## Features

- **Real-Time Train Status**: Retrieve up-to-date information on train locations, delays, and status.
- **Input Validation**: Ensures train numbers are 5 digits and dates are in the correct format (YYYY-MM-DD).
- **API Integration**: Fetches data from railway APIs or uses web search with caching for efficiency.
- **Geospatial Calculations**: Computes distances, directions, and speeds using mathematical formulas like Haversine.
- **User-Friendly Responses**: Presents train status in an easy-to-read format with emojis and summaries.
- **Robust Error Handling**: Gracefully manages errors with helpful suggestions and guidance.
- **Interactive Mode**: Allows continuous querying without restarting the application.

## Installation

Follow these steps to set up the project on your local machine:

### 1. Clone the Repository

```bash
git clone https://github.com/naakaarafr/railway-status-crew.git
cd railway-status-crew
```

### 2. Install Dependencies

Ensure you have Python 3.8+ installed, then run:

```bash
pip install -r requirements.txt
```

Required packages include `crewai`, `langchain-google-genai`, `python-dotenv`, and others listed in requirements.txt.

### 3. Set Up Environment Variables

Create a `.env` file in the project root and add your API keys:

```env
GOOGLE_API_KEY=your_gemini_api_key
SERPER_API_KEY=your_serper_api_key
```

- `GOOGLE_API_KEY` is required for Gemini AI functionality.
- `SERPER_API_KEY` is optional for web search; mock data is used if not provided.

## Configuration

The project uses `config.py` to manage settings:

- **Gemini API Key**: Powers the AI agents via the Google Gemini model.
- **Serper API Key**: Enables web search for train status data.
- **Model Parameters**: Configures the AI model with a temperature of 0.1 and max tokens of 1000.

To check the configuration status, run:

```bash
python main.py info
```

## Usage

Run the application via the command-line interface with the following syntax:

```bash
python main.py <command> [arguments]
```

### Available Commands

#### `status <train_number> [date]`
Fetch live train status.

**Examples:**
```bash
python main.py status 12345
python main.py status 12345 2024-12-25
```

#### `info`
Display system and crew information.

**Example:**
```bash
python main.py info
```

#### `health`
Perform a system health check.

**Example:**
```bash
python main.py health
```

#### `interactive`
Enter interactive mode for multiple queries.

**Example:**
```bash
python main.py interactive
```

#### `quick <train_number> [date]`
Quick utility for status checks.

**Example:**
```bash
python main.py quick 12345
```

#### `help`
Show available commands and usage.

**Example:**
```bash
python main.py help
```

### Notes

- Train numbers must be exactly 5 digits.
- Dates (optional) must be in YYYY-MM-DD format; defaults to today if omitted.

## How It Works

The system operates using a crew of AI agents, each with a specific role, managed by the `RailwayStatusCrew` class in `crew.py`. Here's an overview of the components:

### Agents (`agents.py`)

- **User Input Handler**: Validates train numbers and dates.
- **API Integration Specialist**: Fetches data from railway APIs or web searches.
- **Data Processing Expert**: Structures raw data into usable formats.
- **Geospatial Calculator**: Performs distance and direction calculations.
- **Response Generator**: Creates user-friendly responses.
- **Error Handler**: Manages errors with helpful feedback.

### Tools (`tools.py`)

- **TrainValidationTool**: Checks train number and date validity.
- **RailwayAPITool**: Retrieves train status data with caching.
- **GeospatialTool**: Calculates distances and bearings.
- **DataProcessingTool**: Processes raw data with delay and reliability metrics.
- **ResponseGeneratorTool**: Formats responses with emojis.
- **ErrorHandlingTool**: Provides error messages and suggestions.

### Tasks (`tasks.py`)

Tasks are executed sequentially:

1. Validate user input.
2. Fetch API data.
3. Process the data.
4. Perform geospatial calculations (if coordinates are available).
5. Generate a response.
6. Handle errors (triggered as needed).

### Workflow

1. **Input**: User provides a train number and optional date.
2. **Validation**: Input is checked for correctness.
3. **Data Fetching**: Real-time data is retrieved or mock data is used.
4. **Processing**: Data is structured and analyzed.
5. **Output**: A formatted response is delivered to the user.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository: https://github.com/naakaarafr/railway-status-crew.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m 'Add your feature'`.
4. Push to the branch: `git push origin feature/your-feature`.
5. Open a pull request.

Please ensure your code follows the project's style and includes tests where applicable.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

- **Developer**: naakaarafr
- **Technologies**: Powered by CrewAI and Google Gemini AI.
- **Inspiration**: Built to simplify access to real-time train information for Indian Railways users.

---

Feel free to reach out to naakaarafr via GitHub for questions or support!
