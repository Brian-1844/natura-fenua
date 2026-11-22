# Natura Fenua 🌺☁️🐦

Application pour reconnaître la nature de Tahiti **sans connexion** : nuages, plantes et arbres,
oiseaux, insectes et champignons. Chaque espèce a sa fiche (nom en reo Tahiti, en français,
nom scientifique, usages, précautions).

- **Version web** : https://brian-1844.github.io/natura-fenua/
- **App Android (APK)** : https://github.com/Brian-1844/natura-fenua/releases/latest/download/natura-fenua.apk

## Comment l'app reconnaît

Une IA (MobileNet V3) calcule une « empreinte » de la photo, puis l'app la compare aux empreintes
des photos d'apprentissage et choisit l'espèce la plus proche. Tout se passe sur le téléphone.

- Les photos d'apprentissage sont dans `photos/<section>/<espèce>/`, par exemple `photos/plantes/nono/`.
- Le nom du dossier de l'espèce est son `id` dans `data.json` (`tiare`, `uru`, `nono`, `taro`…).
- Un dossier `autre` par section (photos de fond, de choses qui ne sont pas dans la liste) aide l'app
  à répondre « je ne reconnais rien » au lieu de se tromper.
- À chaque envoi sur GitHub, l'onglet **Actions** recalcule les empreintes (`refs/`), affiche la
  précision dans le journal, puis construit un nouvel APK.
- Dans l'app, **Apprendre à l'app** ajoute des photos directement sur le téléphone (elles marchent
  tout de suite pour toi), et **Exporter mes photos (ZIP)** crée un fichier déjà rangé par dossier,
  à mettre dans `photos/` pour que tout le monde en profite.

## Carte et espèces dangereuses

- **Ma carte de Tahiti** : repères placés par l'utilisateur et découvertes avec position. Fond de carte
  OpenStreetMap quand il y a du réseau ; sans réseau, un contour simplifié de Tahiti et Moorea
  (`vendor/tahiti.geojson`, Natural Earth) reste affiché avec les repères. Les espèces rares (`"rare": true`)
  ne sont jamais placées sur la carte.
- **Fiches rouges** : ajoute `"danger": "texte"` à une espèce dans `data.json` pour une fiche rouge « ☠ DANGER »,
  un badge rouge dans les listes, et la liste « Espèces dangereuses » de l'accueil.
- Pour une carte partagée entre tous les utilisateurs, il faudra un serveur (Supabase ou Firebase) avec
  modération ; pas encore fait.

## Conseils pour de bonnes photos d'apprentissage

- Mieux vaut **10 plantes différentes** (ou 10 endroits, 10 jours) que 100 photos de la même : les photos
  presque identiques (rafale) sont comptées une seule fois.
- Ajoute un dossier `autre` par section (routes, maisons, mer, ciel, autres plantes…) : sans lui, l'app ne
  peut pas dire « je ne reconnais rien ».
- Le journal de l'onglet **Actions** affiche la précision réelle (testée sans les photos de la même séance)
  et les seuils « sûr » / « peut-être » calculés automatiquement.

## Mettre en ligne (une seule fois)

1. Sur GitHub, crée un dépôt **public** nommé `natura-fenua`.
2. **Settings → Secrets and variables → Actions** : crée les mêmes secrets que pour Hiʻo Video
   (`KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`). Si l'alias de ta clé n'est pas `hio`, ajoute aussi `KEYSTORE_ALIAS`.
3. **Settings → Actions → General → Workflow permissions** : coche *Read and write permissions*.
4. **Settings → Pages** : Source = *Deploy from a branch*, branche `main`, dossier `/ (root)`.
5. Envoie les fichiers. L'APK apparaît dans **Releases** après environ 6 minutes.

## Publier une mise à jour de l'app

1. Modifie `index.html` (ou `data.json` pour les fiches).
2. Augmente le numéro de version au **même** endroit dans ces 3 fichiers :
   `index.html` (`APP_VERSION`), `version.json` et `sw.js` (`CACHE`).
3. Envoie les fichiers : un nouvel APK est construit, et le bouton ⓘ de l'app propose la mise à jour.

## Ajouter des photos

Mets les photos dans le bon dossier (`photos/plantes/tiare/`…) depuis le site GitHub
(*Add file → Upload files*, jusqu'à 100 photos à la fois). Tout le reste est automatique.

## Bon à savoir

- Champignons et plantes : l'app peut se tromper. Elle ne dit jamais qu'une chose est comestible.
- La version web a besoin d'internet la première fois pour télécharger l'IA (environ 25 Mo) ;
  l'APK l'inclut déjà.
- Les noms en reo Tahiti sont à faire vérifier (famille, Académie tahitienne).
