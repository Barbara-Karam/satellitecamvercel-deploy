from flask import Flask, request, jsonify, Response
import requests as http_requests
import os
from datetime import datetime

app = Flask(__name__)

BLOB_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
BLOB_API_URL = "https://blob.vercel-storage.com"


# --- Upload route ---
@app.route("/upload", methods=["POST"])
def upload():
    if "imageFile" not in request.files:
        return "No file", 400

    file = request.files["imageFile"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
    filename = f"{timestamp}_{file.filename}"

    file_data = file.read()
    content_type = file.content_type or "application/octet-stream"

    # Upload to Vercel Blob
    resp = http_requests.put(
        f"{BLOB_API_URL}/{filename}",
        headers={
            "authorization": f"Bearer {BLOB_TOKEN}",
            "content-type": content_type,
            "x-content-type": content_type,
            "x-api-version": "7",
        },
        data=file_data,
    )

    if resp.status_code in (200, 201):
        print("Saved to Vercel Blob:", filename)
        return "OK", 200

    print("Blob upload failed:", resp.status_code, resp.text)
    return "Upload failed", 500


# --- API endpoint returning all image data ---
@app.route("/api/images")
def api_images():
    resp = http_requests.get(
        BLOB_API_URL,
        headers={
            "authorization": f"Bearer {BLOB_TOKEN}",
            "x-api-version": "7",
        },
    )

    if resp.status_code != 200:
        return jsonify([])

    data = resp.json()
    blobs = data.get("blobs", [])

    images = []
    for blob in blobs:
        pathname = blob.get("pathname", "")
        if pathname.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            images.append(
                {
                    "name": pathname,
                    "url": blob.get("url", ""),
                    "uploadedAt": blob.get("uploadedAt", ""),
                }
            )

    images.sort(key=lambda x: x.get("uploadedAt", ""), reverse=True)
    return jsonify(images)


# --- Gallery page with live updates ---
@app.route("/")
def gallery():
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Live Image Gallery</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .gallery { display: flex; flex-wrap: wrap; }
        .gallery img {
            margin: 5px;
            height: 150px;
            object-fit: cover;
            border-radius: 4px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }
    </style>
</head>
<body>
    <h1>Live Uploaded Images</h1>
    <div class="gallery" id="gallery"></div>

    <script>
        const gallery = document.getElementById("gallery");
        let loadedImages = new Set();

        async function loadImages() {
            try {
                const response = await fetch("/api/images");
                const images = await response.json();

                images.forEach(img => {
                    if (!loadedImages.has(img.url)) {
                        const a = document.createElement("a");
                        a.href = img.url;
                        a.target = "_blank";

                        const imageElem = document.createElement("img");
                        imageElem.src = img.url;
                        imageElem.alt = img.name;

                        a.appendChild(imageElem);
                        gallery.appendChild(a);

                        loadedImages.add(img.url);
                    }
                });
            } catch (err) {
                console.error("Failed to load images:", err);
            }
        }

        loadImages();
        setInterval(loadImages, 5000);
    </script>
</body>
</html>"""
    return Response(html, content_type="text/html")
