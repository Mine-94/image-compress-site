import os
import tempfile
import uuid
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    send_file,
    jsonify,
    after_this_request,
)
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps

app = Flask(__name__)

MAX_CONTENT_LENGTH = 30 * 1024 * 1024  # 30MB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

UPLOAD_DIR = Path(tempfile.gettempdir()) / "image-compress-uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}

QUALITY_PRESETS = {
    "high": 90,   # 고화질
    "medium": 75,  # 권장
    "low": 50,    # 최대 압축
}

RESIZE_PRESETS = {
    "100": 1.0,
    "75": 0.75,
    "50": 0.5,
    "25": 0.25,
}


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def process_image(input_path: Path, output_path: Path, quality: str, resize: str) -> tuple[int, int, int, int]:
    img = Image.open(input_path)
    img = ImageOps.exif_transpose(img)  # respect camera orientation
    orig_w, orig_h = img.size

    scale = RESIZE_PRESETS.get(resize, 1.0)
    if scale < 1.0:
        new_w = max(1, round(orig_w * scale))
        new_h = max(1, round(orig_h * scale))
        img = img.resize((new_w, new_h), Image.LANCZOS)
    else:
        new_w, new_h = orig_w, orig_h

    q = QUALITY_PRESETS.get(quality, 75)
    fmt = (img.format or "JPEG")
    ext = input_path.suffix.lower()

    if ext in (".jpg", ".jpeg"):
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=q, optimize=True, progressive=True)
    elif ext == ".webp":
        img.save(output_path, "WEBP", quality=q, method=6)
    elif ext == ".png":
        # PNG is lossless; use max compression. "quality" maps to palette
        # reduction aggressiveness for extra savings on the "low" preset.
        if quality == "low" and img.mode in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "P", palette=Image.ADAPTIVE, colors=256)
        img.save(output_path, "PNG", optimize=True, compress_level=9)
    else:
        img.save(output_path)

    return orig_w, orig_h, new_w, new_h


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/robots.txt")
def robots():
    return app.send_static_file("robots.txt")


@app.route("/sitemap.xml")
def sitemap():
    return app.send_static_file("sitemap.xml")


@app.route("/ads.txt")
def ads():
    return app.send_static_file("ads.txt")


@app.route("/api/process", methods=["POST"])
def api_process():
    if "file" not in request.files:
        return jsonify({"error": "파일이 없습니다."}), 400

    file = request.files["file"]
    quality = request.form.get("quality", "medium")
    resize = request.form.get("resize", "100")

    if file.filename == "":
        return jsonify({"error": "파일이 없습니다."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "JPG, PNG, WEBP 파일만 업로드할 수 있습니다."}), 400

    if quality not in QUALITY_PRESETS:
        quality = "medium"
    if resize not in RESIZE_PRESETS:
        resize = "100"

    job_id = uuid.uuid4().hex
    safe_name = secure_filename(file.filename) or "image.jpg"
    ext = Path(safe_name).suffix.lower() or ".jpg"
    input_path = UPLOAD_DIR / f"{job_id}_in{ext}"
    output_path = UPLOAD_DIR / f"{job_id}_out{ext}"

    file.save(input_path)
    original_size = input_path.stat().st_size

    try:
        orig_w, orig_h, new_w, new_h = process_image(input_path, output_path, quality, resize)
    except Exception as exc:  # noqa: BLE001
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        return jsonify({"error": f"이미지 처리 실패: {exc}"}), 500

    compressed_size = output_path.stat().st_size

    used_original = False
    if compressed_size >= original_size and resize == "100":
        output_path.unlink(missing_ok=True)
        output_path = input_path
        compressed_size = original_size
        used_original = True

    stem = safe_name.rsplit(".", 1)[0]
    download_name = f"{stem}_compressed{ext}"

    return jsonify(
        {
            "job_id": job_id,
            "download_url": f"/api/download/{job_id}?name={download_name}&ext={ext}",
            "original_size": original_size,
            "compressed_size": compressed_size,
            "original_size_human": human_size(original_size),
            "compressed_size_human": human_size(compressed_size),
            "ratio": round((1 - compressed_size / original_size) * 100, 1)
            if original_size and not used_original
            else 0,
            "original_dimensions": f"{orig_w}×{orig_h}",
            "new_dimensions": f"{new_w}×{new_h}",
            "used_original": used_original,
        }
    )


@app.route("/api/download/<job_id>")
def api_download(job_id):
    safe_job_id = secure_filename(job_id)
    ext = request.args.get("ext", ".jpg")
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"

    out_path = UPLOAD_DIR / f"{safe_job_id}_out{ext}"
    in_path = UPLOAD_DIR / f"{safe_job_id}_in{ext}"

    target = out_path if out_path.exists() else in_path
    if not target.exists():
        return jsonify({"error": "파일을 찾을 수 없습니다. 다시 시도해주세요."}), 404

    download_name = request.args.get("name", f"compressed{ext}")
    mimetype = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")

    @after_this_request
    def cleanup(response):
        try:
            in_path.unlink(missing_ok=True)
            out_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        return response

    return send_file(
        target,
        as_attachment=True,
        download_name=download_name,
        mimetype=mimetype,
    )


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "파일이 너무 큽니다. 30MB 이하 파일만 지원합니다."}), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
