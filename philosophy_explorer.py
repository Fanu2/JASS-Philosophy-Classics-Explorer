import sys
import sqlite3
import html
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextBrowser, QLineEdit, QLabel,
    QPushButton, QSplitter, QFrame, QMessageBox, QStackedWidget
)

BASE = Path(__file__).resolve().parent
DB = BASE / "JASS_Philosophy_Classics.db"

DARK = """
QMainWindow, QWidget { background:#10131a; color:#e8ecf3; }
QLineEdit { background:#191e28; border:1px solid #394252; border-radius:8px;
            padding:9px 11px; color:#fff; }
QListWidget { background:#151923; border:1px solid #303746; border-radius:8px;
              padding:5px; }
QListWidget::item { padding:9px 7px; border-radius:6px; }
QListWidget::item:selected { background:#34445f; }
QTextBrowser { background:#141821; border:1px solid #303746; border-radius:8px;
               padding:18px; }
QPushButton { background:#27354b; border:1px solid #42526b; border-radius:7px;
              padding:8px 13px; }
QPushButton:hover { background:#354966; }
QLabel#title { font-size:22px; font-weight:700; }
QLabel#section { color:#aebbd0; font-size:13px; }
QLabel#small { color:#9ca9bd; font-size:12px; }
QLabel#panelTitle { font-size:14px; font-weight:700; color:#cbd6e8; }
"""

LIGHT = """
QMainWindow, QWidget { background:#f5f3ee; color:#222; }
QLineEdit, QListWidget, QTextBrowser { background:#fff; color:#222;
    border:1px solid #ccc; border-radius:8px; padding:8px; }
QListWidget::item { padding:9px 7px; border-radius:6px; }
QListWidget::item:selected { background:#d9e2ef; }
QPushButton { padding:8px 13px; border:1px solid #bbb; border-radius:7px;
              background:#eee; color:#222; }
QLabel#title { font-size:22px; font-weight:700; }
QLabel#section, QLabel#small { color:#666; font-size:13px; }
QLabel#panelTitle { font-size:14px; font-weight:700; color:#333; }
"""

class Explorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JASS Philosophy Classics Explorer")
        self.resize(1500, 860)
        self.con = sqlite3.connect(DB)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS bookmarks "
            "(passage_id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        self.con.commit()
        self.dark = True
        self.results = []
        self.current_id = None
        self.current_row = -1
        self.font_size = 20
        self.build_ui()
        self.load_initial()

    def build_ui(self):
        root = QWidget()
        main = QVBoxLayout(root)
        main.setContentsMargins(18, 16, 18, 14)
        main.setSpacing(8)

        # Compact header
        top = QHBoxLayout()
        title = QLabel("JASS Philosophy Classics")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search philosophy, concepts, passages…")
        self.search.setMinimumWidth(430)
        self.search.returnPressed.connect(self.search_text)
        top.addWidget(self.search)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_text)
        top.addWidget(search_btn)

        self.bookmarks_btn = QPushButton("★ Bookmarks")
        self.bookmarks_btn.clicked.connect(self.show_bookmarks)
        top.addWidget(self.bookmarks_btn)

        theme = QPushButton("Toggle Theme")
        theme.clicked.connect(self.toggle_theme)
        top.addWidget(theme)

        main.addLayout(top)

        self.info = QLabel("49,096 searchable passages • 1.62 million words • offline")
        self.info.setObjectName("section")
        main.addWidget(self.info)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        # LEFT
        left = QFrame()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 8, 0)
        ll.addWidget(QLabel("SEARCH RESULTS"))

        self.list = QListWidget()
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.ElideRight)
        self.list.itemClicked.connect(self.show_item)
        ll.addWidget(self.list)

        split.addWidget(left)

        # CENTER
        center = QFrame()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(8, 0, 8, 0)

        self.heading = QLabel("Welcome to Philosophy Classics")
        self.heading.setObjectName("title")
        cl.addWidget(self.heading)

        self.meta = QLabel("Select a passage or search the collection.")
        self.meta.setObjectName("section")
        cl.addWidget(self.meta)

        self.reader = QTextBrowser()
        self.reader.setOpenExternalLinks(False)
        cl.addWidget(self.reader, 1)

        controls = QHBoxLayout()
        self.prev = QPushButton("◀ Previous")
        self.prev.clicked.connect(self.previous)
        controls.addWidget(self.prev)

        copy_btn = QPushButton("Copy Passage")
        copy_btn.clicked.connect(self.copy_passage)
        controls.addWidget(copy_btn)

        smaller = QPushButton("A−")
        smaller.setToolTip("Decrease reading font")
        smaller.clicked.connect(lambda: self.change_font(-1))
        controls.addWidget(smaller)

        larger = QPushButton("A+")
        larger.setToolTip("Increase reading font")
        larger.clicked.connect(lambda: self.change_font(1))
        controls.addWidget(larger)

        controls.addStretch()

        self.bookmark = QPushButton("☆ Bookmark")
        self.bookmark.clicked.connect(self.toggle_bookmark)
        controls.addWidget(self.bookmark)

        self.next = QPushButton("Next ▶")
        self.next.clicked.connect(self.next_item)
        controls.addWidget(self.next)

        cl.addLayout(controls)
        split.addWidget(center)

        # RIGHT
        right = QFrame()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        panel = QLabel("PASSAGE INFORMATION")
        panel.setObjectName("panelTitle")
        rl.addWidget(panel)

        self.details = QLabel()
        self.details.setObjectName("small")
        self.details.setWordWrap(True)
        rl.addWidget(self.details)

        rl.addSpacing(18)

        panel2 = QLabel("COLLECTION")
        panel2.setObjectName("panelTitle")
        rl.addWidget(panel2)

        self.collection = QLabel(
            "<b>JASS Philosophy Classics</b><br><br>"
            "49,096 searchable passages<br>"
            "2,257 reading chunks<br>"
            "1.62 million words<br><br>"
            "SQLite + FTS5<br>"
            "Offline / local-first"
        )
        self.collection.setObjectName("small")
        self.collection.setWordWrap(True)
        rl.addWidget(self.collection)

        rl.addSpacing(18)

        panel3 = QLabel("METADATA")
        panel3.setObjectName("panelTitle")
        rl.addWidget(panel3)

        self.metadata_note = QLabel(
            "Author/work metadata is not reliably supplied for every passage. "
            "No philosopher attribution is invented by this Explorer."
        )
        self.metadata_note.setObjectName("small")
        self.metadata_note.setWordWrap(True)
        rl.addWidget(self.metadata_note)
        rl.addStretch()

        split.addWidget(right)

        split.setSizes([315, 860, 300])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)

        main.addWidget(split, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(DARK)

    def load_initial(self):
        cur = self.con.execute(
            "SELECT id, source_line, text FROM passages ORDER BY id LIMIT 250"
        )
        rows = cur.fetchall()
        self.populate(rows, "49,096 searchable passages • 1.62 million words • offline")

        if rows:
            self.list.setCurrentRow(0)
            self.show_item(self.list.item(0))

    def populate(self, rows, status=None):
        self.list.clear()
        self.results = [r[0] for r in rows]
        for pid, line, text in rows:
            preview = " ".join(text.split())
            if len(preview) > 72:
                preview = preview[:72].rstrip() + "…"

            item = QListWidgetItem()
            item.setData(Qt.UserRole, pid)
            item.setToolTip(text)
            item.setText(f"Passage {pid:05d}  •  {preview}")
            self.list.addItem(item)

        if status:
            self.info.setText(status)

    def search_text(self):
        q = self.search.text().strip()
        if not q:
            self.load_initial()
            return

        try:
            cur = self.con.execute(
                """SELECT p.id, p.source_line, p.text
                   FROM passages_fts f
                   JOIN passages p ON p.id=f.rowid
                   WHERE passages_fts MATCH ?
                   LIMIT 500""", (q,)
            )
            rows = cur.fetchall()
        except sqlite3.Error:
            cur = self.con.execute(
                "SELECT id, source_line, text FROM passages "
                "WHERE text LIKE ? LIMIT 500", (f"%{q}%",)
            )
            rows = cur.fetchall()

        self.populate(
            rows,
            f"{len(rows):,} matches • Full-text search"
        )
        if rows:
            self.list.setCurrentRow(0)
            self.show_item(self.list.item(0))
        else:
            self.heading.setText("No matches")
            self.meta.setText("")
            self.reader.setHtml(
                "<div style='font-size:18px;'>No passages matched your search.</div>"
            )

    def show_bookmarks(self):
        rows = self.con.execute(
            """SELECT p.id, p.source_line, p.text
               FROM bookmarks b
               JOIN passages p ON p.id=b.passage_id
               ORDER BY b.created_at DESC"""
        ).fetchall()

        self.populate(rows, f"{len(rows):,} bookmarked passages")
        if rows:
            self.list.setCurrentRow(0)
            self.show_item(self.list.item(0))
        else:
            self.heading.setText("No bookmarks yet")
            self.meta.setText("Bookmark passages while reading.")
            self.reader.setHtml(
                "<div style='font-size:18px;'>Your saved passages will appear here.</div>"
            )

    def show_item(self, item):
        if not item:
            return
        pid = item.data(Qt.UserRole)
        row = self.con.execute(
            "SELECT id, source_line, text FROM passages WHERE id=?", (pid,)
        ).fetchone()
        if not row:
            return

        self.current_id = row[0]
        self.current_row = self.list.currentRow()

        self.heading.setText(f"Passage {row[0]:,}")
        words = len(row[2].split())
        chars = len(row[2])
        self.meta.setText(
            f"Source line {row[1]:,}  •  {words:,} words  •  {chars:,} characters"
        )

        query = self.search.text().strip()
        content = html.escape(row[2])
        if query and len(query) < 100:
            # Highlight plain search words without changing the stored text.
            terms = [t.strip('"') for t in query.replace("OR", " ").split()
                     if t.strip() and t.upper() not in {"AND", "OR", "NOT"}]
            for term in sorted(set(terms), key=len, reverse=True):
                if len(term) > 80:
                    continue
                import re
                pattern = re.compile(re.escape(html.escape(term)), re.I)
                content = pattern.sub(
                    lambda m: f"<mark>{m.group(0)}</mark>", content
                )

        self.reader.setHtml(
            f"<div style='font-size:{self.font_size}px; line-height:1.7;'>{content}</div>"
        )

        self.details.setText(
            f"<b>Passage</b><br>{row[0]:,}<br><br>"
            f"<b>Source line</b><br>{row[1]:,}<br><br>"
            f"<b>Words</b><br>{words:,}<br><br>"
            f"<b>Characters</b><br>{chars:,}<br><br>"
            f"<b>Metadata status</b><br>Source text preserved; "
            f"author/work not inferred."
        )

        bookmarked = self.con.execute(
            "SELECT 1 FROM bookmarks WHERE passage_id=?", (row[0],)
        ).fetchone() is not None
        self.bookmark.setText("★ Bookmarked" if bookmarked else "☆ Bookmark")

    def copy_passage(self):
        if self.current_id is None:
            return
        row = self.con.execute(
            "SELECT text FROM passages WHERE id=?", (self.current_id,)
        ).fetchone()
        if row:
            QApplication.clipboard().setText(row[0])
            self.info.setText("Passage copied to clipboard.")

    def toggle_bookmark(self):
        if self.current_id is None:
            return
        exists = self.con.execute(
            "SELECT 1 FROM bookmarks WHERE passage_id=?", (self.current_id,)
        ).fetchone()
        if exists:
            self.con.execute(
                "DELETE FROM bookmarks WHERE passage_id=?", (self.current_id,)
            )
            self.bookmark.setText("☆ Bookmark")
            self.info.setText("Bookmark removed.")
        else:
            self.con.execute(
                "INSERT INTO bookmarks(passage_id) VALUES (?)", (self.current_id,)
            )
            self.bookmark.setText("★ Bookmarked")
            self.info.setText("Passage bookmarked.")
        self.con.commit()

    def change_font(self, delta):
        self.font_size = max(14, min(32, self.font_size + delta * 2))
        if self.current_id is not None:
            item = self.list.currentItem()
            if item:
                self.show_item(item)

    def previous(self):
        if self.list.count():
            i = max(0, self.list.currentRow() - 1)
            self.list.setCurrentRow(i)
            self.show_item(self.list.item(i))

    def next_item(self):
        if self.list.count():
            i = min(self.list.count() - 1, self.list.currentRow() + 1)
            self.list.setCurrentRow(i)
            self.show_item(self.list.item(i))

    def toggle_theme(self):
        self.dark = not self.dark
        self.setStyleSheet(DARK if self.dark else LIGHT)

    def closeEvent(self, event):
        self.con.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("JASS Philosophy Classics Explorer")
    w = Explorer()
    w.show()
    sys.exit(app.exec())
