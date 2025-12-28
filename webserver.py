import http.server
import socketserver
import cgi
import boto3
import html
from urllib.parse import urlparse, parse_qs, quote, unquote

PORT = 8000
BUCKET = "yuvalschbucket"

s3 = boto3.client("s3")


def safe(s: str) -> str:
    return html.escape(s, quote=True)


def list_s3_files():
    # Basic listing (no pagination) – OK for labs/small buckets
    resp = s3.list_objects_v2(Bucket=BUCKET)
    files = []
    if "Contents" in resp:
        for obj in resp["Contents"]:
            files.append(obj["Key"])
    files.sort(key=lambda x: x.lower())
    return files


def render_page(files, bucket_name, toast_msg=""):
    # Build rows
    rows = ""
    if files:
        for f in files:
            f_safe = safe(f)
            f_url = quote(f)
            rows += f"""
            <tr class="row">
              <td class="name-cell" title="{f_safe}">
                <span class="file-icon" aria-hidden="true"></span>
                <span class="file-name">{f_safe}</span>
              </td>
              <td class="actions-cell">
                <a class="btn btn-ghost" href="/download?file={f_url}">
                  <span class="btn-ic">⤓</span> Download
                </a>
                <form class="inline" method="post" action="/delete" onsubmit="return confirmDelete('{f_safe}')">
                  <input type="hidden" name="file" value="{f_safe}">
                  <button class="btn btn-danger" type="submit">
                    <span class="btn-ic">⌫</span> Delete
                  </button>
                </form>
              </td>
            </tr>
            """
    else:
        rows = """
        <tr>
          <td colspan="2" class="empty">
            <div class="empty-title">No files yet</div>
            <div class="empty-sub">Upload something — it will appear here instantly.</div>
          </td>
        </tr>
        """

    toast_block = ""
    if toast_msg:
        toast_block = f"""
        <div id="toast" class="toast show">
          <div class="toast-dot"></div>
          <div class="toast-text">{safe(toast_msg)}</div>
          <button class="toast-x" onclick="hideToast()" aria-label="Close">×</button>
        </div>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>S3 Glass Drive</title>
  <style>
    :root {{
      --bg0: #0b0f1a;
      --bg1: #0f172a;
      --ink: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.62);
      --muted2: rgba(255,255,255,0.45);

      --glass: rgba(255,255,255,0.10);
      --glass2: rgba(255,255,255,0.06);
      --line: rgba(255,255,255,0.16);

      --shadow: 0 20px 70px rgba(0,0,0,0.55);
      --shadow2: 0 12px 40px rgba(0,0,0,0.35);

      --btn: rgba(255,255,255,0.10);
      --btnHover: rgba(255,255,255,0.16);

      --danger: rgba(255, 85, 85, 0.14);
      --dangerHover: rgba(255, 85, 85, 0.20);
      --dangerLine: rgba(255, 85, 85, 0.26);

      --radius: 22px;
      --radius2: 16px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
                   "Segoe UI", Roboto, Arial, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 600px at 20% 10%, rgba(120, 119, 198, 0.35), transparent 60%),
        radial-gradient(900px 600px at 80% 20%, rgba(56, 189, 248, 0.22), transparent 55%),
        radial-gradient(800px 550px at 55% 85%, rgba(34, 197, 94, 0.12), transparent 60%),
        linear-gradient(180deg, var(--bg0), var(--bg1));
      min-height: 100vh;
      padding: 42px 18px;
      display: flex;
      justify-content: center;
    }}

    .wrap {{
      width: 100%;
      max-width: 1100px;
    }}

    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 18px;
      margin-bottom: 18px;
    }}

    .brand {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    .title {{
      margin: 0;
      font-size: 30px;
      font-weight: 780;
      letter-spacing: -0.02em;
    }}

    .subtitle {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }}

    .pill {{
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      box-shadow: var(--shadow2);
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}

    .glass {{
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.06));
      backdrop-filter: blur(22px);
      -webkit-backdrop-filter: blur(22px);
      box-shadow: var(--shadow);
      border-radius: var(--radius);
      overflow: hidden;
    }}

    .grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }}

    @media (min-width: 980px) {{
      .grid {{
        grid-template-columns: 380px 1fr;
        align-items: start;
      }}
    }}

    .card-head {{
      padding: 18px 20px 14px;
      border-bottom: 1px solid rgba(255,255,255,0.10);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}

    .card-title {{
      font-weight: 760;
      font-size: 14px;
      letter-spacing: -0.01em;
      color: rgba(255,255,255,0.88);
    }}

    .card-body {{
      padding: 18px 20px 20px;
    }}

    .hint {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
      margin-bottom: 12px;
    }}

    .upload-box {{
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.18);
      border-radius: var(--radius2);
      padding: 14px;
    }}

    input[type="file"] {{
      width: 100%;
      padding: 14px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.06);
      color: var(--muted);
      outline: none;
    }}

    input[type="file"]::file-selector-button {{
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.10);
      color: rgba(255,255,255,0.86);
      border-radius: 999px;
      padding: 10px 12px;
      margin-right: 12px;
      cursor: pointer;
    }}

    input[type="file"]::file-selector-button:hover {{
      background: rgba(255,255,255,0.16);
    }}

    .btn {{
      border: 1px solid rgba(255,255,255,0.14);
      background: var(--btn);
      color: rgba(255,255,255,0.90);
      padding: 10px 14px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      transition: transform 0.06s ease, background 0.14s ease;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      user-select: none;
    }}

    .btn:hover {{
      background: var(--btnHover);
    }}

    .btn:active {{
      transform: translateY(1px);
    }}

    .btn-primary {{
      background: rgba(255,255,255,0.14);
      border-color: rgba(255,255,255,0.18);
    }}

    .btn-primary:hover {{
      background: rgba(255,255,255,0.20);
    }}

    .btn-ghost {{
      background: rgba(255,255,255,0.08);
    }}

    .btn-danger {{
      background: var(--danger);
      border-color: var(--dangerLine);
      color: rgba(255, 170, 170, 0.98);
    }}

    .btn-danger:hover {{
      background: var(--dangerHover);
    }}

    .btn-ic {{
      opacity: 0.9;
      font-size: 13px;
      line-height: 1;
    }}

    .table-wrap {{
      padding: 6px 0 2px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
    }}

    thead th {{
      text-align: left;
      padding: 12px 20px;
      color: var(--muted2);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-bottom: 1px solid rgba(255,255,255,0.10);
    }}

    tbody td {{
      padding: 14px 20px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }}

    tr.row:hover td {{
      background: rgba(255,255,255,0.04);
    }}

    .name-cell {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }}

    .file-icon {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.28);
      flex: 0 0 auto;
      box-shadow: 0 0 0 3px rgba(255,255,255,0.06);
    }}

    .file-name {{
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 520px;
      font-weight: 720;
      font-size: 13px;
      color: rgba(255,255,255,0.90);
    }}

    .actions-cell {{
      text-align: right;
      white-space: nowrap;
    }}

    .inline {{ display: inline; }}

    .actions-cell .btn {{
      margin-left: 10px;
    }}

    .empty {{
      padding: 34px 20px;
      text-align: center;
      color: var(--muted);
    }}

    .empty-title {{
      color: rgba(255,255,255,0.92);
      font-weight: 820;
      margin-bottom: 6px;
    }}

    .empty-sub {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}

    .footer {{
      margin-top: 14px;
      text-align: center;
      color: var(--muted2);
      font-size: 12px;
    }}

    /* Toast */
    .toast {{
      position: fixed;
      left: 50%;
      bottom: 18px;
      transform: translateX(-50%) translateY(20px);
      opacity: 0;
      pointer-events: none;

      display: flex;
      align-items: center;
      gap: 10px;

      padding: 12px 14px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(15, 23, 42, 0.40);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      box-shadow: var(--shadow2);
      transition: opacity 0.18s ease, transform 0.18s ease;
      max-width: calc(100vw - 24px);
    }}

    .toast.show {{
      opacity: 1;
      transform: translateX(-50%) translateY(0);
      pointer-events: auto;
    }}

    .toast-dot {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: rgba(34, 197, 94, 0.9);
      box-shadow: 0 0 0 4px rgba(34,197,94,0.14);
      flex: 0 0 auto;
    }}

    .toast-text {{
      color: rgba(255,255,255,0.88);
      font-size: 13px;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .toast-x {{
      margin-left: 6px;
      width: 28px;
      height: 28px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.16);
      background: rgba(255,255,255,0.06);
      color: rgba(255,255,255,0.85);
      cursor: pointer;
      font-size: 18px;
      line-height: 26px;
      padding: 0;
    }}

    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }}
  </style>

  <script>
    function confirmDelete(name) {{
      return confirm("Delete from S3?\\n\\n" + name);
    }}

    function hideToast() {{
      const t = document.getElementById("toast");
      if (t) t.classList.remove("show");
    }}

    window.addEventListener("load", () => {{
      const t = document.getElementById("toast");
      if (t) {{
        setTimeout(() => {{
          t.classList.remove("show");
        }}, 2600);
      }}
    }});
  </script>
</head>

<body>
  {toast_block}
  <div class="wrap">
    <div class="topbar">
      <div class="brand">
        <h1 class="title">S3 Glass Drive</h1>
        <div class="subtitle">
          Bucket: <span class="mono">{safe(bucket_name)}</span> • Port: <span class="mono">{PORT}</span>
        </div>
      </div>
      <div class="pill">Upload • Download • Delete</div>
    </div>

    <div class="grid">
      <section class="glass">
        <div class="card-head">
          <div class="card-title">Upload</div>
        </div>
        <div class="card-body">
          <div class="hint">
            Choose a file and upload it directly to S3. This interface is intentionally minimal and clean.
          </div>

          <div class="upload-box">
            <form enctype="multipart/form-data" method="post" action="/upload">
              <input type="file" name="file" required />
              <div style="margin-top: 12px;">
                <button class="btn btn-primary" type="submit">
                  <span class="btn-ic">↑</span> Upload to S3
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

      <section class="glass">
        <div class="card-head">
          <div class="card-title">Files</div>
          <div class="subtitle">Live list from S3</div>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Object Key</th>
                <th style="text-align:right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows}
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div class="footer">
      Tip: Keep file names simple (no weird characters) for easiest testing.
    </div>
  </div>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):

    def redirect_home(self, toast: str = ""):
        # Put toast into query so it survives redirect
        loc = "/"
        if toast:
            loc = "/?toast=" + quote(toast)
        self.send_response(303)
        self.send_header("Location", loc)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # Download endpoint
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
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Download failed: {e}")
            return

        # Main UI
        params = parse_qs(parsed.query)
        toast = params.get("toast", [""])[0]
        toast = unquote(toast) if toast else ""

        try:
            files = list_s3_files()
            page = render_page(files, BUCKET, toast_msg=toast)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))
        except Exception as e:
            # Render page with empty list but show error toast
            page = render_page([], BUCKET, toast_msg=f"Error: {e}")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)

        # Upload
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
                self.redirect_home(toast=f"Uploaded: {filename}")
            except Exception as e:
                self.redirect_home(toast=f"Upload failed: {e}")
            return

        # Delete
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
                self.redirect_home(toast=f"Deleted: {filename}")
            except Exception as e:
                self.redirect_home(toast=f"Delete failed: {e}")
            return

        self.send_error(404, "Not found")


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()
