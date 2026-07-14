import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

try:
    from django.core.management import call_command
    # --fake-initial: as tabelas originais já existem no banco (criadas via syncdb);
    # marca a migração 0001 como aplicada e executa apenas as novas (0002+)
    call_command('migrate', '--fake-initial', verbosity=0)

    from django.contrib.auth.models import User
    from gestao.models import Colaborador
    if not User.objects.filter(username='leandro').exists():
        User.objects.create_superuser('leandro', '', 'gnv2024')
    if not Colaborador.objects.filter(nome='Leandro').exists():
        Colaborador.objects.create(nome='Leandro')
except Exception as e:
    print(f"[setup] {e}")

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()
