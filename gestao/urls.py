from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('ordens/', views.ordens, name='ordens'),
    path('ordens/salvar/', views.os_save, name='os_save'),
    path('ordens/<int:pk>/excluir/', views.os_delete, name='os_delete'),
    path('ordens/<int:pk>/json/', views.os_detail_json, name='os_detail_json'),
    path('servicos/', views.servicos, name='servicos'),
    path('servicos/salvar/', views.servico_save, name='servico_save'),
    path('servicos/<int:pk>/excluir/', views.servico_delete, name='servico_delete'),
    path('servicos/<int:pk>/json/', views.servico_detail_json, name='servico_detail_json'),
    path('financeiro/', views.financeiro, name='financeiro'),
    path('contas/', views.contas, name='contas'),
    path('contas/salvar/', views.conta_save, name='conta_save'),
    path('contas/<int:pk>/pagar/', views.conta_toggle_pago, name='conta_toggle_pago'),
    path('contas/<int:pk>/excluir/', views.conta_delete, name='conta_delete'),
    path('contas/<int:pk>/json/', views.conta_detail_json, name='conta_detail_json'),
    path('colaboradores/', views.colaboradores, name='colaboradores'),
    path('colaboradores/adicionar/', views.colab_add, name='colab_add'),
    path('colaboradores/<int:pk>/remover/', views.colab_remove, name='colab_remove'),
    path('exportar/', views.exportar_csv, name='exportar_csv'),
]
