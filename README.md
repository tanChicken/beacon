# Sample Users for Shared Database

These accounts are already created in the shared Render PostgreSQL DB.
Everyone can use them to log in (both locally and on the deployed site).

## Admin
- **Email:** meow1@gmail.com
- **Password:** meow1  

** please create your own superuser account as well! **

## Instructor
- **Email:** instructor1@gmail.com 
- **Password:** instructor1234  

## Student 
- **Email:** student1@gmail.com 
- **Password:** student1234  

** feel free to do testing and create dummy accounts on the database, it would be deleted afterwards as well **

Note: Do not delete or change these accounts.  
If you need to test new accounts, create separate ones instead.


# For first time using shared server + database:
1. pull repo
2. create virtual environment (using 
- python -m venv venv
- venv\Scripts\activate
)
3. install dependencies (pip install -r requirements.txt) (use pip list to ensure everything needed is downloaded)
4. run migrations (migrate)
5. to interact with databases, use python manage.py shell to test it out
6. creating user: User.objects.create(email="<email>", password="<password>", role="STUDENT"/"INSTRUCTOR") (no <> needed)
7. create student objects from sign up also can

- Check settings.py first to see which database are you on, local or shared
- After switching, do python manage.py migrate
- When finished with work, please comment out the local dataabase code and change it back to shared for convenience

- Three test accounts with details are currently provided above, please refer and log in using the details.