# Guide d'Utilisation de l'Application sur Windows

Ce guide simple vous explique comment configurer et lancer l'application en un double-clic sur Windows.

---

## 1. Créer le raccourci sur votre Bureau

Pour pouvoir lancer l'application facilement depuis votre Bureau :
1. Ouvrez l'explorateur de fichiers et accédez au dossier :
   `C:\Users\issam\Documents\Projets perso\AutomatisationNumericFiles`
2. Faites un clic droit sur le fichier `Lancer_Application.bat`.
3. Choisissez **Envoyer vers** > **Bureau (créer un raccourci)**.
4. Un raccourci nommé `Lancer_Application.bat - Raccourci` apparaît maintenant sur votre Bureau. Vous pouvez le renommer en "Lancer Application".

---

## 2. Personnaliser l'icône du raccourci

Pour changer l'icône noire standard par une icône plus agréable :
1. Faites un clic droit sur le raccourci créé sur votre Bureau, puis choisissez **Propriétés**.
2. Allez dans l'onglet **Raccourci** et cliquez sur le bouton **Changer d'icône...** tout en bas.
3. Windows affiche un message d'avertissement, cliquez sur **OK**.
4. Cliquez sur **Parcourir...** pour sélectionner un fichier d'icône (`.ico`) de votre choix, ou choisissez l'une des icônes proposées par défaut par Windows.
5. Cliquez sur **OK** puis sur **Appliquer** pour valider le changement.

---

## 3. Utilisation quotidienne

### Démarrage :
* **Double-cliquez** sur le raccourci sur votre Bureau.
* Une fenêtre noire (l'invite de commandes) s'ouvre, lance les serveurs puis ouvre automatiquement l'application web dans votre navigateur à l'adresse `http://localhost:3000`.

### Arrêt complet :
* Ne fermez pas directement la fenêtre noire avec la croix rouge pour éviter de laisser les serveurs tourner en arrière-plan.
* **Appuyez simplement sur la touche [Entrée]** à l'intérieur de la fenêtre noire de l'invite de commandes. Les serveurs s'arrêteront proprement et la fenêtre se fermera toute seule.
