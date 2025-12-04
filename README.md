python manage.py makemigrations --settings=config.settings.local
python manage.py migrate --settings=config.settings.local

python manage.py makemigrations file_uploads --settings=config.settings.local

python manage.py runserver --settings=config.settings.local
python manage.py migrate --settings=config.settings.local

celery -A config worker --loglevel=info
