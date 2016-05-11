1) Install libraries

        pip install click, flask, sqlalchemy

2) Install postgres

       https://realpython.com/blog/python/flask-by-example-part-2-postgres-sqlalchemy-and-alembic/

3) Create Database Schema for running the application

       The postgres database must have the schema used for the application. Execute all CREATE TABLE commands in server.py to create the       schema to create the same schema in your database.

4) Configure Database access

       In server.py set the value of DATABASEURI accordingly

       DATABASEURI = "postgresql://<DB_NAME>:<PASSWORD>@<IP-ADDRESS>/postgres"

5) Run it in the shell

        From your terminal go to the webserver directory and run the following command:

        python server.py
    
6) Get help:

        python server.py --help



      
