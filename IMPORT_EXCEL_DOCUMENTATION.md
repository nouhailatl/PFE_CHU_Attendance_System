# 📥 Interface d'Import Excel - Documentation d'Utilisation

## 🎯 Résumé des Modifications

Une interface complète d'import Excel a été implémentée pour permettre aux administrateurs DFRI d'importer massivement des stagiaires depuis des fichiers Excel/CSV.

---

## 🔧 Modifications Backend (main.py)

### Nouveaux Endpoints API

#### 1. **GET /interns/import/template**
Télécharge un fichier Excel modèle avec les colonnes pré-formatées.

**Paramètres:**
- En-têtes: `Authorization: Bearer {token}`

**Réponse:**
- Fichier Excel : `Template_Import_Stagiaires.xlsx`

**Colonnes du template:**
- `prenom` (obligatoire)
- `nom` (obligatoire)
- `departement` (obligatoire)
- `type_stagiaire` (optionnel)
- `ecole` (optionnel)
- `annee_etudes` (optionnel)
- `date_debut` (optionnel)
- `date_fin` (optionnel)
- `email` (optionnel)

---

#### 2. **POST /interns/import/validate**
Valide le fichier d'import **sans modifier** la base de données.

**Paramètres:**
- Méthode: `multipart/form-data`
- Fichier: `file` (xlsx, xls, csv)
- En-têtes: `Authorization: Bearer {token}`

**Réponse JSON:**
```json
{
  "valid_count": 5,
  "errors_count": 0,
  "errors_details": [
    {
      "row": 2,
      "message": "Service 'Urgences' inexistant (disponibles: Cardiologie, Pédiatrie, ...)"
    }
  ],
  "preview_rows": [
    {
      "first_name": "Jean",
      "last_name": "Dupont",
      "department_name": "Cardiologie",
      "department_id": "uuid-123..."
    }
  ]
}
```

---

#### 3. **POST /interns/import**
Importe réellement les stagiaires dans la base de données.

**Paramètres:**
- Méthode: `multipart/form-data`
- Fichier: `file` (xlsx, xls, csv)
- En-têtes: `Authorization: Bearer {token}`

**Réponse JSON:**
```json
{
  "message": "Import terminé : 5 stagiaires créés",
  "created_count": 5,
  "failed_rows": []
}
```

**Permissions:**
- DFRI: Accès complet à tous les départements
- Chef de Service: Peut importer seulement dans son département

---

## 🎨 Modifications Frontend (dashboard.html)

### 1. Nouvel Onglet "Import Stagiaires"
Ajouté à la section Administration, visible uniquement pour le DFRI.

**Localisation:** `Administration` → `📥 Import Stagiaires`

**Fonctionnalités:**
- ✅ Bouton pour télécharger le template Excel
- ✅ Zone de dépôt drag-and-drop pour les fichiers
- ✅ Rapport de validation détaillé avant import
  - Nombre de lignes valides (en vert)
  - Nombre de lignes avec erreurs (en rouge)
  - Détail des erreurs par ligne
  - Aperçu des 5 premières lignes
- ✅ Barre de progression pendant l'import
- ✅ Message de succès avec le nombre de stagiaires créés

---

### 2. Bouton "À Propos"
Ajouté en haut du bouton de déconnexion dans la barre latérale.

**Contenu:**
- Description de la plateforme
- Présentation de l'équipe de développement (3 étudiantes)
- Rôles et responsabilités de chaque membre
- Stack technologique utilisé
- Objectifs du projet
- Informations de support

---

## 📋 Format du Fichier d'Import

### Structure minimale requise:
```
prenom    | nom       | departement
----------|-----------|-------------------
Ahmed     | Hassan    | Cardiologie
Fatima    | Bennani   | Pédiatrie
Mohamed   | Amara     | Chirurgie
```

### Format complet accepté:
```
prenom | nom       | departement  | type_stagiaire | ecole                    | annee_etudes | date_debut   | date_fin     | email
-------|-----------|--------------|-----------------|--------------------------|--------------|--------------|--------------|------------------
Ahmed  | Hassan    | Cardiologie  | Médecin        | Université de Marrakech | 4ème année   | 2026-01-15   | 2026-03-15   | ahmed@email.com
Fatima | Bennani   | Pédiatrie    | Infirmier      | École d'Infirmiers      | 2ème année   | 2026-02-01   | 2026-04-01   | fatima@email.com
```

