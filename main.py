import cv2 as cv
import numpy as np
import win32gui
from PIL import ImageGrab
from win32api import GetSystemMetrics
from windowcapture import WindowCapture
from pynput.keyboard import Key, Controller

wincap = WindowCapture('Super Hexagon')

block = 1000000

show_pre_process = False
show_crop = False
show_binary = True
show_info = True

# nav_r = 48
# nav_d = 20
nav_r = 26
nav_d = 20

jump_score = [1, 3, 9, 27, 81]

def process_image(scene):  # image must be square
    if show_pre_process:
        cv.imshow("Pre processed", scene)

    c = int(scene.shape[1] / 2)
    scene_out = scene[0:480, c - 240:c + 240]
    if show_crop:
        cv.imshow("Cropped", scene_out)

    center_color = scene_out[240][240]
    block_color = scene_out[240][240]
    i = 1
    while (center_color == block_color).all() and i < 100:
        block_color = scene_out[240][240 + i]
        i += 1

    t = 70
    block_color_up = block_color + [t, t, t]
    block_color_down = block_color + [-t, -t, -t]

    scene_out = cv.inRange(scene_out, block_color_down, block_color_up)

    if show_binary:
        cv.imshow("Binary", scene_out)

    # edged = cv.Canny(scene_out, 1, 5)
    # contours, _ = cv.findContours(edged, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # for cnt in contours:
    #     #rect = cv.minAreaRect(cnt)
    #     # box = cv.boxPoints(rect)
    #     # box = np.int0(box)
    #     scene_test = cv.drawContours(scene, cnt, 0, (0, 255, 0), 0)
    # cv.imshow("Test", edged)

    return scene_out


