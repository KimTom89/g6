from core.database import DBConnect
from core.models import Base

# 상단의 (Base) 를 상속받은 모델들을 DB 에 테이블 생성한다. 최하단에 있어야한다.
# Base.metadata.create_all(bind=DBConnect().engine)
