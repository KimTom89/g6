import os

# module_name 는 플러그인의 폴더 이름입니다.
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
# 라우터 접두사는 /로 시작합니다. 붙이지 않을 때는 "" 빈문자열로 지정해야합니다.
router_prefix = "/opencv"
admin_router_prefix = router_prefix

TEMPLATE_PATH = f"{module_name}/templates"

# 관리자 메뉴를 설정합니다.
admin_menu = {
    f"{module_name}": [
        {
            "name": "OpenCV",
            "url": "",
        },
        {
            "id": module_name + "1",
            "name": "Chapter 1",
            "url": f"{admin_router_prefix}/chapter/1",
            "tag": "opencv_chapter1"
        },
        {
            "id": module_name + "_webcam_test",
            "name": "WebCam Test 1",
            "url": f"{admin_router_prefix}/webcam/test",
            "tag": "opencv_webcam_test"
        },
    ]
}
