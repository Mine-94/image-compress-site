# 이미지압축

Pillow 기반으로 이미지 용량을 줄이고 크기(리사이즈)도 조절해주는 Flask 웹앱입니다. Lichtbringer 브랜드 디자인 시스템을 사용합니다.

## 로컬에서 실행하기

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://localhost:5001` 접속.

## Docker로 실행하기

```bash
docker build -t image-compress .
docker run -p 8080:8080 image-compress
```

## 배포 (Render 예시)

1. 이 폴더를 GitHub 저장소로 올립니다.
2. [render.com](https://render.com) → **New > Web Service** → 저장소 연결.
3. Environment는 **Docker** 선택.
4. Free/Starter 플랜 선택 후 배포.

## 기능

- JPG, PNG, WEBP 지원
- 크기 조절: 원본 / 75% / 50% / 25%
- 압축 품질: 고화질 / 권장 / 최대 압축
- 업로드 최대 용량: 30MB
- 처리 완료 후 서버에서 파일 자동 삭제

## 애드센스

`templates/base.html`에 이미 애드센스 스크립트 태그(client=ca-pub-8602848692420724)와 `static/ads.txt`가 포함되어 있습니다. Google AdSense 대시보드에서 이 도메인을 새 사이트로 추가하고 소유권 확인 절차를 진행하세요.
