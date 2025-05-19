from django.db import models
from django.contrib.auth.models import User
import math

class BaliseBLE(models.Model):
    """Modèle pour les balises BLE virtuelles"""
    identifiant = models.CharField(max_length=100, unique=True)  # UUID de la balise
    nom = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    puissance_emission = models.IntegerField(default=-59)  # Puissance d'émission en dBm
    rayon_couverture = models.FloatField(default=10.0)  # Rayon de couverture en mètres
    date_installation = models.DateTimeField(auto_now_add=True)
    est_active = models.BooleanField(default=True)
    type_zone = models.CharField(max_length=50, choices=[
        ('salle', 'Salle de classe'),
        ('couloir', 'Couloir'),
        ('entree', 'Entrée'),
        ('autre', 'Autre')
    ], default='autre')

    def __str__(self):
        return f"{self.nom} ({self.identifiant})"

    def simuler_signal(self, distance):
        """
        Simule la force du signal BLE en fonction de la distance
        Utilise le modèle de propagation du signal
        """
        if distance > self.rayon_couverture:
            return -100  # Signal trop faible pour être détecté
        
        # Modèle de propagation simplifié
        n = 2.0  # Facteur d'environnement (2 pour espace libre)
        return self.puissance_emission - (10 * n * math.log10(distance))

class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    identifiant = models.CharField(max_length=50, unique=True)
    annee_scolaire = models.CharField(max_length=20)
    groupe = models.CharField(max_length=50)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.prenom} {self.nom}"

class PositionEtudiant(models.Model):
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    date_mise_a_jour = models.DateTimeField(auto_now=True)
    est_dans_zone_rouge = models.BooleanField(default=False)
    balise_detectee = models.ForeignKey(BaliseBLE, on_delete=models.SET_NULL, null=True)
    force_signal = models.IntegerField(null=True)  # Force du signal en dBm

    class Meta:
        ordering = ['-date_mise_a_jour']

    def __str__(self):
        return f"Position de {self.etudiant} - {self.date_mise_a_jour}"

class ZoneRouge(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    points = models.JSONField()  # Liste de points [{"lat": x, "lng": y}, ...]
    date_creation = models.DateTimeField(auto_now_add=True)
    balises = models.ManyToManyField(BaliseBLE, blank=True)  # Balises BLE dans cette zone
    
    def __str__(self):
        return self.nom

class Notification(models.Model):
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    est_lue = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Notification - {self.date_creation}"

class CarteEcole(models.Model):
    nom = models.CharField(max_length=100)
    image = models.ImageField(upload_to='cartes/')
    date_ajout = models.DateTimeField(auto_now_add=True)
    echelle = models.FloatField(default=1.0)  # Pour la conversion des coordonnées
    
    def __str__(self):
        return self.nom
