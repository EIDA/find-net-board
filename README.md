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

- Connect to your MySQL server to create the database and a user:
  ```bash
  mysql -u root -p
  ```
  Execute the below commands in mysql shell:
  ```sql
  CREATE DATABASE networks_tests;
  CREATE USER 'netstests'@'DBHOST' IDENTIFIED BY 'netstests';
  GRANT CREATE ON *.* TO `netstests`@`DBHOST`;
  GRANT SELECT, INSERT, UPDATE, DELETE, DROP, REFERENCES, ALTER ON `networks_tests`.* TO `netstests`@`DBHOST`;
  GRANT ALL PRIVILEGES ON `test_networks_tests`.* TO `netstests`@`DBHOST`;
  exit
  ```
  **Note:** You need to replace `DBHOST` with the IP of your system as the Docker container, which will hold the application, will see it. Also, make sure you have configured your database to be accessible through this IP.

- From within the project folder build the Docker image:
  ```bash
  docker build --network host -t networkstests .
  ```
  **Note:** Look in the [Dockerfile](https://github.com/EIDA/find-net-board/blob/main/Dockerfile) and make sure to use credentials for the new admin user that do not already exist. If you already have made an admin user (e.g. by having built the image again before) and do not want to make a new one, you can delete the command:
  ```
  RUN python manage.py shell -c "from django.contrib.auth.models import User; \
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword')"
  ```
  If this is the first time you install the application, you can ignore the above note.

- Run the Docker container:
  ```bash
  docker run --network host -p 8000:8000 networkstests
  ```

### Step by step (ideal for development purposes)

Follow the steps below from within project folder to locally install the application:

- Install dependencies (recommended way using [Poetry](https://python-poetry.org/)):
  ```bash
  # create a virtual environment and activate it
  poetry shell
  # install dependencies
  poetry install
  ```

- Connect to your MySQL server to create the database and a user:
  ```bash
  mysql -u root -p
  ```
  Execute the below commands in mysql shell:
  ```sql
  CREATE DATABASE networks_tests;
  CREATE USER 'netstests'@'localhost' IDENTIFIED BY 'netstests';
  GRANT CREATE ON *.* TO `netstests`@`localhost`;
  GRANT SELECT, INSERT, UPDATE, DELETE, DROP, REFERENCES, ALTER ON `networks_tests`.* TO `netstests`@`localhost`;
  GRANT ALL PRIVILEGES ON `test_networks_tests`.* TO `netstests`@`localhost`;
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
  Update might take around 45 minutes and running the tests around 1 hour and 15 minutes.

- Visit http://localhost:8000/board/ to view the board that presents the results of the tests.
  When the page loads, the last set of tests is shown. You can use the search form to view specific tests.

- Visit http://localhost:8000/board/tests/ to view the available test runs.

- Visit http://localhost:8000/board/datacenter/datacenter_name/ to view results of tests for networks of a specific datacenter (replace *datacenter_name* with the name of your datacenter as it appears in https://www.fdsn.org/datacenters/). You can use the search form to view tests within a specific time frame.
