import serial
import pygame
import time
import json

# ==========================================
# [설정] 포트 번호 확인
ARDUINO_PORT = 'COM3' 
BAUD_RATE = 115200 
# ==========================================

# 1. 아두이노 연결
try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # 아두이노 리부팅 대기
    print("✅ 아두이노 연결됨 (3모터 모드)")
except:
    print("❌ 아두이노 연결 실패! 포트를 확인하세요.")
    ser = None

# 2. Pygame & 패드 설정
pygame.init()
pygame.joystick.init()
screen = pygame.display.set_mode((300, 200))
pygame.display.set_caption("Calibration (Auto-Home)")

if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("🎮 패드 연결됨")
else:
    print("❌ 패드를 찾을 수 없습니다.")

# 변수 초기화
current_angles = [90.0, 90.0, 90.0, 90.0] 
saved_positions = {}
target_list = [1, 2, 3, 4, 5, 6, 7, 8, 9] 
current_idx = 0

# 아두이노 전송 함수
def send_arduino(angles):
    if ser and ser.is_open:
        cmd = f"{int(angles[0])},{int(angles[1])},{int(angles[2])},{int(angles[3])}\n"
        ser.write(cmd.encode())

# [추가됨] 로봇을 홈(90도)으로 부드럽게 복귀시키는 함수
def move_to_home():
    global current_angles
    if ser is None: return

    print("🏠 로봇이 초기 위치(90, 90, 90)로 복귀합니다...")
    
    target_angles = [90.0, 90.0, 90.0, 90.0]
    start_angles = list(current_angles)
    
    # 30단계로 나눠서 부드럽게 이동
    STEPS = 30
    for i in range(1, STEPS + 1):
        t = i / STEPS
        temp_angles = []
        for j in range(4): # 4개 값 모두 계산
            val = start_angles[j] + (target_angles[j] - start_angles[j]) * t
            temp_angles.append(val)
        
        send_arduino(temp_angles)
        time.sleep(0.02) # 짧은 대기 (부드러움)

    # 이동 완료 후 현재 각도 업데이트
    current_angles = list(target_angles)
    time.sleep(0.5)
    print("✅ 복귀 완료!")

# ==========================================
# [1] 프로그램 시작 시 홈으로 이동
# ==========================================
move_to_home() 

running = True
clock = pygame.time.Clock()

print("\n===== [틱택토 좌표 설정 (3모터)] =====")
print(f"👉 로봇팔을 화면 속 [{target_list[current_idx]}번 칸] 공중으로 옮기세요.")
print("🟢 [A 버튼]: 저장 / 🔴 [B 버튼]: 저장 후 종료")
print("🔵 [X 버튼]: 초기 위치(90도)로 복귀")
print("======================================")

try:
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            if event.type == pygame.JOYBUTTONDOWN:
                # A 버튼 (0): 현재 위치 저장
                if event.button == 0: 
                    target = target_list[current_idx]
                    saved_positions[str(target)] = list(current_angles)
                    print(f"✅ {target}번 칸 저장 완료! {list(map(int, current_angles))}")
                    
                    current_idx += 1
                    if current_idx >= 9:
                        print("\n🎉 9개 좌표 설정 완료!")
                        with open('config.json', 'w') as f:
                            json.dump(saved_positions, f, indent=4)
                        print("💾 'config.json' 저장됨. 종료합니다.")
                        running = False
                    else:
                        print(f"👉 다음: [{target_list[current_idx]}번 칸]으로 이동하세요.")
                
                # B 버튼 (1): 종료 (나가기)
                if event.button == 1:
                    print("🔴 종료 버튼 눌림.")
                    running = False

                # [2] X 버튼 (2): 홈으로 복귀 (추가됨!)
                if event.button == 2: 
                    move_to_home()

        if pygame.joystick.get_count() > 0:
            # === 3개 모터 조작 ===
            lx = joystick.get_axis(0) 
            ly = joystick.get_axis(1) 
            ry = joystick.get_axis(3) 
            
            if abs(lx) < 0.1: lx = 0
            if abs(ly) < 0.1: ly = 0
            if abs(ry) < 0.1: ry = 0

            # 속도
            current_angles[0] -= lx * 2.0 
            current_angles[1] += ly * 2.0 
            current_angles[2] += ry * 2.0 

            for i in range(3):
                if current_angles[i] < 0: current_angles[i] = 0
                if current_angles[i] > 180: current_angles[i] = 180

            send_arduino(current_angles)

        clock.tick(30)

except KeyboardInterrupt:
    pass
finally:
    # [3] 프로그램 종료 시 홈으로 이동
    print("\n👋 프로그램을 종료합니다. 로봇을 원위치시킵니다.")
    move_to_home()
    
    if ser and ser.is_open: ser.close()
    pygame.quit()