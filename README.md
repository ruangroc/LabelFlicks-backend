# LabelFlicks Server

The LabelFlicks Server is the backend component for the overall LabelFlicks project, which aims to improve the process of converting videos into fully-labeled object detection datasets for training computer vision models.

The LabelFlicks backend server accepts MP4 videos, breaks them down into per-second frames (JPG images), applies the Ultralytics YOLOv8 object detection model to generate bounding boxes and initial predictions, and trains a small neural network on human-reviewed bounding boxes and labels to re-predict the labels of unreviewed bounding boxes when the client requests it. 

The main assumption here is that modern, pre-trained object detection models are good enough that they will automatically detect most objects in an image and that only the labels would need to change to match what a user wants to label for. This is why the label prediction model spun up by the server upon request can be a smaller, fully-connected network that can be trained and used quickly within a human-in-the-loop workflow.

The LabelFlicks server was built using FastAPI and a Docker instance of a PostgreSQL database. The intended frontend client can be found in the [video-labeling-electron](https://github.com/ruangroc/video-labeling-electron) repo.

## Getting Started

### Step 1: Set up the database

You will first want to get an instance of a PostgreSQL database running. I chose to use the latest [postgres Docker image](https://hub.docker.com/_/postgres/).

If you want to save a copy of the data attached to this container, you can create a Docker volume:
```
docker volume create <your-volume-name>
```

Then start the Docker instance with the volume attached: 
```
docker run --rm --name <your-instance-name> -v <your-volume-name>:/var/lib/postgresql/data -e POSTGRES_PASSWORD=<your-postgres-password> -p 5432:5432 -d postgres:latest
```

If you don't care to access the data in your database later (i.e. after you stop the Docker instance), you can start the instance without the volume attached:
```
docker run --rm --name <your-instance-name> -e POSTGRES_PASSWORD=<your-postgres-password> -p 5432:5432 -d postgres:latest
```

If you do attach a volume and you want to see a visual representation of the database at some point, I recommend installing [DBeaver](https://dbeaver.io/). I also recommend using [Docker Desktop](https://www.docker.com/products/docker-desktop/) to manage your Docker instances and volumes.

### Step 2: Create the `.env` file

The `.env` file should contain at least these three environment variables:
```
TEST_ENVIRONMENT=<"TRUE" or "FALSE">
POSTGRES_TEST_DATABASE_URL=<your postgres test database connection string>
POSTGRES_DEV_DATABASE_URL=<your postgres dev database connection string>
```

The postgres connection strings will likely have the format: `postgresql://postgres:<postgres-password>@localhost:5432/postgres`

### Step 3: Set up the virtual environment

Create a virtual environment if you have not yet done so:
```
virtualenv venv
```

Activate the virtual environment:
```
// Windows version:
. venv/Scripts/activate

// Unix version:
. venv/bin/activate
```

Install dependencies if you have not yet done so:
```
pip install -r requirements.txt
```

### Step 4: Start the FastAPI server

Start the FastAPI server:
```
uvicorn main:app --port=5000 --reload
```

If you do not want the auto-reloading capability, which restarts the server upon detecting changes to your code, then exclude the `--reload` flag.

Note: the LabelFlicks frontend client uses localhost:8000 by default so we're running the server on port 5000 to avoid clashes. If you decide to change the frontend default port instead, you can exclude the `--port=5000` parameter here.

### Step 5: See the endpoints in action

If you simply want to learn more about the server, simply navigate to `localhost:5000/docs` in your web browser of choice. There will be Swagger docs for each FastAPI endpoint and each one comes with a `Try it out` feature that lets you test the endpoints.

If you want to see the full LabelFlicks application in motion, follow the instructions in the [video-labeling-electron](https://github.com/ruangroc/video-labeling-electron) README file.

## Tests

1. You will follow steps 1 through 3 in the Getting Started instructions.

2. Run the tests using: `pytest`

