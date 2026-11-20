# HyperFrames : règles apprises à l'usage

La documentation complète est dans le paquet (`hyperframes docs <sujet>`, et les références des skills sous `node_modules/hyperframes/dist/skills/`). Ce qui a réellement posé problème :

- **Un `<video>` minuté ne doit pas être dans un élément lui-même minuté** (`data-start`) : l'extracteur d'images et la visibilité ne s'accordent plus. Mettre `data-start/data-duration` sur le média, et l'enveloppe sans minutage (elle peut porter des transformations).
- **Jamais deux tweens sur la même propriété du même élément** : le zoom lent va sur le média, les « punch » sur l'enveloppe, le tremblement sur le conteneur caméra.
- **Pas de `transform` CSS sur un élément animé par GSAP** (ex. `translateX(-50%)` pour centrer) : centrer avec `left:0; right:0; margin:0 auto; width:max-content`.
- **`fromTo` avec une valeur de départ visible** (opacité 0,5…) s'applique à la création : ajouter `immediateRender: false`, sinon l'élément est visible dès la première image.
- **Enregistrer la timeline en dernier** (`window.__timelines["id"] = tl`), après le chargement des polices.
- **Canvas / WebGL** : dessiner dans `window.addEventListener("hf-seek", e => renderAt(e.detail.time))`, état calculé à partir du temps seul, aléatoire seedé (mulberry32), `preserveDrawingBuffer: true`.
- **Audio** : `<audio data-start data-duration data-media-start data-volume data-fade-in data-fade-out>` ; une musique continue se découpe en plusieurs éléments qui lisent le même fichier à l'offset voulu.
- **Commandes** : `hyperframes lint` (rapide), `hyperframes check` (lint + exécution réelle : trouve les erreurs JavaScript), `hyperframes snapshot --at "1,2,3" --no-end` (planche `contact-sheet.jpg` dans `.hyperframes/artifacts/snapshots/<id>/`), `hyperframes render -q delivery -w 3 -o x.mp4`. Rendu ≈ 0,1 s par image + extraction vidéo : lancer en arrière-plan.
- Écran noir dans les snapshots = erreur JavaScript : lancer `hyperframes check` pour la voir.
- Chrome de rendu : `hyperframes browser ensure` (une fois). Télémétrie : `hyperframes telemetry disable`.