def find_player(scene):
    contours, _ = cv.findContours(scene, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv.contourArea(cnt)
        if area < 100:
            rect = cv.minAreaRect(cnt)
            # box = cv.boxPoints(rect)
            # box = np.int0(box)
            # scene = cv.drawContours(scene, [box], 0, (0, 255, 0), 0)
            if 10 < rect[0][0] < 170 and 10 < rect[0][1] < 170:
                return rect[0]

    return 0, 0


def generate_nav_mesh(scene, player_x, player_y):
    base_dis = np.sqrt((player_x - screen.shape[1] / 2) ** 2 + (player_y - 240) ** 2) + 10
    nav_mesh = [[block for x in range(nav_d)] for y in range(nav_r)]

    for r in range(nav_r):
        dis = base_dis + (240 - base_dis)
        nav_x = int(dis * np.cos(360 * r / nav_r * np.pi / 180)) + 240
        nav_y = int(dis * np.sin(360 * r / nav_r * np.pi / 180)) + 240
        if scene[nav_y - 1][nav_x - 1] == 0:
            nav_mesh[r][nav_d - 1] = 0

    for d in range(nav_d - 2, -1, -1):
        for r in range(nav_r - 1, -1, -1):
            dis = base_dis + d / nav_d * (240 - base_dis)
            nav_x = int(dis * np.cos(360 * r / nav_r * np.pi / 180)) + 240
            nav_y = int(dis * np.sin(360 * r / nav_r * np.pi / 180)) + 240
            nav_x_p = int(dis * np.cos(360 * (r + 1) / nav_r * np.pi / 180)) + 240
            nav_y_p = int(dis * np.sin(360 * (r + 1) / nav_r * np.pi / 180)) + 240
            nav_x_m = int(dis * np.cos(360 * (r - 1) / nav_r * np.pi / 180)) + 240
            nav_y_m = int(dis * np.sin(360 * (r - 1) / nav_r * np.pi / 180)) + 240

            if scene[nav_y][nav_x] == 0 and scene[nav_y_p][nav_x_p] == 0 and scene[nav_y_m][nav_x_m] == 0:
                if nav_mesh[r][d + 1] != block:
                    nav_mesh[r][d] = nav_mesh[r][d + 1] + jump_score[0]

                for x in range(len(jump_score)):
                    if nav_mesh[(r + x) % nav_r][d + 1] + jump_score[x] < nav_mesh[r][d]:
                        nav_mesh[r][d] = nav_mesh[(r + x) % nav_r][d + 1] + jump_score[x]
                    if nav_mesh[(r - x) % nav_r][d + 1] + jump_score[x] < nav_mesh[r][d]:
                        nav_mesh[r][d] = nav_mesh[(r - x) % nav_r][d + 1] + jump_score[x]
            else:
                nav_mesh[r][d + 1] = block
    return nav_mesh


def get_nav_path(nav_mesh, player_x, player_y):
    player_dis = np.sqrt((player_x - screen.shape[1] / 2) ** 2 + (player_y - 240) ** 2)
    player_x = (player_x - int(screen.shape[1] / 2)) / player_dis
    player_y = (player_y - 240) / player_dis
    player_angle = np.arccos(player_x) * 180 / np.pi
    if player_y < 0:
        player_angle *= -1
        player_angle += 360

    on_r = int(player_angle / 360 * nav_r + 0.5) % nav_r

    for d in range(0, nav_d):
        current = nav_mesh[on_r][d]
        left = nav_mesh[(on_r + 1) % nav_r][d]
        right = nav_mesh[(on_r - 1) % nav_r][d]

        if current > left or current > right:
            if left < right:
                on_r = (on_r + 1) % nav_r
            else:
                on_r = (on_r - 1) % nav_r

        nav_mesh[on_r][d] = 1000

    on_r = int(player_angle / 360 * nav_r + 0.5) % nav_r
    on = nav_mesh[on_r][0]
    left = nav_mesh[(on_r + 1) % nav_r][0]
    right = nav_mesh[(on_r - 1) % nav_r][0]
    dir = 0
    if left == 1000:
        dir = 1
    elif right == 1000:
        dir = -1

    return dir, nav_mesh



if __name__ == '__main__':
    player_x = 0
    player_y = 0
    left_down = False
    right_down = False
    keyboard = Controller()
    while True:
        in_focus = "super hexagon" in win32gui.GetWindowText(win32gui.GetForegroundWindow()).lower()
        screen = wincap.get_screenshot()
        scene = np.array(screen)
        # scene = cv.imread("img/screenshot02.png")
        # scene = cv.cvtColor(scene, cv.COLOR_RGB2BGR)
        scene = process_image(scene)

        new_player_x, new_player_y = find_player(scene[150:330, 150:330])

        if new_player_x != 0:
            player_x = int(new_player_x) + int(screen.shape[1] / 2) - 90
        if new_player_y != 0:
            player_y = int(new_player_y) + 150

        screen = cv.circle(screen, [player_x, player_y], 10, (0, 255, 0), thickness=2, lineType=8, shift=0)

        nav_mesh = generate_nav_mesh(scene, player_x, player_y)
        move_dir, nav_mesh = get_nav_path(nav_mesh, player_x, player_y)
        base_dis = np.sqrt((player_x - screen.shape[1] / 2) ** 2 + (player_y - 240) ** 2) + 11
        for d in range(nav_d):
            for r in range(nav_r):
                dis = base_dis + d / nav_d * (240 - base_dis)
                nav_x = int(dis * np.cos(360 * r / nav_r * np.pi / 180)) + int(screen.shape[1] / 2)
                nav_y = int(dis * np.sin(360 * r / nav_r * np.pi / 180)) + 240
                if nav_mesh[r][d] == 1000: #Nav
                    screen = cv.circle(screen, [nav_x, nav_y], 5, (255, 255, 255), thickness=2, lineType=8, shift=0)
                if nav_mesh[r][d] == block: #Red
                    screen = cv.circle(screen, [nav_x, nav_y], 1, (0, 0, 255), thickness=2, lineType=8, shift=0)
                else:
                    screen = cv.circle(screen, [nav_x, nav_y], 1, (0, 255, 0), thickness=1, lineType=8, shift=0)

        if in_focus:
            print(move_dir)
            if move_dir == -1:
                keyboard.press('a')
                keyboard.release('d')
            elif move_dir == 1:
                keyboard.press('d')
                keyboard.release('a')
            else:
                keyboard.release('a')
                keyboard.release('d')

        if show_info:
            cv.imshow("Info", screen)

        if cv.waitKey(1) == ord("q"):
            cv.destroyAllWindows()
            break
