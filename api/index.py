import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Cria as tabelas no banco automaticamente na primeira execução
from django.core.management import call_command
try:
    call_command('migrate', '--run-syncdb', verbosity=0)
except Exception as e:
    print(f"[migrate] {e}")

# Cria o usuário admin se não existir
try:
    from django.contrib.auth.models import User
    from gestao.models import Colaborador
    if not User.objects.filter(username='leandro').exists():
        User.objects.create_superuser('leandro', '', 'gnv2024')
    if not Colaborador.objects.filter(nome='Leandro').exists():
        Colaborador.objects.create(nome='Leandro')
except Exception as e:
    print(f"[admin] {e}")

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()
