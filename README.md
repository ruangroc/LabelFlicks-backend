# video-labeling-backend

## Instructions for running the server

### Step 1: Database setup

If you want to save a copy of the data attached to this container, create a Docker volume (I'm naming it "viva-volume"): `docker volume create viva-volume`

Start running a Docker container for the PostgreSQL database with the volume attached: `docker run --rm --name vivadb -v viva-volume:/var/lib/postgresql/data -e POSTGRES_PASSWORD=viva -p 5432:5432 -d postgres:latest`

Note: to see a visual representation of the database, I recommend installing [DBeaver](https://dbeaver.io/).

### Step 2: Create `.env` file

The `.env` file will look something like this:

```
AZURE_STORAGE_CONNECTION_STRING="..."
AZURE_ACCOUNT_URL="..."
POSTGRES_DEV_DATABASE_URL ="postgresql://postgres:viva@localhost:5432/postgres"
```

Note: the Azure lines are only required if you want the server to store uploaded videos and images to your Azure blob storage account. Otherwise, leave those lines out of the `.env` file and the server will default to storing content in the local file storage system.

### Step 3: Start the FastAPI server

Make sure the virtualenv is activated: `. venv/Scripts/activate` or `. venv/bin/activate`

To start the server with auto-reloading capability (restart upon detecting changes): `uvicorn main:app --port=5000 --reload`

To start the server without auto-reloading: `uvicorn main:app --port=5000`

Note: the Svelte + Electron frontend client uses localhost:8000 by default so we're running the server on port 5000 to avoid clashes.

### Step 4: See the endpoints in action

In your web browser of choice, go to: `localhost:5000/docs`

There should be Swagger docs for each FastAPI endpoint that each come with a `Try it out` feature that lets you test the endpoints.



## Instructions for running the unit and integration tests

### Step 1: Database setup

Create a database for testing that's separate from the development database (this one is named "testdb"): `docker run --rm --name testdb -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:latest`

### Step 2: Create `.env` file

The `.env` file will look something like this:

```
TEST_ENVIRONMENT="TRUE"
POSTGRES_TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
```

Note: it's fine to use the same `.env` file in the previous section, just make sure that `TEST_ENVIRONMENT` is set to the value you want before you run the tests or the server.

### Step 3: Run the tests

Make sure the virtualenv is activated: `. venv/Scripts/activate` or `. venv/bin/activate`

Then start the tests using this command: `pytest`


## Miscellaneous notes and useful commands for development

I use [Docker Desktop](https://www.docker.com/products/docker-desktop/) to manage most of my Docker stuff, but the following CLI commands are still handy to know.

List all containers: `docker container ls`

Stop running a named container: `docker container stop <container-name>`

Remove a named container: `docker rm <container-name>`

Remove old volumes: `docker volume prune`

Connect to a running Postgres Docker container: `docker exec -it vivadb bash`

Connect to a Postgres database within a Docker container using psql: `docker exec -it vivadb psql -U postgres`

