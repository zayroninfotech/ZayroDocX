"""
Run once on server to create superadmin in MongoDB:
  python create_superadmin.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZayroDocs.settings')
django.setup()

from apps.dashboard.mongo_auth import create_user, user_exists

username = 'vamsi'
password = 'Zayron@2026'

if user_exists(username):
    print(f'User "{username}" already exists in MongoDB.')
else:
    user = create_user(username=username, password=password, email='', is_superuser=True)
    print(f'Superadmin "{username}" created in MongoDB. ID: {user.id}')
