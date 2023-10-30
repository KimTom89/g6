import datetime
from datetime import timedelta
import re
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from database import get_db

from jinja2 import Environment, FileSystemLoader
from database import engine, get_db, SessionLocal
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from common import *
from typing import Optional

from settings import APP_IS_DEBUG
from user_agents import parse
import os
import models
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(debug=APP_IS_DEBUG)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = Jinja2Templates(directory=TEMPLATES_DIR, extensions=["jinja2.ext.i18n"])
templates.env.globals["is_admin"] = is_admin
templates.env.globals["generate_one_time_token"] = generate_one_time_token
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals['getattr'] = getattr
templates.env.globals["generate_token"] = generate_token

from _admin.admin import router as admin_router
from _bbs.board import router as board_router
from _bbs.login import router as login_router
from _bbs.register import router as register_router
from _bbs.content import router as content_router
from _bbs.faq import router as faq_router
from _bbs.qa import router as qa_router
from _bbs.member_profile import router as user_profile_router
from _bbs.memo import router as memo_router
from _bbs.poll import router as poll_router
from _bbs.ajax_autosave import router as autosave_router
from _bbs.formmail import router as formmail_router

app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(board_router, prefix="/board", tags=["board"])
app.include_router(login_router, prefix="/bbs", tags=["login"])
app.include_router(register_router, prefix="/bbs", tags=["register"])
app.include_router(user_profile_router, prefix="/bbs", tags=["profile"])
app.include_router(content_router, prefix="/bbs", tags=["content"])
app.include_router(faq_router, prefix="/bbs", tags=["faq"])
app.include_router(qa_router, prefix="/bbs", tags=["qa"])
app.include_router(memo_router, prefix="/bbs", tags=["memo"])
app.include_router(poll_router, prefix="/bbs", tags=["poll"])
app.include_router(autosave_router, prefix="/bbs/ajax", tags=["autosave"])
app.include_router(formmail_router, prefix="/bbs", tags=["formmail"])

# is_mobile = False
# user_device = 'pc'

