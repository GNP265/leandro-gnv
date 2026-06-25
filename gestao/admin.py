from django.contrib import admin
from .models import OrdemServico, Colaborador

@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ['pk', 'nome_cliente', 'placa', 'servico', 'data', 'valor', 'status']
    list_filter = ['status', 'data', 'colaborador']
    search_fields = ['nome_cliente', 'placa', 'servico']
    date_hierarchy = 'data'

@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo', 'criado_em']
