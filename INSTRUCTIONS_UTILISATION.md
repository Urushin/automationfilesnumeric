# Guide d'Utilisation de l'Application

Ce guide simple vous explique comment configurer et lancer l'application en un double-clic.

---

## 1. Autoriser le lancement du script (À faire une seule fois)

Par défaut, macOS bloque l'exécution des scripts non configurés. Pour autoriser le script à se lancer :
1. Ouvrez l'application **Terminal** (utilisez la recherche Spotlight en appuyant sur `Cmd + Espace` et tapez "Terminal").
2. Copiez et collez la commande suivante puis appuyez sur Entrée :
   ```bash
   chmod +x "/Users/issam/Documents/Projets perso/AutomatisationNumericFiles/Lancer_Application.command"
   ```
3. Vous pouvez maintenant fermer l'application Terminal.

---

## 2. Personnaliser l'icône sur votre Bureau

Pour rendre le raccourci plus joli sur votre bureau avec une belle image :
1. Faites un clic droit sur le fichier `Lancer_Application.command` et choisissez **Lire les informations** (ou faites `Cmd + I`).
2. Ouvrez l'image de votre choix dans l'application **Aperçu** de votre Mac.
3. Appuyez sur `Cmd + A` (tout sélectionner) puis `Cmd + C` (copier) dans Aperçu.
4. Revenez à la fenêtre d'informations ouverte à l'étape 1.
5. Cliquez sur la petite icône noire du script située tout en haut à gauche de la fenêtre d'informations pour la mettre en surbrillance.
6. Appuyez sur `Cmd + V` (coller). L'icône est maintenant personnalisée !

---

## 3. Utilisation quotidienne

### Démarrage :
* **Double-cliquez** simplement sur `Lancer_Application.command`.
* Une fenêtre de terminal s'ouvrira, les serveurs démarreront automatiquement en arrière-plan, et votre navigateur web s'ouvrira directement sur la page d'accueil de l'application (`http://localhost:3000`).

### Arrêt complet :
* Pour éteindre les serveurs proprement et libérer la mémoire, il vous suffit de **fermer la fenêtre du Terminal** ou d'appuyer sur `Ctrl + C` dans cette fenêtre.
* Tous les serveurs s'arrêteront instantanément en arrière-plan sans laisser de processus bloqués.
