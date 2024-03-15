source venv/Scripts/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
