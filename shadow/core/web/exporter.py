import os
import json
import csv
import sqlite3
from typing import Dict, Any, List, Optional

class WebDataExporter:
    @staticmethod
    def export_markdown(data: List[Dict[str, Any]], filepath: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("# Web Intelligence Export\n\n")
                for item in data:
                    f.write(f"## URL: {item.get('url')}\n")
                    f.write(f"**Depth**: {item.get('depth', 0)}\n\n")
                    f.write(f"{item.get('content', '')}\n\n")
                    f.write("---\n\n")
            return True
        except Exception:
            return False

    @staticmethod
    def export_json(data: List[Dict[str, Any]], filepath: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    @staticmethod
    def export_csv(data: List[Dict[str, Any]], filepath: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["url", "depth", "title", "content_preview"])
                for item in data:
                    meta = item.get("metadata") or {}
                    title = meta.get("title") or ""
                    content = item.get("content") or ""
                    writer.writerow([
                        item.get("url"),
                        item.get("depth", 0),
                        title,
                        content[:200].replace("\n", " ") + "..."
                    ])
            return True
        except Exception:
            return False

    @staticmethod
    def export_sqlite(data: List[Dict[str, Any]], filepath: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            conn = sqlite3.connect(filepath)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS web_exports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    depth INTEGER,
                    title TEXT,
                    content TEXT
                )
            """)
            for item in data:
                meta = item.get("metadata") or {}
                title = meta.get("title") or ""
                cursor.execute("""
                    INSERT INTO web_exports (url, depth, title, content)
                    VALUES (?, ?, ?, ?)
                """, (item.get("url"), item.get("depth", 0), title, item.get("content")))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    @staticmethod
    def export_html(data: List[Dict[str, Any]], filepath: str) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("<!DOCTYPE html><html><head><meta charset='utf-8'><title>Export</title>")
                f.write("<style>body{font-family:sans-serif;padding:30px;} .item{border-bottom:1px solid #ccc;padding:20px 0;}</style>")
                f.write("</head><body><h1>Web Intelligence Export</h1>")
                for item in data:
                    meta = item.get("metadata") or {}
                    title = meta.get("title") or "Page"
                    f.write("<div class='item'>")
                    f.write(f"<h2><a href='{item.get('url')}'>{title}</a></h2>")
                    f.write(f"<p><strong>Depth:</strong> {item.get('depth', 0)}</p>")
                    f.write(f"<pre style='white-space:pre-wrap;'>{item.get('content')}</pre>")
                    f.write("</div>")
                f.write("</body></html>")
            return True
        except Exception:
            return False

    @staticmethod
    def export_pdf(data: List[Dict[str, Any]], filepath: str) -> bool:
        # Standard PDF binary layout mockup
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(b"%PDF-1.4\n%mock PDF export of Web Intelligence")
            return True
        except Exception:
            return False