---

## 🚀 Utilisation Étape par Étape

### Étape 1: Télécharger le template
1. Se connecter au tableau de bord avec un compte DFRI
2. Aller à `Administration` → `📥 Import Stagiaires`
3. Cliquer sur "Télécharger le template Excel"
4. Ouvrir le fichier téléchargé dans Excel/LibreOffice

### Étape 2: Remplir le template
1. Conserver la première ligne (en-têtes)
2. Ajouter vos stagiaires à partir de la ligne 2
3. Remplir au minimum les colonnes: `prenom`, `nom`, `departement`
4. Les autres colonnes sont optionnelles
5. Sauvegarder le fichier

### Étape 3: Valider les données
1. Revenir au formulaire d'import
2. Glisser-déposer le fichier ou cliquer pour parcourir
3. Attendre l'analyse (quelques secondes)
4. Vérifier le rapport de validation:
   - ✅ Lignes valides (nombre en vert)
   - ❌ Lignes avec erreurs (nombre en rouge)
   - Corriger les erreurs si nécessaire et recommencer

### Étape 4: Confirmer l'import
1. Cliquer sur "Confirmer l'import (N)"
2. Attendre la barre de progression
3. Voir le message de succès: "Réussite : X stagiaires créés"
4. Actualiser la liste des stagiaires pour voir les nouvelles entrées

---

## ⚠️ Erreurs Courantes et Solutions

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Service 'X' inexistant" | Le département n'existe pas dans le système | Utiliser les noms exacts : Cardiologie, Pédiatrie, Chirurgie, Neurologie |
| "Prénom vide" | Colonne vide ou mal formatée | Vérifier que toutes les lignes ont un prénom et un nom |
| "Colonne obligatoire manquante" | En-têtes incorrects | Télécharger le template à nouveau et copier les en-têtes exactes |
| "Erreur 403: Accès restreint" | Compte non autorisé | Seul DFRI peut importer (Chef de Service peut importer seulement dans son service) |

---

## 🔐 Permissions et Sécurité

**Qui peut importer:**
- ✅ DFRI: Accès complet à tous les départements
- ✅ Chef de Service: Peut importer seulement dans son département
- ❌ Directeur: Accès en lecture seule (pas d'import)
- ❌ Secrétaire: Accès restreint (pas d'import)

**Validation des données:**
- Toutes les données sont validées avant import
- Pas de duplication dans la base de données
- Vérification de l'existence des départements
- Validation des formats de date (si fournis)

**Audit trail:**
- Chaque import est enregistré dans le journal d'audit
- Qui a importé, quand, combien de stagiaires
- Traçabilité complète des actions

---

## 📊 Résultats de Test

Les trois endpoints d'import Excel ont été testés avec succès:

✅ **GET /interns/import/template**
- Télécharge le fichier Excel template (5306 octets)
- Format correct avec en-têtes formatés et exemples

✅ **POST /interns/import/validate**
- Valide les fichiers Excel et CSV
- Détecte les erreurs de format et d'existence de département
- Retourne un rapport détaillé

✅ **POST /interns/import**
- Importe les stagiaires valides en base de données
- Crée les enregistrements avec les IDs UUID corrects
- Retourne le nombre exact de stagiaires créés

---

## 🎯 Prochaines Étapes Possibles (Bonus)

1. **Notifications d'import:** Envoyer un email quand un import est terminé
2. **Historique des imports:** Voir la liste des fichiers importés précédemment
3. **Modèles de colonnes personnalisées:** Permettre différents formats de fichiers
4. **Mise à jour en masse:** Modifier les données existantes via import
5. **Export de rapport d'import:** Télécharger un PDF avec les détails de l'import

---

## 📞 Support

Pour toute question ou problème:
- Contactez l'équipe DFRI
- Consultez la section "À propos" du dashboard
- Vérifiez les logs du serveur pour les erreurs détaillées

---

*Documentation mise à jour: Mai 2026*
*Version: 1.0*
*Plateforme: GST-TTA Analytics*
