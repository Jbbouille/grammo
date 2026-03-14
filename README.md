# Correcteur Grammalecte

Application de bureau pour la correction orthographique et grammaticale du français, basée sur [Grammalecte](https://grammalecte.net/).

## Fonctionnalités

- Détection des fautes d'**orthographe** (souligné en rouge) et de **grammaire** (souligné en bleu)
- Vérification automatique au collage de texte
- Liste des erreurs triées par ordre d'apparition dans le texte
- Application des suggestions via clic droit sur le texte ou sur la liste d'erreurs
- Correction en un clic de toutes les fautes avec suggestions
- Copie du texte corrigé dans le presse-papier

## Utilisation

1. Coller ou saisir votre texte dans la zone d'édition
2. La vérification se lance automatiquement au collage, ou manuellement avec **Ctrl+Entrée**
3. Les erreurs apparaissent soulignées dans le texte et listées à droite
4. Clic droit sur un mot souligné (ou sur une entrée de la liste) pour choisir une suggestion
5. **Appliquer toutes les suggestions** corrige toutes les fautes en une fois et copie le résultat

## Installation (développement)

Python 3.11+ requis.

```bash
pip install PyQt6
python main.py
```

## Compilation

Des exécutables pour Windows, macOS et Linux sont produits automatiquement via GitHub Actions.
Les binaires sont disponibles dans l'onglet [Releases](../../releases).

## Licence

Ce projet est distribué sous licence [GPL v3](LICENSE).
Grammalecte est distribué sous licence GPL v2+ — voir `Grammalecte-fr-v2.3.0/LICENSE.txt`.
