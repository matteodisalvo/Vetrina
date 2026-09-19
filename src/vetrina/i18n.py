"""The texts of the window in every language it speaks, and the language to start in.

Each entry of TEXTS holds one text in all the languages, side by side, so a new text or a
new language is added in one place. Texts in braces, such as {title}, are filled in by the app.
"""

from __future__ import annotations

import locale
import os
import re
import subprocess
import sys

#: Language code -> its name, written in that language.
LANGUAGES = {"it": "Italiano", "en": "English", "es": "Español", "fr": "Français", "de": "Deutsch"}

TEXTS: dict[str, dict[str, str]] = {
    # Header
    "subtitle": {
        "it": "Miniature social per i repository GitHub",
        "en": "Social previews for GitHub repositories",
        "es": "Miniaturas sociales para repositorios de GitHub",
        "fr": "Miniatures sociales pour les dépôts GitHub",
        "de": "Social-Vorschaubilder für GitHub-Repositorys",
    },
    "repository_placeholder": {
        "it": "proprietario/repository oppure link GitHub",
        "en": "owner/repository or GitHub link",
        "es": "propietario/repositorio o enlace de GitHub",
        "fr": "propriétaire/dépôt ou lien GitHub",
        "de": "Besitzer/Repository oder GitHub-Link",
    },
    "load": {"it": "Carica da GitHub", "en": "Load from GitHub", "es": "Cargar de GitHub",
             "fr": "Charger depuis GitHub", "de": "Von GitHub laden"},
    "loading": {"it": "Carico…", "en": "Loading…", "es": "Cargando…", "fr": "Chargement…", "de": "Lädt…"},

    # Text
    "section_text": {"it": "Testo", "en": "Text", "es": "Texto", "fr": "Texte", "de": "Text"},
    "title": {"it": "Titolo", "en": "Title", "es": "Título", "fr": "Titre", "de": "Titel"},
    "description": {"it": "Descrizione", "en": "Description", "es": "Descripción", "fr": "Description",
                    "de": "Beschreibung"},
    "footer": {
        "it": "Testo in basso a destra (opzionale)",
        "en": "Bottom-right text (optional)",
        "es": "Texto abajo a la derecha (opcional)",
        "fr": "Texte en bas à droite (facultatif)",
        "de": "Text unten rechts (optional)",
    },
    "footer_hint": {
        "it": "Es. il tuo nome, un sito, una data…",
        "en": "E.g. your name, a website, a date…",
        "es": "P. ej. tu nombre, una web, una fecha…",
        "fr": "Par ex. votre nom, un site, une date…",
        "de": "Z. B. dein Name, eine Website, ein Datum…",
    },

    # Picture
    "section_picture": {"it": "Immagine", "en": "Image", "es": "Imagen", "fr": "Image", "de": "Bild"},
    "drop_here": {"it": "Trascina un'immagine qui", "en": "Drag an image here", "es": "Arrastra una imagen aquí",
                  "fr": "Faites glisser une image ici", "de": "Bild hierher ziehen"},
    "or": {"it": "oppure", "en": "or", "es": "o", "fr": "ou", "de": "oder"},
    "drop_replace": {
        "it": "Trascina un'altra immagine per sostituirla",
        "en": "Drag another image to replace it",
        "es": "Arrastra otra imagen para sustituirla",
        "fr": "Faites glisser une autre image pour la remplacer",
        "de": "Ein anderes Bild hierher ziehen, um es zu ersetzen",
    },
    "no_picture": {"it": "Nessuna immagine", "en": "No image", "es": "Ninguna imagen", "fr": "Aucune image",
                   "de": "Kein Bild"},
    "choose_file": {"it": "Scegli file", "en": "Choose file", "es": "Elegir archivo", "fr": "Choisir un fichier",
                    "de": "Datei wählen"},
    "remove": {"it": "Rimuovi", "en": "Remove", "es": "Quitar", "fr": "Retirer", "de": "Entfernen"},
    "github_avatar": {"it": "Foto profilo GitHub", "en": "GitHub profile picture",
                      "es": "Foto de perfil de GitHub", "fr": "Photo de profil GitHub", "de": "GitHub-Profilbild"},
    "project_logo": {"it": "Logo del progetto", "en": "Project logo", "es": "Logo del proyecto",
                     "fr": "Logo du projet", "de": "Projektlogo"},

    # Statistics, labels, bar
    "section_stats": {"it": "Statistiche GitHub", "en": "GitHub statistics", "es": "Estadísticas de GitHub",
                      "fr": "Statistiques GitHub", "de": "GitHub-Statistiken"},
    "contributors": {"it": "Contributori", "en": "Contributors", "es": "Colaboradores", "fr": "Contributeurs",
                     "de": "Mitwirkende"},
    "issues": {"it": "Issue", "en": "Issues", "es": "Issues", "fr": "Issues", "de": "Issues"},
    "stars": {"it": "Stelle", "en": "Stars", "es": "Estrellas", "fr": "Étoiles", "de": "Sterne"},
    "forks": {"it": "Fork", "en": "Forks", "es": "Forks", "fr": "Forks", "de": "Forks"},
    "section_labels": {"it": "Lingua delle etichette", "en": "Label language", "es": "Idioma de las etiquetas",
                       "fr": "Langue des libellés", "de": "Sprache der Beschriftungen"},
    "section_bar": {"it": "Barra in basso", "en": "Bottom bar", "es": "Barra inferior", "fr": "Barre du bas",
                    "de": "Leiste unten"},
    "bar_languages": {"it": "Linguaggi", "en": "Languages", "es": "Lenguajes", "fr": "Langages",
                      "de": "Sprachen"},
    "bar_single": {"it": "Colore unico", "en": "Single color", "es": "Color único", "fr": "Couleur unique",
                   "de": "Einzelfarbe"},
    "and_more": {"it": "e altri {count}", "en": "and {count} more", "es": "y {count} más",
                 "fr": "et {count} autres", "de": "und {count} weitere"},
    "change_color": {"it": "Cambia colore…", "en": "Change color…", "es": "Cambiar color…",
                     "fr": "Changer la couleur…", "de": "Farbe ändern…"},
    "color_title": {"it": "Colore della barra", "en": "Bar color", "es": "Color de la barra",
                    "fr": "Couleur de la barre", "de": "Farbe der Leiste"},

    # Preview
    "light": {"it": "Chiaro", "en": "Light", "es": "Claro", "fr": "Clair", "de": "Hell"},
    "dark": {"it": "Scuro", "en": "Dark", "es": "Oscuro", "fr": "Sombre", "de": "Dunkel"},
    "preview_at": {"it": "Anteprima al {percent}%", "en": "Preview at {percent}%",
                   "es": "Vista previa al {percent}%", "fr": "Aperçu à {percent}%",
                   "de": "Vorschau bei {percent}%"},
    "save": {"it": "Salva PNG…", "en": "Save PNG…", "es": "Guardar PNG…", "fr": "Enregistrer le PNG…",
             "de": "PNG speichern…"},
    "full_size_title": {"it": "{app} · anteprima al {percent}%", "en": "{app} · preview at {percent}%",
                        "es": "{app} · vista previa al {percent}%", "fr": "{app} · aperçu à {percent}%",
                        "de": "{app} · Vorschau bei {percent}%"},

    # Status line
    "status_start": {
        "it": "Incolla in alto il link di un repository GitHub, oppure compila i campi a mano.",
        "en": "Paste the link of a GitHub repository above, or fill in the fields by hand.",
        "es": "Pega arriba el enlace de un repositorio de GitHub o rellena los campos a mano.",
        "fr": "Collez en haut le lien d'un dépôt GitHub, ou remplissez les champs à la main.",
        "de": "Füge oben den Link eines GitHub-Repositorys ein oder fülle die Felder von Hand aus.",
    },
    "status_missing": {
        "it": "Scrivi prima il repository, es. matteodisalvo/Quantum-Viterbi-Algorithm.",
        "en": "Write the repository first, e.g. matteodisalvo/Quantum-Viterbi-Algorithm.",
        "es": "Escribe primero el repositorio, p. ej. matteodisalvo/Quantum-Viterbi-Algorithm.",
        "fr": "Saisissez d'abord le dépôt, par ex. matteodisalvo/Quantum-Viterbi-Algorithm.",
        "de": "Gib zuerst das Repository ein, z. B. matteodisalvo/Quantum-Viterbi-Algorithm.",
    },
    "status_loading": {"it": "Carico i dati da GitHub…", "en": "Loading data from GitHub…",
                       "es": "Cargando los datos de GitHub…", "fr": "Chargement des données depuis GitHub…",
                       "de": "Daten werden von GitHub geladen…"},
    "status_loaded": {
        "it": "Caricato {title}. Puoi modificare qualsiasi campo prima di salvare.",
        "en": "Loaded {title}. You can edit any field before saving.",
        "es": "Cargado {title}. Puedes modificar cualquier campo antes de guardar.",
        "fr": "{title} chargé. Vous pouvez modifier chaque champ avant d'enregistrer.",
        "de": "{title} geladen. Du kannst jedes Feld vor dem Speichern ändern.",
    },
    "status_bad_image": {
        "it": "{name} non è un'immagine che riesco ad aprire.",
        "en": "{name} is not an image I can open.",
        "es": "{name} no es una imagen que pueda abrir.",
        "fr": "{name} n'est pas une image que je peux ouvrir.",
        "de": "{name} ist kein Bild, das ich öffnen kann.",
    },
    "status_saved": {"it": "Salvata in {path}", "en": "Saved to {path}", "es": "Guardada en {path}",
                     "fr": "Enregistrée dans {path}", "de": "Gespeichert unter {path}"},
    "star_prompt": {
        "it": "Ti piace Vetrina? ⭐ Lasciale una stella su GitHub",
        "en": "Enjoying Vetrina? ⭐ Star it on GitHub",
        "es": "¿Te gusta Vetrina? ⭐ Dale una estrella en GitHub",
        "fr": "Vous aimez Vetrina ? ⭐ Donnez-lui une étoile sur GitHub",
        "de": "Gefällt dir Vetrina? ⭐ Gib ihr einen Stern auf GitHub",
    },
    "status_save_failed": {
        "it": "Non riesco a salvare la miniatura: {error}",
        "en": "I can't save the thumbnail: {error}",
        "es": "No puedo guardar la miniatura: {error}",
        "fr": "Impossible d'enregistrer la miniature : {error}",
        "de": "Das Vorschaubild kann nicht gespeichert werden: {error}",
    },
    "status_language": {"it": "Lingua dell'interfaccia: {name}", "en": "Interface language: {name}",
                        "es": "Idioma de la interfaz: {name}", "fr": "Langue de l'interface : {name}",
                        "de": "Sprache der Oberfläche: {name}"},

    # File dialogs and saved files
    "choose_title": {"it": "Scegli un'immagine", "en": "Choose an image", "es": "Elige una imagen",
                     "fr": "Choisissez une image", "de": "Bild auswählen"},
    "images": {"it": "Immagini", "en": "Images", "es": "Imágenes", "fr": "Images", "de": "Bilder"},
    "all_files": {"it": "Tutti i file", "en": "All files", "es": "Todos los archivos", "fr": "Tous les fichiers",
                  "de": "Alle Dateien"},
    "save_title": {"it": "Salva la miniatura", "en": "Save the thumbnail", "es": "Guardar la miniatura",
                   "fr": "Enregistrer la miniature", "de": "Vorschaubild speichern"},
    "file_suffix": {"it": "miniatura", "en": "thumbnail", "es": "miniatura", "fr": "miniature",
                    "de": "vorschaubild"},

    # Info window
    "info_title": {"it": "Informazioni su {app}", "en": "About {app}", "es": "Acerca de {app}",
                   "fr": "À propos de {app}", "de": "Über {app}"},
    "made_by": {"it": "Creato da", "en": "Made by", "es": "Creado por", "fr": "Créé par", "de": "Erstellt von"},
    "follow_me": {"it": "Seguimi su", "en": "Follow me on", "es": "Sígueme en", "fr": "Suivez-moi sur",
                  "de": "Folge mir auf"},
    "website": {"it": "Sito web", "en": "Website", "es": "Sitio web", "fr": "Site web", "de": "Website"},
    "icons_credit": {"it": "Icone di Tabler Icons, licenza MIT", "en": "Icons by Tabler Icons, MIT license",
                     "es": "Iconos de Tabler Icons, licencia MIT", "fr": "Icônes de Tabler Icons, licence MIT",
                     "de": "Icons von Tabler Icons, MIT-Lizenz"},

    # Loading errors
    "error_format": {
        "it": "Scrivi il repository come proprietario/nome, oppure incolla il suo link GitHub.",
        "en": "Write the repository as owner/name, or paste its GitHub link.",
        "es": "Escribe el repositorio como propietario/nombre o pega su enlace de GitHub.",
        "fr": "Saisissez le dépôt sous la forme propriétaire/nom, ou collez son lien GitHub.",
        "de": "Gib das Repository als Besitzer/Name ein oder füge seinen GitHub-Link ein.",
    },
    "error_not_found": {
        "it": "Repository {repository} non trovato, oppure privato.",
        "en": "Repository {repository} not found, or private.",
        "es": "Repositorio {repository} no encontrado o privado.",
        "fr": "Dépôt {repository} introuvable ou privé.",
        "de": "Repository {repository} nicht gefunden oder privat.",
    },
    "error_rate_limited": {
        "it": "GitHub ha limitato le richieste: riprova fra qualche minuto.",
        "en": "GitHub is limiting requests: try again in a few minutes.",
        "es": "GitHub ha limitado las peticiones: vuelve a intentarlo en unos minutos.",
        "fr": "GitHub limite les requêtes : réessayez dans quelques minutes.",
        "de": "GitHub begrenzt die Anfragen: Versuche es in ein paar Minuten erneut.",
    },
    "error_http": {"it": "GitHub ha risposto con l'errore {code}.", "en": "GitHub answered with error {code}.",
                   "es": "GitHub ha respondido con el error {code}.", "fr": "GitHub a répondu avec l'erreur {code}.",
                   "de": "GitHub hat mit dem Fehler {code} geantwortet."},
    "error_offline": {
        "it": "Impossibile raggiungere GitHub: controlla la connessione.",
        "en": "Can't reach GitHub: check your connection.",
        "es": "No se puede acceder a GitHub: comprueba la conexión.",
        "fr": "Impossible de joindre GitHub : vérifiez la connexion.",
        "de": "GitHub ist nicht erreichbar: Prüfe die Verbindung.",
    },
    "error_unexpected": {"it": "Qualcosa è andato storto: {error}", "en": "Something went wrong: {error}",
                         "es": "Algo ha salido mal: {error}", "fr": "Une erreur s'est produite : {error}",
                         "de": "Etwas ist schiefgelaufen: {error}"},
}


def translate(language: str, key: str, **values: object) -> str:
    """The text ``key`` in ``language`` (English when that language lacks it), filled in."""
    texts = TEXTS[key]
    return texts.get(language, texts["en"]).format(**values)


def system_language() -> str:
    """The first language of the system that the app speaks, else English."""
    preferred = []
    if sys.platform == "darwin":  # the order set in System Settings, then the locale
        try:
            preferred += re.findall(r'"?([a-z]{2})[-_"\s,]', subprocess.run(
                ["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True, timeout=2).stdout)
        except (OSError, subprocess.SubprocessError):
            pass
    preferred += [os.environ.get("LANG", "")[:2], (locale.getlocale()[0] or "")[:2]]
    return next((code for code in preferred if code in LANGUAGES), "en")
