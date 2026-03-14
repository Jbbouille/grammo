#!/usr/bin/env python3
"""
Application de correction orthographique et grammaticale
utilisant Grammalecte et PyQt6.
"""

import sys
import os

# Ajouter le dossier grammalecte au path (supporte l'exécutable PyInstaller)
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_base, "Grammalecte-fr-v2.3.0"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QListWidget, QListWidgetItem,
    QSplitter, QStatusBar, QMessageBox, QToolButton, QMenu
)
from PyQt6.QtGui import (
    QTextCharFormat, QColor, QTextCursor, QFont, QIcon
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import grammalecte
from grammalecte.grammar_checker import GrammarChecker


class TextEdit(QTextEdit):
    pasted = pyqtSignal()
    context_menu_at = pyqtSignal(object, int)  # (QPoint global, doc position)

    def insertFromMimeData(self, source):
        super().insertFromMimeData(source)
        self.pasted.emit()

    def contextMenuEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        self.context_menu_at.emit(event.globalPos(), cursor.position())


class CheckerThread(QThread):
    """Thread pour la vérification en arrière-plan."""
    results_ready = pyqtSignal(list, list, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, checker, text):
        super().__init__()
        self.checker = checker
        self.text = text

    def run(self):
        try:
            grammar_errors, spell_errors = self.checker.getParagraphErrors(
                self.text, bSpellSugg=True
            )
            self.results_ready.emit(list(grammar_errors), list(spell_errors), self.text)
        except Exception as e:
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.checker = None
        self.grammar_errors = []
        self.spell_errors = []
        self._updating = False  # True pendant nos propres modifications du texte
        self._init_checker()
        self._build_ui()

    def _init_checker(self):
        try:
            self.checker = GrammarChecker("fr")
        except Exception as e:
            QMessageBox.critical(None, "Erreur", f"Impossible de charger Grammalecte :\n{e}")

    def _build_ui(self):
        self.setWindowTitle("Correcteur orthographique — Grammalecte")
        self.resize(1000, 650)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # --- Barre d'outils ---
        toolbar = QHBoxLayout()
        self.btn_copy = QToolButton()
        self.btn_copy.setIcon(QIcon.fromTheme(
            "edit-copy",
            QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_FileDialogContentsView
            )
        ))
        self.btn_copy.setText("Copier")
        self.btn_copy.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_copy.setToolTip("Copier tout le texte dans le presse-papier")
        self.btn_copy.clicked.connect(self.copy_text)

        self.btn_check = QPushButton("Vérifier  (Ctrl+Entrée)")
        self.btn_check.setShortcut("Ctrl+Return")
        self.btn_check.clicked.connect(self.check_text)

        self.btn_apply_all = QPushButton("Appliquer toutes les suggestions")
        self.btn_apply_all.setEnabled(False)
        self.btn_apply_all.clicked.connect(self.apply_all_suggestions)

        self.btn_clear = QPushButton("Effacer les annotations")
        self.btn_clear.clicked.connect(self.clear_annotations)

        toolbar.addWidget(self.btn_copy)
        toolbar.addWidget(self.btn_apply_all)
        toolbar.addWidget(self.btn_check)
        toolbar.addWidget(self.btn_clear)
        toolbar.addStretch()
        root.addLayout(toolbar)

        # --- Splitter éditeur / panneau erreurs ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Éditeur
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(QLabel("Texte à vérifier :"))

        self.editor = TextEdit()
        self.editor.setFont(QFont("Georgia", 13))
        self.editor.setPlaceholderText("Saisissez ou collez votre texte ici…")
        self.editor.pasted.connect(self.check_text)
        self.editor.context_menu_at.connect(self._show_context_menu)
        self.editor.document().contentsChanged.connect(self._on_contents_changed)
        editor_layout.addWidget(self.editor)
        splitter.addWidget(editor_widget)

        # Panneau erreurs
        errors_widget = QWidget()
        errors_layout = QVBoxLayout(errors_widget)
        errors_layout.setContentsMargins(0, 0, 0, 0)
        errors_layout.addWidget(QLabel("Erreurs détectées :"))

        self.error_list = QListWidget()
        self.error_list.setWordWrap(True)
        self.error_list.itemClicked.connect(self._on_error_clicked)
        self.error_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.error_list.customContextMenuRequested.connect(self._show_error_list_context_menu)
        errors_layout.addWidget(self.error_list)

        self.detail_label = QLabel()
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet(
            "background:#f5f5dc; border:1px solid #ccc; padding:6px; border-radius:4px;"
        )
        self.detail_label.setMinimumHeight(80)
        errors_layout.addWidget(self.detail_label)

        splitter.addWidget(errors_widget)
        splitter.setSizes([600, 380])
        root.addWidget(splitter)

        # --- Status bar ---
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Prêt. Cliquez sur « Vérifier » pour analyser le texte.")

    # ------------------------------------------------------------------
    # Vérification
    # ------------------------------------------------------------------

    def check_text(self):
        if not self.checker:
            return
        text = self.editor.toPlainText()
        if not text.strip():
            return

        self.btn_check.setEnabled(False)
        self.status.showMessage("Analyse en cours…")
        self.clear_annotations()

        self._thread = CheckerThread(self.checker, text)
        self._thread.results_ready.connect(self._on_results)
        self._thread.error_occurred.connect(self._on_error)
        self._thread.start()

    def _on_results(self, grammar_errors, spell_errors, original_text):
        self.grammar_errors = grammar_errors
        self.spell_errors = spell_errors
        self._apply_annotations(original_text)
        self._populate_error_list()
        total = len(grammar_errors) + len(spell_errors)
        self.status.showMessage(
            f"{total} erreur(s) : {len(grammar_errors)} grammaticale(s), "
            f"{len(spell_errors)} orthographique(s)."
        )
        self.btn_check.setEnabled(True)
        # Activer le bouton seulement si au moins une erreur a une suggestion
        has_suggestions = any(
            e.get("aSuggestions") for e in (self.spell_errors + self.grammar_errors)
        )
        self.btn_apply_all.setEnabled(has_suggestions)

    def _on_contents_changed(self):
        if not self._updating and (self.spell_errors or self.grammar_errors):
            self.clear_annotations()

    def _on_error(self, msg):
        self.status.showMessage(f"Erreur : {msg}")
        self.btn_check.setEnabled(True)

    def _show_error_list_context_menu(self, pos):
        item = self.error_list.itemAt(pos)
        if not item:
            return
        kind, err = item.data(Qt.ItemDataRole.UserRole)
        suggestions = err.get("aSuggestions", [])
        if not suggestions:
            return
        menu = QMenu(self)
        for sugg in suggestions[:6]:
            action = menu.addAction(f"→ {sugg}")
            action.triggered.connect(
                lambda checked, e=err, s=sugg: self._apply_single_suggestion(e, s)
            )
        menu.exec(self.error_list.mapToGlobal(pos))

    def _show_context_menu(self, global_pos, doc_pos):
        all_errors = [("spell", e) for e in self.spell_errors] + \
                     [("grammar", e) for e in self.grammar_errors]
        matching = [(kind, e) for kind, e in all_errors
                    if e["nStart"] <= doc_pos <= e["nEnd"]]

        if not matching:
            self.editor.createStandardContextMenu().exec(global_pos)
            return

        menu = QMenu(self)
        for kind, err in matching:
            suggestions = err.get("aSuggestions", [])
            label = err.get("sValue", "") if kind == "spell" else err.get("sMessage", "")
            menu.addSection(label)
            if suggestions:
                for sugg in suggestions[:6]:
                    action = menu.addAction(f"→ {sugg}")
                    action.triggered.connect(
                        lambda checked, e=err, s=sugg: self._apply_single_suggestion(e, s)
                    )
            else:
                menu.addAction("Aucune suggestion disponible").setEnabled(False)

        menu.exec(global_pos)

    def _apply_single_suggestion(self, err, suggestion):
        self._updating = True
        cursor = self.editor.textCursor()
        cursor.setPosition(err["nStart"])
        cursor.setPosition(err["nEnd"], QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(suggestion)
        self._updating = False
        # Relancer la vérification pour recalculer les offsets sur le nouveau texte
        self.check_text()

    def copy_text(self):
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.status.showMessage("Texte copié dans le presse-papier.")

    def apply_all_suggestions(self):
        """Remplace chaque erreur par sa première suggestion, de la fin vers le début."""
        all_errors = self.spell_errors + self.grammar_errors
        # Garder uniquement les erreurs avec au moins une suggestion
        fixable = [e for e in all_errors if e.get("aSuggestions")]
        if not fixable:
            return

        # Trier de la fin vers le début pour que les offsets restent valides
        fixable.sort(key=lambda e: e["nStart"], reverse=True)

        self._updating = True
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()  # une seule opération annulable (Ctrl+Z)
        applied = 0
        for err in fixable:
            suggestion = err["aSuggestions"][0]
            cursor.setPosition(err["nStart"])
            cursor.setPosition(err["nEnd"], QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(suggestion)
            applied += 1
        cursor.endEditBlock()
        self._updating = False

        self.btn_apply_all.setEnabled(False)
        self.clear_annotations()
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.status.showMessage(
            f"{applied} correction(s) appliquée(s) — texte copié dans le presse-papier. "
            "Cliquez sur « Vérifier » pour une nouvelle analyse."
        )

    # ------------------------------------------------------------------
    # Annotations visuelles
    # ------------------------------------------------------------------

    def _apply_annotations(self, text):
        self._updating = True
        doc = self.editor.document()
        doc.setUndoRedoEnabled(False)

        # Format orthographe : soulignement rouge
        fmt_spell = QTextCharFormat()
        fmt_spell.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        fmt_spell.setUnderlineColor(QColor("red"))

        # Format grammaire : soulignement bleu
        fmt_grammar = QTextCharFormat()
        fmt_grammar.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DashUnderline)
        fmt_grammar.setUnderlineColor(QColor("#0055cc"))

        for err in self.spell_errors:
            self._underline(err["nStart"], err["nEnd"], fmt_spell)

        for err in self.grammar_errors:
            self._underline(err["nStart"], err["nEnd"], fmt_grammar)

        doc.setUndoRedoEnabled(True)
        self._updating = False

    def _underline(self, start, end, fmt):
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.mergeCharFormat(fmt)

    def clear_annotations(self):
        self._updating = True
        doc = self.editor.document()
        doc.setUndoRedoEnabled(False)
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
        cursor.mergeCharFormat(fmt)
        doc.setUndoRedoEnabled(True)
        self._updating = False
        self.error_list.clear()
        self.detail_label.clear()
        self.grammar_errors = []
        self.spell_errors = []
        self.btn_apply_all.setEnabled(False)

    # ------------------------------------------------------------------
    # Liste des erreurs
    # ------------------------------------------------------------------

    def _populate_error_list(self):
        self.error_list.clear()

        tagged = [("spell", e) for e in self.spell_errors] + \
                 [("grammar", e) for e in self.grammar_errors]
        tagged.sort(key=lambda x: x[1]["nStart"])

        for kind, err in tagged:
            if kind == "spell":
                word = err.get("sValue", "?")
                item = QListWidgetItem(f"🔴 Orthographe : « {word} »")
            else:
                msg = err.get("sMessage", "Erreur grammaticale")
                item = QListWidgetItem(f"🔵 Grammaire : {msg}")
            item.setData(Qt.ItemDataRole.UserRole, (kind, err))
            self.error_list.addItem(item)

    def _on_error_clicked(self, item):
        kind, err = item.data(Qt.ItemDataRole.UserRole)

        # Sélectionner le mot dans l'éditeur
        cursor = self.editor.textCursor()
        cursor.setPosition(err["nStart"])
        cursor.setPosition(err["nEnd"], QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

        # Afficher les détails
        if kind == "spell":
            suggestions = err.get("aSuggestions", [])
            sugg_text = ", ".join(suggestions[:6]) if suggestions else "aucune suggestion"
            self.detail_label.setText(
                f"<b>Mot :</b> {err.get('sValue', '')}<br>"
                f"<b>Suggestions :</b> {sugg_text}"
            )
        else:
            self.detail_label.setText(
                f"<b>Règle :</b> {err.get('sRuleId', '')}<br>"
                f"<b>Message :</b> {err.get('sMessage', '')}"
            )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Grammalecte Qt")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
