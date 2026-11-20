# Contrôle qualité

Ne jamais envoyer un rendu sans avoir fait ces vérifications ; dire clairement ce qui n'a pas pu l'être (on ne peut pas écouter : le signaler et demander à l'utilisateur d'écouter les passages modifiés).

## Avant le rendu

1. `node scripts/check_cuts.mjs projet.config.mjs` → aucun mot coupé (hors ponctuation).
2. `hyperframes lint` → 0 erreur. Les avertissements « fichier introuvable » avant `prep` sont normaux.
3. Relire **tous** les sous-titres :
   ```bash
   node -e "const h=require('fs').readFileSync('<root>/build/edit/index.html','utf8');console.log([...h.matchAll(/<div class=\"cap\"[^>]*>(.*?)<\/div>/g)].map(m=>[...m[1].matchAll(/>([^<]+)<\/span>/g)].map(x=>x[1]).join(' ')).join(' | '))"
   ```
   Chercher : mots manquants (« NUMÉRO 2 » sans « QUESTION », « COMBIEN A-T-IL » sans « Y »), noms mal transcrits, groupes à cheval sur deux phrases. Corriger avec `fix` (global ou par segment).
4. `hyperframes snapshot --at "…"` aux endroits modifiés (entourer les points entre guillemets sous PowerShell) et regarder chaque image : titres qui se chevauchent, calques qui ne disparaissent pas (ex. score final resté sur la vidéo bonus), cadrage des cartes (visage visible).

## Après le rendu

`node scripts/qa_render.mjs final.mp4` vérifie : 1080×1920, H.264 + AAC, loudness −16 à −11 LUFS, crête ≤ −1 dB, écrans noirs (doivent être voulus), images figées > 2 s, silences > 0,5 s, erreurs de décodage ; et produit une planche contact 1 image/s à regarder en entier.

Puis extraire quelques images serrées autour de chaque raccord modifié (`ffmpeg -ss T -t 4 -i final.mp4 -vf "fps=4,scale=180:320,tile=8x2" …`) : transitions, première image de chaque plan (pas d'image d'un autre clip), score qui évolue au bon moment.

## Ce que les spectateurs ont remarqué sur un vrai projet (à vérifier systématiquement)

| Retour | Cause | Correction |
|---|---|---|
| « des fois le son est coupé » | coupes au milieu des mots, noise gate | `check_cuts`, sorties prolongées, queues de son, pas de gate |
| « on ne voit pas le visage de X » | carte photo tirée d'un plan large | carte recadrée dans la source 4K au moment où le joueur pose face caméra |
| « laisse-les avancer » | présentation trop courte | 1,2–2 s de marche vers la caméra + zoom qui suit, puis arrêt sur image |
| « on entend le top trop tôt » | phrase qui n'existe que dans l'enregistrement externe, hors image | démarrer la question sur la coupe caméra ; morceau téléphone seulement là où il est synchrone |
| « une scène coupée bizarre avant le gagnant » | segment qui commence avant une jointure du rush | commencer après la jointure |
| « on va croire que je ne connais pas les réponses » | l'animateur valide une mauvaise réponse | retirer sa phrase, croix + « CONTESTÉ » |
| « il y a deux fois la question 1 » | manche rejouée | rembobinage VHS + « ON RECOMMENCE » |
| faux raccords | sauts dans le même plan | flash + whoosh + changement de cadrage (automatique) |
| la Q2 « mal faite » : des paniers sans réponse | réponses inaudibles, attribution déduite | demander l'audio ou le déroulé à l'utilisateur, ne garder que les paniers suivis d'une réponse |
