# Tesseract OCR 설치 가이드 (OS별 가이드)

본 프로젝트의 **예치금 자동 간편충전(`charge`) 모듈**은 모바일 웹페이지 환경의 가상 보안 키패드를 해독하기 위해 머신러닝 기반 OCR(광학 문자 인식) 엔진인 [Tesseract](https://github.com/tesseract-ocr/tesseract)를 필수로 요구합니다.

아래 가이드에 따라 사용 중인 운영체제(OS)에 맞춰 Tesseract를 설치해 주세요.

---

## 🍎 macOS (추천/가장 쉬움)

macOS에서는 패키지 관리자인 `Homebrew`를 사용하여 단 한 줄로 설치할 수 있습니다.

1. 터미널(Terminal) 앱을 엽니다.
2. 아래 명령어를 실행하여 Tesseract 빈(bin) 파일을 설치합니다.
   ```bash
   brew install tesseract
   ```
3. 설치가 완료되면, 터미널에 `tesseract --version`을 입력하여 정상적으로 버전 정보가 출력되는지 확인합니다.

> **참고**: `charge.py` 내부에서 `/opt/homebrew/bin/tesseract` 또는 `/usr/local/bin/tesseract` 경로를 자동으로 탐색하므로 별도의 환경변수 설정이 필요 없습니다.

---

## 🪟 Windows

Windows 시스템에서는 비공식 프리컴파일 인스톨러를 다운로드하여 설치해야 하며, **환경변수 스크립트 등록** 과정이 필요할 수 있습니다.

1. **다운로드**:
   - [UB-Mannheim Tesseract 저장소](https://github.com/UB-Mannheim/tesseract/wiki)에 접속합니다.
   - 최신 버전의 인스톨러(예: `tesseract-ocr-w64-setup-5.x.x.exe`)를 클릭하여 다운로드합니다.
   
2. **설치 진행**:
   - 다운로드받은 `.exe` 파일을 실행합니다.
   - 설치 옵션 중 추가 언어 데이터(Additional language data) 설치 여부를 물어보는데, 본 프로젝트는 숫자(`digits`)만을 스캔하므로 기본 설정(영어) 그대로 `Next`를 눌러 설치를 완료합니다.
   - **설치 경로를 기억해 두세요**. (보통 `C:\Program Files\Tesseract-OCR` 또는 `%LOCALAPPDATA%\Tesseract-OCR`)

3. **환경변수 설정 (옵션)**:
   - 본 프로그램의 최신 버전은 `C:\Program Files\Tesseract-OCR\tesseract.exe` 경로를 자동으로 찾습니다.
   - 하지만 명령 프롬프트(CMD)에서 `tesseract` 명령어를 전역으로 사용하려면 환경 변수를 등록해야 합니다.
     1. 키보드의 `Windows` 키를 누르고 **"환경 변수 편집"**을 검색 후 엽니다.
     2. `시스템 속성` 창에서 우측 하단의 **[환경 변수(N)...]** 버튼을 클릭합니다.
     3. 위쪽 **사용자 변수** 또는 아래쪽 **시스템 변수** 목록에서 **`Path`** 변수를 찾아 **[편집(E)...]** 버튼을 누릅니다.
     4. **[새로 만들기(N)]** 버튼을 누르고 Tesseract가 설치된 폴더 경로(예: `C:\Program Files\Tesseract-OCR`)를 입력하고 확인을 누릅니다.
     5. 설정 적용 후, CMD 쉘을 껐다가 다시 켜서 `tesseract --version` 입력 후 작동을 확인합니다.

---

## 🐧 Linux (Ubuntu / Debian 등)

apt를 지원하는 데비안 계열 리눅스에서는 간편하게 설치할 수 있습니다.

1. 터미널을 호출합니다.
2. 패키지 목록을 업데이트하고 tesseract-ocr 본체 팩을 설치합니다.
   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr
   ```
3. 설치 후 버전 확인:
   ```bash
   tesseract --version
   ```
4. 리눅스 환경에서도 스크립트가 `/usr/bin/tesseract` 경로를 기본적으로 체크하여 실행하므로 보통 즉시 사용 가능합니다.

---

### ❓ 자동 감지 경로 외의 폴더에 설치하셨나요?
만약 위의 기본 설치 경로들이 아닌 다른 드라이브나 폴더에 Tesseract를 설치하셨다면 (ex: `D:\Utils\Tesseract`), 아래와 같이 `.env` 파일에 경로를 직접 수동 매핑해 주시면 됩니다.

**`.env` 파일에 추가:**
```env
# 본인 환경의 Tesseract 실행 파일 (.exe 또는 바이너리) 전체 경로 입력
TESSERACT_PATH=D:\Utils\Tesseract\tesseract.exe
```
