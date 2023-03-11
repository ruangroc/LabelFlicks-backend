# video-labeling-backend

## Running the FastAPI server

With auto-reloading: `uvicorn main:app --port=5000 --reload`

To test endpoints, I can go to `localhost:5000/docs` and use the `Try it out` feature

Note: the Svelte + Electron UI uses localhost:8000 by default.

## Running the Postgres Database

Initializing database for the first time and create a bind mounted Docker volume named `viva-volume`:

`docker volume create viva-volume`

`docker run --rm --name vivadb -v viva-volume:/var/lib/postgresql/data -e POSTGRES_PASSWORD=viva -p 5432:5432 -d postgres:latest`

If creating a database for testing, use: `docker run --rm --name testdb -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:latest`

The .env file should contain the database URLs to select between and whether it's a test environment or not in addition to the Azure URLs (if using Azure blob storage.)

```
AZURE_STORAGE_CONNECTION_STRING="..."
AZURE_ACCOUNT_URL="..."
TEST_ENVIRONMENT="TRUE"
POSTGRES_TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
POSTGRES_DEV_DATABASE_URL ="postgresql://postgres:viva@localhost:5432/postgres"
```

Connect to an already running postgres container: `docker exec -it vivadb bash`

Or via psql: `docker exec -it vivadb psql -U postgres`

Though I also installed [DBeaver](https://dbeaver.io/) to create the tables and columns

## Helpful Docker commands for me

`docker container ls`

`docker container stop <container-name>`

`docker rm <container-name>`

`docker volume prune`

