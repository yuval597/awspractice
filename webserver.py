import http.server
import socketserver
import cgi
import boto3
import html
from urllib.parse import urlparse, parse_qs, quote, unquote

PORT = 8000
BUCKET = "yuvalschbucket"

s3 = boto3.client("s3")


def list_s3_files():
    response = s3.list_objects_v2(Bucket=BUCKET)
    files = []
    if "Contents" in response:
        for obj in response["Contents"]:
            files.append(obj["Key"])
    files.sort(key=lambda x: x.lower())
    return files


def safe_html(text: str) -> str:
    return html.escape(text, quote=True)


class UploadHandler(http.server.BaseHTTPRequestHandler):

    def send_html(self, content: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)

        # ---------- DOWNLOAD ----------
        if parsed.path == "/download":
            params = parse_qs(parsed.query)
            filename = params.get("file", [None])[0]
            if not filename:
                self.send_error(400, "Missing file name")
                return

            filename = unquote(filename)

            try:
                obj = s3.get_object(Bucket=BUCKET, Key=filename)
                data = obj["Body"].read()

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"'
                )
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Download failed: {e}")
            return

        # ---------- MAIN PAGE ----------
        try:
            files = list_s3_files()
        except Exception as e:
            files = []
            error_msg = f"S3 list failed: {e}"
        else:
            error_msg = ""

        file_rows = ""
        if files:
            for f in files:
                f_safe = safe_html(f)
                f_url = quote(f)
                file_rows += f"""
                <div class="row">
                    <div class="left">
                        <div class="dot" aria-hidden="true"></div>
                        <div class="name" title="{f_safe}">{f_safe}</div>
                    </div>

                    <div class="actions">
                        <a class="btn btn-secondary" href="/download?file={f_url}">Download</a>

                        <form method="post" action="/delete" onsubmit="return confirmDelete('{f_safe}')">
                            <input type="hidden" name="file" value="{f_safe}">
                            <button type="submit" class="btn btn-danger">Delete</button>
                        </form>
                    </div>
                </div>
                """
        else:
            file_rows = """
            <div class="empty">
                <div class="empty-title">No files</div>
                <div class="empty-sub">Upload a file to see it listed here.</div>
            </div>
            """

        error_banner = ""
        if error_msg:
            error_banner = f"""
            <div class="alert">
                <div class="alert-title">Something went wrong</div>
                <div class="alert-text">{safe_html(error_msg)}</div>
            </div>
            """

        page = f"""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>S3 Drive</title>
            <style>
                :root {{
                    --bg0: #f5f5f7;
                    --bg1: rgba(255,255,255,0.72);
                    --line: rgba(0,0,0,0.10);
                    --text: rgba(0,0,0,0.88);
                    --muted: rgba(0,0,0,0.52);
                    --shadow: 0 18px 60px rgba(0,0,0,0.12);
                    --shadow2: 0 10px 30px rgba(0,0,0,0.10);

                    --btn: rgba(0,0,0,0.06);
                    --btnHover: rgba(0,0,0,0.09);
                    --btnText: rgba(0,0,0,0.86);

                    --danger: rgba(255, 59, 48, 0.12);
                    --dangerHover: rgba(255, 59, 48, 0.16);
                    --dangerText: rgba(150, 0, 0, 0.90);

                    --radius: 18px;
                }}

                * {{ box-sizing: border-box; }}

                body {{
                    margin: 0;
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, Arial, sans-serif;
                    color: var(--text);
                    background:
                        radial-gradient(900px 500px at 10% 0%, rgba(0,0,0,0.06), transparent 55%),
                        radial-gradient(900px 500px at 90% 10%, rgba(0,0,0,0.05), transparent 60%),
                        var(--bg0);
                    min-height: 100vh;
                    padding: 34px 16px;
                    display: flex;
                    justify-content: center;
                }}

                .wrap {{
                    width: 100%;
                    max-width: 980px;
                }}

                .header {{
                    display: flex;
                    align-items: flex-end;
                    justify-content: space-between;
                    gap: 12px;
                    margin-bottom: 18px;
                }}

                .title {{
                    font-size: 28px;
                    font-weight: 750;
                    letter-spacing: -0.02em;
                    line-height: 1.15;
                    margin: 0;
                }}

                .sub {{
                    margin-top: 6px;
                    color: var(--muted);
                    font-size: 13px;
                }}

                .pill {{
                    padding: 10px 12px;
                    border: 1px solid var(--line);
                    border-radius: 999px;
                    background: rgba(255,255,255,0.55);
                    backdrop-filter: blur(14px);
                    -webkit-backdrop-filter: blur(14px);
                    box-shadow: var(--shadow2);
                    color: var(--muted);
                    font-size: 12px;
                    white-space: nowrap;
                }}

                .grid {{
                    display: grid;
                    grid-template-columns: 1fr;
                    gap: 14px;
                }}

                @media (min-width: 900px) {{
                    .grid {{
                        grid-template-columns: 360px 1fr;
                        align-items: start;
                    }}
                }}

                .card {{
                    background: var(--bg1);
                    border: 1px solid var(--line);
                    border-radius: var(--radius);
                    box-shadow: var(--shadow);
                    backdrop-filter: blur(18px);
                    -webkit-backdrop-filter: blur(18px);
                    overflow: hidden;
                }}

                .card-head {{
                    padding: 16px 18px 12px;
                    border-bottom: 1px solid rgba(0,0,0,0.06);
                }}

                .card-title {{
                    font-size: 14px;
                    font-weight: 700;
                    letter-spacing: -0.01em;
                }}

                .card-body {{
                    padding: 18px;
                }}

                .hint {{
                    color: var(--muted);
                    font-size: 12px;
                    line-height: 1.5;
                    margin-bottom: 12px;
                }}

                input[type="file"] {{
                    width: 100%;
                    padding: 14px;
                    border-radius: 14px;
                    border: 1px solid rgba(0,0,0,0.10);
                    background: rgba(255,255,255,0.72);
                    color: var(--muted);
                    outline: none;
                }}

                input[type="file"]:focus {{
                    border-color: rgba(0,0,0,0.22);
                }}

                .btn {{
                    border: 1px solid rgba(0,0,0,0.10);
                    background: var(--btn);
                    color: var(--btnText);
                    padding: 10px 14px;
                    border-radius: 999px;
                    font-weight: 650;
                    font-size: 13px;
                    cursor: pointer;
                    transition: background 0.12s ease, transform 0.05s ease;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                }}

                .btn:hover {{
                    background: var(--btnHover);
                }}

                .btn:active {{
                    transform: translateY(1px);
                }}

                .btn-primary {{
                    background: rgba(0,0,0,0.86);
                    border-color: rgba(0,0,0,0.86);
                    color: rgba(255,255,255,0.92);
                }}

                .btn-primary:hover {{
                    background: rgba(0,0,0,0.92);
                }}

                .btn-secondary {{
                    background: rgba(255,255,255,0.72);
                }}

                .btn-secondary:hover {{
                    background: rgba(255,255,255,0.90);
                }}

                .btn-danger {{
                    background: var(--danger);
                    color: var(--dangerText);
                    border-color: rgba(255, 59, 48, 0.18);
                }}

                .btn-danger:hover {{
                    background: var(--dangerHover);
                }}

                .rows {{
                    padding: 6px 0;
                }}

                .row {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    padding: 12px 18px;
                    border-top: 1px solid rgba(0,0,0,0.06);
                }}

                .row:hover {{
                    background: rgba(255,255,255,0.35);
                }}

                .left {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    min-width: 0;
                }}

                .dot {{
                    width: 9px;
                    height: 9px;
                    border-radius: 999px;
                    background: rgba(0,0,0,0.26);
                    flex: 0 0 auto;
                }}

                .name {{
                    font-size: 13px;
                    font-weight: 650;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    max-width: 520px;
                }}

                .actions {{
                    display: flex;
                    gap: 10px;
                    align-items: center;
                    flex-wrap: wrap;
                }}

                form {{ margin: 0; }}

                .empty {{
                    padding: 34px 18px;
                    text-align: center;
                    color: var(--muted);
                }}

                .empty-title {{
                    font-weight: 750;
                    color: var(--text);
                    margin-bottom: 6px;
                }}

                .alert {{
                    margin-bottom: 14px;
                    border: 1px solid rgba(255, 59, 48, 0.20);
                    background: rgba(255, 59, 48, 0.09);
                    border-radius: var(--radius);
                    padding: 14px 16px;
                }}

                .alert-title {{
                    font-weight: 750;
                    margin-bottom: 4px;
                }}

                .alert-text {{
                    color: rgba(0,0,0,0.64);
                    font-size: 12px;
                    line-height: 1.35;
                }}

                .footer {{
                    margin-top: 12px;
                    color: var(--muted);
                    font-size: 12px;
                    text-align: center;
                }}

                .mono {{
                    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
                    font-size: 12px;
                }}
            </style>

            <script>
                function confirmDelete(name) {{
                    return confirm("Delete from S3?\\n\\n" + name);
                }}
            </script>
        </head>

        <body>
            <div class="wrap">
                <div class="header">
                    <div>
                        <h1 class="title">S3 Drive</h1>
                        <div class="sub">Bucket: <span class="mono">{safe_html(BUCKET)}</span></div>
                    </div>
                    <div class="pill">EC2 • HTTP • Port {PORT}</div>
                </div>

                {error_banner}

                <div class="grid">
                    <div class="card">
                        <div class="card-head">
                            <div class="card-title">Upload</div>
                        </div>
                        <div class="card-body">
                            <div class="hint">
                                Choose a file and upload it directly to S3.<br>
                                Your files will appear in the list on the right.
                            </div>

                            <form enctype="multipart/form-data" method="post" action="/upload">
                                <input type="file" name="file" required>
                                <div style="margin-top: 12px;">
                                    <button class="btn btn-primary" type="submit">Upload</button>
                                </div>
                            </form>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-head">
                            <div class="card-title">Files</div>
                        </div>
                        <div class="rows">
                            {file_rows}
                        </div>
                    </div>
                </div>

                <div class="footer">
                    Minimal UI • Upload / Download / Delete
                </div>
            </div>
        </body>
        </html>
        """

        self.send_html(page)

    def do_POST(self):
        parsed = urlparse(self.path)

        # ---------- UPLOAD ----------
        if parsed.path == "/upload":
            try:
                ctype, _ = cgi.parse_header(self.headers.get("Content-Type", ""))
                if ctype != "multipart/form-data":
                    self.send_error(400, "Invalid form (expected multipart/form-data)")
                    return

                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={"REQUEST_METHOD": "POST"}
                )

                file_field = form["file"]
                filename = file_field.filename

                if not filename:
                    self.send_error(400, "No file selected")
                    return

                s3.upload_fileobj(file_field.file, BUCKET, filename)

                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()

            except Exception as e:
                self.send_error(500, f"Upload failed: {e}")
            return

        # ---------- DELETE ----------
        if parsed.path == "/delete":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8", errors="ignore")
                params = parse_qs(body)

                filename = params.get("file", [None])[0]
                if not filename:
                    self.send_error(400, "Missing file name")
                    return

                filename = html.unescape(filename)

                s3.delete_object(Bucket=BUCKET, Key=filename)

                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()

            except Exception as e:
                self.send_error(500, f"Delete failed: {e}")
            return

        self.send_error(404, "Not found")


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), UploadHandler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()
