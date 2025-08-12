# Running the Service

## Development Environment Setup
1. Install Python 3.9 or above https://www.python.org/downloads/macos/

2. Open a terminal and navigate to the root of the repository (e.g., where the `service/` folder lives).

3. Create a new virtual environment named 'venv': `python -m venv venv`

4. Activate the virtual environment by running the following command in linux: `source venv/bin/activate`. In windows, the command is `venv\Scripts\activate`

5. Install the required dependencies:
```
cd service
pip install -r requirements_dev.txt
```

6. Install the package:
```bash
pip install -e .
```

7. Set the following environment variable:
   - on Windows (CMD):
        ```bash 
        set PYTHONPATH=%PYTHONPATH%;C:\Your\Project\Root
        set ENV=development
        ```
   - on macOS/Linux:
     ```bash 
     export PYTHONPATH=$PYTHONPATH:$(pwd)
     export ENV=development
     ```

    For production build, please change value of ENV to 'production'

## Starting the Service
1. From the root of the repository, navigate to the service directory: `cd service`
3. Run the application: `python app.py manage run`

> The FastAPI service should now be running at http://localhost:5000.

