# video-labeling-backend

## Running the FastAPI server

With auto-reloading: `uvicorn main:app --reload`

## Running the Postgres Database

Initializing database for the first time and create a bind mounted Docker volume named `viva-volume`:

`docker volume create viva-volume`

`docker run --rm --name vivadb -v viva-volume:/var/lib/postgresql/data -e POSTGRES_PASSWORD=viva -p 5432:5432 -d postgres:latest`


Connect to an already running postgres container: `docker exec -it vivadb bash`

Or via psql: `docker exec -it vivadb psql -U postgres`

Though I also installed [DBeaver](https://dbeaver.io/) to create the tables and columns

## Helpful Docker commands for me

`docker container ls`

`docker container stop <container-name>`

`docker rm <container-name>`

`docker volume prune`

