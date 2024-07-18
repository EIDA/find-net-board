# find-net-board

This is an application that tests and presents the consistency of networks metadata of various sources.

## Installation

Clone current GitHub repository and enter project folder:
```bash
git clone https://github.com/EIDA/find-net-board.git
cd find-net-board
```

For production see the recommended option using [Docker](https://www.docker.com/) below. For development purposes see the step by step installation.

### With Docker containers (recommended)

- Connect to your PostgreSQL server to create the database and a role:
  ```bash
  psql -U postgres -h localhost
  ```
  Execute the below commands in psql shell:
  ```sql
  CREATE ROLE netstests WITH LOGIN PASSWORD 'netstests' CREATEDB;
  CREATE DATABASE networks_tests OWNER netstests;
  exit
  ```
  **Note:** You can use your own choices for role name, database name, password, host and port. Be sure to pass them through environment variables when running the docker container.

- From within the project folder, either build the Docker image:
  ```bash
  docker build --network host -t networkstests .
  ```
  or pull from [https://ghcr.io/eida/eida/find-net-board:main](https://ghcr.io/eida/eida/find-net-board:main).

- Run the Docker container:
  ```bash
  docker run --network host -p 8000:8000 networkstests
  ```
  **Note:** You might need to use you own names for database variables. The supported environment variables are:
   - NETSTESTS_DBNAME
   - NETSTESTS_DBUSER
   - NETSTESTS_DBPASSWORD
   - NETSTESTS_DBHOST
   - NETSTESTS_DBPORT

   Example:
   ```
   NETSTESTS_DBNAME=networks_tests NETSTESTS_DBUSER=netstests docker run --network host -p 8000:8000 networkstests
   ```

### Step by step (ideal for development purposes)

Follow the steps below from within the project folder to locally install the application:

- Install dependencies (recommended way using [Poetry](https://python-poetry.org/)):
  ```bash
  # create a virtual environment and activate it
  poetry shell
  # install dependencies
  poetry install
  ```

- Connect to your PostgreSQL server to create the database and a role:
  ```bash
  psql -U postgres -h localhost
  ```
  Execute the below commands in mysql shell:
  ```sql
  CREATE ROLE netstests WITH LOGIN PASSWORD 'netstests' CREATEDB;
  CREATE DATABASE networks_tests OWNER netstests;
  exit
  ```

- Go back to project folder with the virtual environment activated and build the database schema:
  ```bash
  python manage.py migrate
  ```

- Create and admin user for the application:
  ```bash
  python manage.py createsuperuser
  # enter desired username, email and password in the corresponding prompts
  # be sure to remember the username and password you are going to use
  ```

- Start the development server:
  ```bash
  python manage.py runserver
  ```
  **Note that deploying in a production web server might require more steps.**

- Schedule periodic tasks with [Celery](https://docs.celeryq.dev/en/stable/):
  ```bash
  celery -A netstests worker -B --loglevel=info
  ```

## Use

Provided that the application is up and running:

- Visit http://localhost:8000/admin/ to view the admin page.
  While at it you can click `Update DB from Sources` or `Run Tests` buttons to perform the corresponding tasks.
  Update might take around 30 minutes and running the tests around 40 minutes.

- Visit http://localhost:8000/board/ to view the board that presents the results of the tests.
  When the page loads, the last set of tests is shown. You can use the search form to view specific tests.

- Visit http://localhost:8000/board/tests/ to view the available test runs.

- Visit http://localhost:8000/board/datacenter/datacenter_name/ to view results of tests for networks of a specific datacenter (replace *datacenter_name* with the name of your datacenter as it appears in https://www.fdsn.org/datacenters/). You can use the search form to view tests within a specific time frame.

## Testing (for development purposes)

To run the tests and get `coverage` information, run the below command from within the project folder:
```bash
pytest --cov-report html
```

The report will be available in `htmlcov/index.html` file.


## Things pending

- A few `ruff` errors are still not addressed. Most of them could probably be ignored though.

- Test suite is quite poor and needs more meaningful tests to increase coverage percentage.

- Maybe a good idea could be to use class based views.
