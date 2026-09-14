mig:
	python manage.py makemigrations
	python manage.py migrate

ad:
	python manage.py createsuperuser
run:
	python ./manage.py runserver