# 항상 실행해야 하는 미들웨어
@app.middleware("http")
async def main_middleware(request: Request, call_next):

    ### 미들웨어가 여러번 실행되는 것을 막는 코드 시작    
    # 요청의 경로를 얻습니다.
    path = request.url.path
    # 경로가 정적 파일에 대한 것이 아닌지 확인합니다 (css, js, 이미지 등).
    if (path.startswith('/static') or path.endswith(('.css', '.js', '.jpg', '.png', '.gif', '.webp'))):
        response = await call_next(request)
        return response
    ### 미들웨어가 여러번 실행되는 것을 막는 코드 끝
    
    member = None

    db: Session = SessionLocal()
    config = db.query(models.Config).first()
    request.state.config = config

    is_super_admin = False
    ss_mb_id = request.session.get("ss_mb_id", "")
    if ss_mb_id:
        member = db.query(models.Member).filter(models.Member.mb_id == ss_mb_id).first()
        if member:
            if member.mb_intercept_date or member.mb_leave_date: # 차단 되었거나, 탈퇴한 회원이면 세션 초기화
                request.session["ss_mb_id"] = ""
                member = None
            elif member.mb_today_login.strftime("%Y-%m-%d") != TIME_YMD:  # 오늘 처음 로그인 이라면
                # if member.mb_today_login[:10] != TIME_YMD: # 오늘 처음 로그인 이라면
                # 첫 로그인 포인트 지급
                insert_point(request, member.mb_id, config.cf_login_point, TIME_YMD + " 첫로그인", "@login", member.mb_id, TIME_YMD)
                # 오늘의 로그인이 될 수도 있으며 마지막 로그인일 수도 있음
                # 해당 회원의 접근일시와 IP 를 저장
                member.mb_today_login = TIME_YMDHIS
                member.mb_login_ip = request.client.host
                db.commit()
            # 최고관리자인지 확인
            if config.cf_admin == member.mb_id:
                is_super_admin = True
            
    else:
        cookie_mb_id = request.cookies.get("ck_mb_id")
        if cookie_mb_id:
            cookie_mb_id = re.sub("[^a-zA-Z0-9_]", "", cookie_mb_id)[:20] # 쿠키에 저장된 아이디에서 영문자,숫자,_ 20글자 얻는다.
        if cookie_mb_id and cookie_mb_id.lower() != config.cf_admin.lower(): # 최고관리자 아이디라면 자동로그인 금지
            member = db.query(models.Member).filter(models.Member.mb_id == cookie_mb_id).first()
            if member and not (member.mb_intercept_date or member.mb_leave_date): # 차단 했거나 탈퇴한 회원이 아니면
                # 메일인증을 사용하고 메일인증한 시간이 있다면, 년도만 체크하여 시간이 있음을 확인
                if config.cf_use_email_certify and member.mb_email_certify[:2] != "00":
                    ss_mb_key  = session_member_key(request, member)
                    # 쿠키에 저장된 키와 여러가지 정보를 조합하여 만든 키가 일치한다면 로그인으로 간주
                    if request.cookies.get("ck_auto") == ss_mb_key:
                        request.session["ss_mb_id"] = cookie_mb_id
                        return RedirectResponse(url="/", status_code=302).set_cookie(key="ss_mb_id", value=cookie_mb_id, max_age=3600)
    
    request.state.is_super_admin = is_super_admin

    if request.method == "GET":
        request.state.sst = request.query_params.get("sst") if request.query_params.get("sst") else ""
        request.state.sod = request.query_params.get("sod") if request.query_params.get("sod") else ""
        request.state.sfl = request.query_params.get("sfl") if request.query_params.get("sfl") else ""
        request.state.stx = request.query_params.get("stx") if request.query_params.get("stx") else ""
        request.state.sca = request.query_params.get("sca") if request.query_params.get("sca") else ""
        request.state.page = request.query_params.get("page") if request.query_params.get("page") else ""
    else:
        request.state.sst = request._form.get("sst") if request._form and request._form.get("sst") else ""
        request.state.sod = request._form.get("sod") if request._form and request._form.get("sod") else ""
        request.state.sfl = request._form.get("sfl") if request._form and request._form.get("sfl") else ""
        request.state.stx = request._form.get("stx") if request._form and request._form.get("stx") else ""
        request.state.sca = request._form.get("sca") if request._form and request._form.get("sca") else ""
        request.state.page = request._form.get("page") if request._form and request._form.get("page") else ""
        
    # pc, mobile 구분
    request.state.is_mobile = False
    request.state.device = 'pc'
    
    if 'SET_DEVICE' in globals():
        if SET_DEVICE == 'mobile':
            request.state.is_mobile = True
            request.state.device = 'mobile'
    else:
        user_agent = request.headers.get("User-Agent", "")
        ua = parse(user_agent)
        if 'USE_MOBILE' in globals() and USE_MOBILE:
            if ua.is_mobile or ua.is_tablet: # 모바일과 태블릿에서 접속하면 모바일로 간주
                request.state.is_mobile = True
                request.state.device = 'mobile'
                
    # 로그인한 회원 정보
    request.state.login_member = member

    # 에디터 전역변수
    request.state.editor = config.cf_editor
    request.state.use_editor = True if config.cf_editor else False
                
    # request.state.context = {
    #     # "request": request,
    #     # "config": config,
    #     # "member": member,
    #     # "outlogin": outlogin.body.decode("utf-8"),
    # }      
    db.close()
    response = await call_next(request)

    # 접속자 기록
    vi_ip = request.client.host
    ck_visit_ip = request.cookies.get('ck_visit_ip', None)
    if ck_visit_ip != vi_ip:
        # 접속을 추적하는 쿠키 설정 및 접속 레코드 기록
        response.set_cookie('ck_visit_ip', vi_ip, max_age=86400)  # 쿠키를 하루 동안 유지
        # 접속 레코드 기록
        record_visit(request)
        
    # print("After request")

    return response

