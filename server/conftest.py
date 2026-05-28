# 파일 목적: pytest 가 server/ 를 import 경로에 넣어 `import blog`/`import main` 이 동작하게 함
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
