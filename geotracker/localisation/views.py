from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Etudiant, PositionEtudiant, ZoneRouge, Notification, BaliseBLE
import json
from datetime import datetime
from django.contrib import messages
import math

# Create your views here.

@login_required
def dashboard(request):
    """Vue principale avec les deux onglets"""
    etudiants = Etudiant.objects.all()
    zones_rouges = ZoneRouge.objects.all()
    notifications = Notification.objects.filter(est_lue=False)[:5]
    balises = BaliseBLE.objects.filter(est_active=True)
    
    context = {
        'etudiants': etudiants,
        'zones_rouges': zones_rouges,
        'notifications': notifications,
        'balises': balises
    }
    return render(request, 'localisation/dashboard.html', context)

@login_required
def ajouter_etudiant(request):
    """Vue pour ajouter un étudiant"""
    if request.method == 'POST':
        # Logique d'ajout d'étudiant
        pass
    return render(request, 'localisation/ajouter_etudiant.html')

@login_required
@require_POST
def update_position(request):
    try:
        data = json.loads(request.body)
        etudiant_id = data.get('etudiant_id')
        position_actuelle = data.get('position', {})  # Position actuelle de l'étudiant
        
        etudiant = get_object_or_404(Etudiant, id=etudiant_id)
        
        # Simuler la détection des balises
        balises_detectees = simuler_detection_balises(position_actuelle)
        
        if balises_detectees:
            # Calculer la position par triangulation
            position = calculer_position_triangulation(balises_detectees)
            
            if position:
                # Créer ou mettre à jour la position
                pos, created = PositionEtudiant.objects.update_or_create(
                    etudiant=etudiant,
                    defaults={
                        'latitude': position['latitude'],
                        'longitude': position['longitude'],
                        'est_dans_zone_rouge': False,
                        'balise_detectee': position.get('balise_plus_proche'),
                        'force_signal': position.get('force_signal')
                    }
                )
                
                # Vérifier si l'étudiant est dans une zone rouge
                for zone in ZoneRouge.objects.all():
                    if est_dans_zone_rouge(position['latitude'], position['longitude'], zone.points):
                        pos.est_dans_zone_rouge = True
                        pos.save()
                        
                        # Créer une notification
                        Notification.objects.create(
                            message=f"{etudiant.prenom} {etudiant.nom} est entré dans la zone rouge : {zone.nom}"
                        )
                        break
                
                return JsonResponse({
                    'status': 'success',
                    'position': position,
                    'balises_detectees': balises_detectees
                })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Aucune balise détectée'
        })
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def simuler_detection_balises(position):
    """
    Simule la détection des balises BLE à partir d'une position
    """
    balises_detectees = []
    balises_actives = BaliseBLE.objects.filter(est_active=True)
    
    for balise in balises_actives:
        # Calculer la distance entre la position et la balise
        distance = calculer_distance(
            position['latitude'],
            position['longitude'],
            balise.latitude,
            balise.longitude
        )
        
        # Simuler la force du signal
        force_signal = balise.simuler_signal(distance)
        
        # Si le signal est détectable
        if force_signal > -100:
            balises_detectees.append({
                'identifiant': balise.identifiant,
                'force_signal': force_signal,
                'distance': distance,
                'type_zone': balise.type_zone
            })
    
    # Trier par force de signal (du plus fort au plus faible)
    return sorted(balises_detectees, key=lambda x: x['force_signal'], reverse=True)

def calculer_distance(lat1, lon1, lat2, lon2):
    """
    Calcule la distance en mètres entre deux points géographiques
    en utilisant la formule de Haversine
    """
    R = 6371000  # Rayon de la Terre en mètres
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculer_position_triangulation(balises_detectees):
    """
    Calcule la position de l'étudiant en utilisant la triangulation
    basée sur la force du signal des balises BLE détectées.
    """
    if not balises_detectees or len(balises_detectees) < 3:
        return None
    
    # Trier les balises par force de signal (du plus fort au plus faible)
    balises_triees = sorted(balises_detectees, key=lambda x: x['force_signal'], reverse=True)
    
    # Prendre les 3 balises avec le signal le plus fort
    balises_principales = balises_triees[:3]
    
    # Récupérer les informations des balises
    balises_info = []
    for b in balises_principales:
        balise = BaliseBLE.objects.get(identifiant=b['identifiant'])
        balises_info.append({
            'balise': balise,
            'force_signal': b['force_signal'],
            'distance': calculer_distance_signal(b['force_signal'], balise.puissance_emission)
        })
    
    # Calculer la position par triangulation
    try:
        # Utiliser la méthode de trilatération
        position = trilateration(balises_info)
        return {
            'latitude': position['latitude'],
            'longitude': position['longitude'],
            'balise_plus_proche': balises_info[0]['balise'],
            'force_signal': balises_info[0]['force_signal']
        }
    except:
        # En cas d'échec, utiliser la position de la balise la plus proche
        balise_plus_proche = balises_info[0]['balise']
        return {
            'latitude': balise_plus_proche.latitude,
            'longitude': balise_plus_proche.longitude,
            'balise_plus_proche': balise_plus_proche,
            'force_signal': balises_info[0]['force_signal']
        }

