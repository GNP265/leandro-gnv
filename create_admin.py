#!/usr/bin/env python
"""Run this once to create the admin user and default collaborator."""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from gestao.models import Colaborador

# Create admin user
if not User.objects.filter(username='leandro').exists():
    User.objects.create_superuser('leandro', '', 'gnv2024')
    print('✅ Usuário criado: leandro / gnv2024')
    print('⚠️  TROQUE A SENHA pelo painel /admin/ após o primeiro login!')
else:
    print('Usuário "leandro" já existe.')

# Create default collaborator
if not Colaborador.objects.filter(nome='Leandro').exists():
    Colaborador.objects.create(nome='Leandro')
    print('✅ Colaborador "Leandro" criado.')
