import importlib
import logging
import pkgutil
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from sqlalchemy.inspection import inspect

from core.database import DBConnect
from core.models import Config
from lib.social.social import register_social_provider

# Package.
package_name = 'lib.social.providers'

# pkgutil 로 서브디렉토리의 모듈을 가져온다.
package = importlib.import_module(package_name)
for _, module_name, _ in pkgutil.walk_packages(package.__path__):
    full_module_name = f"{package_name}.{module_name}"
    imported_module = importlib.import_module(full_module_name)

__all__ = [
    "google",
    "facebook",
    "naver",
    "kakao",
    "twitter",
]

# 비동기 함수로 변경
async def load_social_config():
    async_session = DBConnect()._sessionLocal()
    try:
        # 테이블 존재 여부 확인 (비동기 방식)
        # SQLAlchemy 비동기 inspect 방식 사용
        async with DBConnect().engine.connect() as conn:
            insp = await conn.run_sync(lambda sync_conn: inspect(sync_conn))
            has_table = await conn.run_sync(
                lambda sync_conn: insp.has_table(DBConnect().table_prefix + "config")
            )
            
            if has_table:
                # 설정 데이터 가져오기
                result = await async_session.execute(select(Config))
                config = result.scalar_one_or_none()
                
                if config:
                    # 서버시작시 소셜로그인 설정을 불러온다
                    register_social_provider(config)
    except Exception as e:
        logging.warning("소셜로그인 설정을 불러올 수 없습니다. " + str(e.args[0]))
    finally:
        await async_session.close()