def calculer_distance_signal(force_signal, puissance_emission):
    """
    Calcule la distance approximative en mètres basée sur la force du signal
    en utilisant le modèle de propagation du signal.
    """
    # Constante d'environnement (2-4, 2 pour espace libre)
    n = 2.0
    
    # Calcul de la distance en utilisant la formule de propagation
    distance = 10 ** ((puissance_emission - force_signal) / (10 * n))
    return distance

def trilateration(balises_info):
    """
    Calcule la position par trilatération à partir de 3 points et leurs distances.
    """
    # Implémentation de la trilatération
    # À adapter selon vos besoins spécifiques
    # Pour l'instant, retourne une moyenne pondérée des positions
    lat_sum = 0
    lng_sum = 0
    weight_sum = 0
    
    for info in balises_info:
        weight = 1 / (info['distance'] + 1)  # Éviter division par zéro
        lat_sum += info['balise'].latitude * weight
        lng_sum += info['balise'].longitude * weight
        weight_sum += weight
    
    return {
        'latitude': lat_sum / weight_sum,
        'longitude': lng_sum / weight_sum
    }

@login_required
def ajouter_zone_rouge(request):
    """Vue pour ajouter une zone rouge"""
    if request.method == 'POST':
        # Logique d'ajout de zone
        pass
    return render(request, 'localisation/ajouter_zone.html')

@login_required
def ajouter_balise(request):
    """Vue pour ajouter une nouvelle balise BLE"""
    if request.method == 'POST':
        identifiant = request.POST.get('identifiant')
        nom = request.POST.get('nom')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        puissance_emission = request.POST.get('puissance_emission', -59)
        
        BaliseBLE.objects.create(
            identifiant=identifiant,
            nom=nom,
            latitude=latitude,
            longitude=longitude,
            puissance_emission=puissance_emission
        )
        messages.success(request, 'Balise ajoutée avec succès')
        return redirect('dashboard')
    
    return render(request, 'localisation/ajouter_balise.html')

def est_dans_zone_rouge(lat, lng, points):
    """
    Vérifie si un point (lat, lng) est à l'intérieur d'un polygone défini par une liste de points.
    Utilise l'algorithme du point dans un polygone (ray casting).
    """
    n = len(points)
    inside = False
    j = n - 1
    
    for i in range(n):
        if ((points[i]['lat'] > lat) != (points[j]['lat'] > lat) and
            (lng < (points[j]['lng'] - points[i]['lng']) * (lat - points[i]['lat']) /
             (points[j]['lat'] - points[i]['lat']) + points[i]['lng'])):
            inside = not inside
        j = i
    
    return inside

@login_required
def admin_dashboard(request):
    """Vue pour le tableau de bord d'administration"""
    context = {
        'etudiants_count': Etudiant.objects.count(),
        'zones_count': ZoneRouge.objects.count(),
        'balises_count': BaliseBLE.objects.count(),
        'notifications': Notification.objects.filter(est_lue=False)[:5]
    }
    return render(request, 'localisation/admin_dashboard.html', context)

@login_required
def simulation_dashboard(request):
    """Vue pour l'interface de simulation"""
    context = {
        'etudiants': Etudiant.objects.all(),
        'zones': ZoneRouge.objects.all(),
        'balises': BaliseBLE.objects.filter(est_active=True)
    }
    return render(request, 'localisation/simulation_dashboard.html', context)

@login_required
def liste_etudiants(request):
    """Vue pour la liste des étudiants"""
    context = {
        'etudiants': Etudiant.objects.all()
    }
    return render(request, 'localisation/liste_etudiants.html', context)

@login_required
def liste_zones(request):
    """Vue pour la liste des zones rouges"""
    context = {
        'zones': ZoneRouge.objects.all()
    }
    return render(request, 'localisation/liste_zones.html', context)

@login_required
def gestion_carte(request):
    """Vue pour la gestion de la carte de l'école"""
    return render(request, 'localisation/gestion_carte.html')

@login_required
def notifications(request):
    """Vue pour les notifications"""
    context = {
        'notifications': Notification.objects.all().order_by('-date_creation')
    }
    return render(request, 'localisation/notifications.html', context)
