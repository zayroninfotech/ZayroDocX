from django.contrib.auth.models import User
if User.objects.filter(username='vamsi').exists():
    u = User.objects.get(username='vamsi')
    u.set_password('Zayron@2026')
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print('Updated existing user vamsi as superadmin')
else:
    User.objects.create_superuser('vamsi', 'zayroninfotech@gmail.com', 'Zayron@2026')
    print('Created superuser vamsi')
