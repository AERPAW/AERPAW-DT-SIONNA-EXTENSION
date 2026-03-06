### Sionna Interface for AERPAW Digital Twin

This tool provides fastAPI endpoints, a sionna wrapper and controller system that act together to provide following functionality:
- Load scene
- Reset
- Add, update, remove Transmitter/Receiver
- calculate paths and CIR

For api reference, refer to schemas.py or FastAPI docs. 

#### Setup
##### Basic Setup
To get the repository up and running:
1) Clone this repository: `git clone git@github.com:AERPAW/AERPAW-DT-SIONNA-EXTENSION.git`
2) Go to the directory: `cd aerpaw_sionna`
3) Create a virtual environment and activate it: `python -m venv venv && source venv/bin/activate`
4) Install the required dependencies: `pip install -r requirements.txt`
5) Go into src/ and run the application: `cd src && uvicorn app:app --reload`

##### Docker 
To run the code with docker, after cloning the repository, run the following:
1) `sudo docker compose up --build`
2) Go to `http://127.0.0.1:8000/docs` for testing and reference documentation

Relevant files:
scenes/ -- contains the scenes that can be loaded (not tested with custom scenes right now)
app.py -- API endpoints
main.py -- orchestration and business logic
siona_wrapper.py -- wrapper class to sionna providing core functionality
schemas.py -- schemas (pydantic) for API 
utils.py -- utility functions and enum classes
Docker-compose and Dockerfile -- Docker setup and configuration