# 아래 app.add_middleware(...) 코드는 반드시 common 함수의 아래에 위치해야 함. 
# 안 그러면 아래와 같은 오류를 맛볼수 있음 ㅠㅠ
# AssertionError: SessionMiddleware must be installed to access request.session
app.add_middleware(SessionMiddleware, secret_key="secret", session_cookie="session", max_age=3600 * 3)


@app.exception_handler(AlertException)
async def alert_exception_handler(request: Request, exc: AlertException):
    """AlertException 예외처리 등록

    Args:
        request (Request): request 객체
        exc (AlertException): 예외 객체

    Returns:
        _TemplateResponse: 경고창 템플릿
    """
    return templates.TemplateResponse(
        "alert.html", {"request": request, "errors": exc.detail, "url": exc.url}, status_code=exc.status_code
    )

@app.exception_handler(AlertCloseException)
async def alert_close_exception_handler(request: Request, exc: AlertCloseException):
    """AlertCloseException 예외처리 등록

    Args:
        request (Request): request 객체
        exc (AlertCloseException): 예외 객체

    Returns:
        _TemplateResponse: 경고창 & 윈도우창 닫기 템플릿
    """
    return templates.TemplateResponse(
        "alert_close.html", {"request": request, "errors": exc.detail}, status_code=exc.status_code
    )


def get_member(mb_id, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    return member

@app.get("/root")
def read_root():
    return {"Hello": "World"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, response: Response, db: Session = Depends(get_db)):
    
    context = {
        "request": request,
        "latest": latest,
        "newwins": get_newwins(request)
    }
    return templates.TemplateResponse(f"index.{request.state.device}.html", context)


# 최신글
def latest(request: Request, skin_dir='', bo_table='', rows=10, subject_len=40):

    if not skin_dir:
        skin_dir = 'basic'

    g6_file_cache = G6FileCache()
    cache_filename = f"latest-{bo_table}-{skin_dir}-{rows}-{subject_len}-{g6_file_cache.get_cache_secret_key()}.html"
    cache_file = os.path.join(g6_file_cache.cache_dir, cache_filename)

    # 캐시된 파일이 있으면 파일을 읽어서 반환
    if os.path.exists(cache_file):
        return g6_file_cache.get(cache_file)
    
    db = SessionLocal()
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    
    models.Write = dynamic_create_write_table(bo_table)
    writes = db.query(models.Write).filter(models.Write.wr_is_comment == False).order_by(models.Write.wr_num).limit(rows).all()
    for write in writes:
        write.is_notice = write.wr_id in board.bo_notice.split(",")
        write.subject = write.wr_subject[:subject_len]
        write.icon_hot = write.wr_hit >= 100
        write.icon_new = write.wr_datetime > (datetime.now() - timedelta(days=1))
        write.icon_file = write.wr_file
        write.icon_link = write.wr_link1 or write.wr_link2
        write.icon_reply = write.wr_reply
    
    context = {
        "request": request,
        "writes": writes,
        "bo_table": bo_table,
        "bo_subject": board.bo_subject,
    }
    temp = templates.TemplateResponse(f"latest/{skin_dir}.html", context)
    return temp.body.decode("utf-8")

def get_newwins(request: Request):
    """
    레이어 팝업 목록을 반환하는 함수
    """
    db = SessionLocal()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_division = "comm" # comm, both, shop
    newwins = db.query(models.NewWin).filter(
        models.NewWin.nw_begin_time <= now,
        models.NewWin.nw_end_time >= now,
        models.NewWin.nw_device.in_(["both", request.state.device]),
        models.NewWin.nw_division.in_(["both", current_division]),
    ).order_by(models.NewWin.nw_id.asc()).all()

    # "hd_pops_" + nw_id 이름으로 선언된 쿠키가 있는지 확인하고 있다면 팝업을 제거
    newwins = [newwin for newwin in newwins if not request.cookies.get("hd_pops_" + str(newwin.nw_id))]

    return newwins