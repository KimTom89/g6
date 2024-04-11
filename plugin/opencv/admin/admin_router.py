"""OpenCV Admin Router"""
import cv2
from fastapi import APIRouter
from starlette.requests import Request

from core.template import AdminTemplates
from .. import plugin_config
from ..plugin_config import module_name, admin_router_prefix

templates = AdminTemplates()
admin_router = APIRouter(prefix=admin_router_prefix, tags=['demo_admin'])


@admin_router.get("/chapter/1")
def opencv_chapter1(
    request: Request
):
    """OpenCV Chapter1 Router"""
    request.session["menu_key"] = module_name
    request.session["plugin_submenu_key"] = module_name + "1"

    image = cv2.imread('data/00_raiser.jpg', cv2.IMREAD_COLOR)
    image_view = cv2.imshow("00_raiser", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    context = {
        "request": request,
        "image_view": image_view
    }
    return templates.TemplateResponse(
        f"{plugin_config.TEMPLATE_PATH}/admin/chapter1.html", context)


@admin_router.get("/webcam/test")
def opencv_chapter1(
    request: Request
):
    """OpenCV Chapter1 Router"""
    request.session["menu_key"] = module_name
    request.session["plugin_submenu_key"] = module_name + "_webcam_test"

    cap = cv2.VideoCapture(0)               # 웹캠 객체 생성
    if cap.isOpened():                      # 캡처 객체 초기화 확인
        while True: 
            ret, img = cap.read()           # 다음 프레임 읽기
            if ret:                         # 프레임 읽기 정상
                cv2.imshow('camera', img)
                if cv2.waitKey(1) != -1:    # 화면에 표시
                    break
            else: 
                print('no frame')           # 다음 프레임을 읽을 수 없음.
                break

    else:
        print("Can't open video.")          # 캡처 객체 초기화 실패
    cap.release()                           # 캡쳐 자원 반납
    cv2.destroyAllWindows()

    context = {
        "request": request,
    }
    return templates.TemplateResponse(
        f"{plugin_config.TEMPLATE_PATH}/admin/chapter1.html", context)
