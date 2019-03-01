### Creating a migration
alembic --config database/migrations/alembic.ini revision --autogenerate -m "Revision description"


### Migrating
alembic --config migrations/alembic.ini upgrade head