from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import tempfile
import subprocess
import os
import zipfile
from typing import List
from io import BytesIO

app = FastAPI()

app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/")
async def root():
    return FileResponse("public/index.html")


class DownloadRequest(BaseModel):
    videoIds: List[str]


@app.post("/download", response_class=StreamingResponse)
async def download(request: DownloadRequest):
    urls = [f"https://www.youtube.com/watch?v={vid}" for vid in request.videoIds]

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_dir = os.path.join(temp_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        command = [
            "yt-dlp",
            "-f", "bestaudio",
            "-o", os.path.join(audio_dir, "%(title)s.%(ext)s"),
            *urls
        ]

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            return JSONResponse(status_code=500, content={"error": f"yt-dlp 실행 실패: {e}"})

        # ✅ 메모리에 zip 파일 생성
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for root_dir, _, files in os.walk(audio_dir):
                for file in files:
                    full_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(full_path, audio_dir)
                    zipf.write(full_path, arcname)
        zip_buffer.seek(0)  # 파일 포인터 맨 앞으로

        # ✅ 파일을 열지 않고 바로 메모리로 StreamingResponse
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=download.zip"
            }
        )
