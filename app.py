# formatted using black
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
)
import os
import sqlite3
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(64)
DB_NAME = "storage.db"
PASSWORD = "admin"


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


def create_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            upload_date TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def generate_file_id():
    return secrets.token_hex(6)


@app.route("/")
def index():
    if "has_admin" in request.cookies and request.cookies["has_admin"] == "True":
        return redirect(url_for("admin"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    password = request.form.get("password")
    if password == PASSWORD:
        r = redirect(url_for("admin"))
        r.set_cookie("has_admin", "True")
        return r
    flash("Wrong password !")
    return redirect(url_for("index"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "has_admin" in request.cookies and request.cookies["has_admin"] == "True":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        sort_by = request.args.get("sort_by", "")
        query = request.args.get("query", "")
        if sort_by == "f_a":
            cursor.execute(
                "SELECT * FROM files WHERE file_name LIKE ? ORDER BY file_name ASC",
                ("%" + query + "%",),
            )
        elif sort_by == "f_d":
            cursor.execute(
                "SELECT * FROM files WHERE file_name LIKE ? ORDER BY file_name DESC",
                ("%" + query + "%",),
            )
        elif sort_by == "d_d":
            cursor.execute(
                "SELECT * FROM files WHERE file_name LIKE ? ORDER BY upload_date DESC",
                ("%" + query + "%",),
            )
        else:
            cursor.execute(
                "SELECT * FROM files WHERE file_name LIKE ? ORDER BY upload_date ASC",
                ("%" + query + "%",),
            )

        files = cursor.fetchall()
        conn.close()
        return render_template("admin.html", files=files, query=query)
    return redirect(url_for("index"))


@app.route("/upload", methods=["POST"])
def upload():
    if "has_admin" in request.cookies and request.cookies["has_admin"] == "True":
        files = request.files.getlist("files")
        for file in files:
            filename = file.filename
            file_id = generate_file_id()
            file.save(os.path.join("uploads", filename))

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO files (id, file_name, upload_date) VALUES (?, ?, datetime("now"))',
                (
                    file_id,
                    filename,
                ),
            )
            conn.commit()
            conn.close()

        flash("Files uploaded successfully!")
    return redirect(url_for("admin"))


@app.route("/delete/<string:file_id>", methods=["GET", "POST"])
def delete(file_id):
    if "has_admin" in request.cookies and request.cookies["has_admin"] == "True":
        if request.method == "POST":
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT file_name FROM files WHERE id = ?", (file_id,))
            file_name = cursor.fetchone()[0]
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
            conn.close()

            os.remove(os.path.join("uploads", file_name))

            flash("File deleted successfully")
            return redirect(url_for("admin"))

        return render_template("delete.html", file_id=file_id)
    return redirect(url_for("index"))


@app.route("/download/<path:filename>")
def download(filename):
    if "has_admin" in request.cookies and request.cookies["has_admin"] == "True":
        return send_from_directory("uploads", filename, as_attachment=True)
    return redirect(url_for("index"))


@app.route("/share/<string:file_id>", methods=["GET", "POST"])
def share(file_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_name FROM files WHERE id = ?", (file_id,))
    file_name = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return send_from_directory("uploads", file_name, as_attachment=False)


if __name__ == "__main__":
    create_table()
    app.run(debug=False)
