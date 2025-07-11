import os
import sys
import importlib

# .env 파일이 있으면 로드합니다.
if os.path.exists(".env"):
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("[INFO] .env 파일 로드 완료.")
    except ImportError:
        print("[INFO] python-dotenv가 없어 .env 파일을 로드하지 못했습니다.")

# --- 체크할 항목 정의 ---
REQUIRED_FILES = [
    "app/main.py",
    "app/config.py",
]
REQUIRED_MODULES = [
    "app.config",
    "app.services.dynamic_ai_service",
]
REQUIRED_SETTINGS = [
    "PROJECT_NAME",
    "PROJECT_VERSION",
]

# --- 1. 필수 파일 체크 ---
print("--- 1. 필수 파일 체크 시작 ---")
has_error = False
for f in REQUIRED_FILES:
    if not os.path.exists(f):
        print(f"[ERROR] 필수 파일이 없습니다: {f}")
        has_error = True
if not has_error:
    print("[OK] 모든 필수 파일이 존재합니다.")
else:
    sys.exit(1)

# --- 2. 필수 모듈 임포트 체크 ---
print("\n--- 2. 필수 모듈 임포트 체크 시작 ---")
has_error = False
for m in REQUIRED_MODULES:
    try:
        importlib.import_module(m)
        print(f"[OK] 모듈 임포트 성공: {m}")
    except ImportError as e:
        print(f"[ERROR] 모듈을 임포트할 수 없습니다: {m} ({e})")
        has_error = True
if has_error:
    sys.exit(1)

# --- 3. 필수 설정값 체크 ---
print("\n--- 3. 필수 설정값 체크 시작 ---")
try:
    from app.config import settings
    
    required_settings = [
        "PROJECT_NAME",
        "PROJECT_VERSION",
        "BACKEND_CORS_ORIGINS",
        "SUPABASE_URL",
        "SUPABASE_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "MAPS_PLATFORM_API_KEY"
    ]
    
    missing_settings = []
    for setting_name in required_settings:
        # 'API_KEY'가 포함된 설정은 실제 값이 없어도 통과 (Railway에서 주입)
        if "API_KEY" in setting_name.upper() or "URL" in setting_name.upper():
             if not hasattr(settings, setting_name):
                missing_settings.append(setting_name)
        # 그 외 설정은 값이 비어있는지 확인
        else:
            value = getattr(settings, setting_name, None)
            if value is None or value == "":
                missing_settings.append(setting_name)

    if not missing_settings:
        print("[OK] 모든 필수 설정값이 존재합니다.")
    else:
        for setting in missing_settings:
            print(f"[ERROR] 필수 설정값이 누락되었습니다: {setting}")
        sys.exit(1)

except ImportError as e:
    print(f"[ERROR] 설정 파일(app.config)을 임포트할 수 없습니다: {e}")
    sys.exit(1)
except AttributeError as e:
    print(f"[ERROR] 설정 파일에 필요한 속성이 없습니다: {e}")
    sys.exit(1)

print("\n[SUCCESS] 모든 배포 전 점검을 통과했습니다.")