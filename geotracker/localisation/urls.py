from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('simulation/', views.simulation_dashboard, name='simulation_dashboard'),
    path('etudiants/', views.liste_etudiants, name='liste_etudiants'),
    path('etudiants/ajouter/', views.ajouter_etudiant, name='ajouter_etudiant'),
    path('zones/', views.liste_zones, name='liste_zones'),
    path('zones/ajouter/', views.ajouter_zone, name='ajouter_zone'),
    path('carte/', views.gestion_carte, name='gestion_carte'),
    path('notifications/', views.notifications, name='notifications'),
] 