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
    path('financeiro/', views.financeiro, name='financeiro'),
    path('colaboradores/', views.colaboradores, name='colaboradores'),
    path('colaboradores/adicionar/', views.colab_add, name='colab_add'),
    path('colaboradores/<int:pk>/remover/', views.colab_remove, name='colab_remove'),
    path('exportar/', views.exportar_csv, name='exportar_csv'),
]
