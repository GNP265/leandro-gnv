import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Roda migrações e cria admin automaticamente
from django.core.management import call_command
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'auth_user'
        )
    """)
    tabelas_existem = cursor.fetchone()[0]

if not tabelas_existem:
    call_command('migrate', '--run-syncdb', verbosity=1)
    from django.contrib.auth.models import User
    from gestao.models import Colaborador
    if not User.objects.filter(username='leandro').exists():
        User.objects.create_superuser('leandro', '', 'gnv2024')
    if not Colaborador.objects.filter(nome='Leandro').exists():
        Colaborador.objects.create(nome='Leandro')

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()
