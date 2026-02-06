import serial
import time
import json
import socket
import qrcode
import io
import random
import os
from flask import Flask, render_template_string, request, jsonify, send_file

app = Flask(__name__)

# ==========================================
# 1. 설정 및 아두이노 연결
# ==========================================
ARDUINO_PORT = 'COM3'  # 포트 번호 꼭 확인하세요!
BAUD_RATE = 115200

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

robot_positions = {}
try:
    with open(CONFIG_PATH, 'r') as f:
        robot_positions = json.load(f)
    print(f"✅ 좌표 파일 로딩 완료!")
except Exception as e:
    print(f"❌ 좌표 파일 로딩 실패: {e}")

ser = None
try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("✅ 아두이노 연결 성공")
except:
    print("⚠️ 아두이노 연결 실패")

current_angles = [90, 90, 90, 90]

# [업그레이드] 부드러운 움직임 공식 (Ease-In-Out)
def ease_in_out(t):
    # 0~1 사이의 시간을 넣으면, 부드러운 곡선 값을 반환
    return t * t * (3 - 2 * t)

def move_robot_smoothly(target_pos_num):
    global current_angles
    if ser is None or str(target_pos_num) not in robot_positions: return
    
    target_angles = robot_positions[str(target_pos_num)]
    
    # [속도 조절]
    # STEPS: 40 -> 25 (단계 줄여서 더 빠르게)
    # DELAY: 0.04 -> 0.02 (대기 줄여서 더 빠르게)
    STEPS = 25       
    DELAY = 0.02     
    
    start_angles = list(current_angles)

    for i in range(1, STEPS + 1):
        # 선형 비율 (0.0 ~ 1.0)
        linear_t = i / STEPS
        # 곡선 비율 (부드러운 가감속 적용)
        smooth_t = ease_in_out(linear_t)

        temp_angles = []
        for j in range(3):
            # 부드러운 비율(smooth_t)을 적용해 각도 계산
            angle = start_angles[j] + (target_angles[j] - start_angles[j]) * smooth_t
            temp_angles.append(int(angle))
        
        cmd = f"{temp_angles[0]},{temp_angles[1]},{temp_angles[2]},90\n"
        ser.write(cmd.encode())
        time.sleep(DELAY)

    current_angles = list(target_angles)
    time.sleep(0.3) # 도착 후 대기 시간도 단축

def move_to_home():
    global current_angles
    if ser is None: return
    print("🏠 로봇 홈 복귀")
    target = [90, 90, 90, 90]
    start = list(current_angles)
    STEPS = 20 # 복귀는 빠르게
    for i in range(1, STEPS + 1):
        t = i / STEPS
        smooth_t = ease_in_out(t)
        temp = []
        for j in range(3):
            val = start[j] + (target[j] - start[j]) * smooth_t
            temp.append(int(val))
        cmd = f"{temp[0]},{temp[1]},{temp[2]},90\n"
        ser.write(cmd.encode())
        time.sleep(0.02)
    current_angles = list(target)
    time.sleep(0.2)

# ==========================================
# 2. 게임 로직
# ==========================================
board = [''] * 9
game_winner = None
turn = 'X'
difficulty = None # 초기엔 선택 안 된 상태

def check_winner(b):
    wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for x, y, z in wins:
        if b[x] == b[y] == b[z] and b[x] != '': return b[x]
    if '' not in b: return 'Draw'
    return None

def get_ai_move(b):
    empty = [i for i, x in enumerate(b) if x == '']
    if not empty: return None

    # EASY: 70% 확률로 랜덤
    if difficulty == 'EASY':
        if random.random() < 0.7: return random.choice(empty)

    # HARD: 최적수
    for i in range(9): # 이기는 수
        if b[i] == '':
            b[i] = 'O'; 
            if check_winner(b) == 'O': b[i] = ''; return i
            b[i] = ''
    for i in range(9): # 막는 수
        if b[i] == '':
            b[i] = 'X'; 
            if check_winner(b) == 'X': b[i] = ''; return i
            b[i] = ''
    if b[4] == '': return 4
    return random.choice(empty)

# ==========================================
# 3. 웹사이트 (모바일 새로고침 제거 버전)
# ==========================================
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]
    except: ip = '127.0.0.1'
    finally: s.close()
    return ip

SERVER_IP = get_ip()
SERVER_PORT = 5000
CONTROLLER_URL = f"http://{SERVER_IP}:{SERVER_PORT}/controller"

# [모니터 화면]
DISPLAY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Display</title>
    <style>
        body { background-color: #D5CABD; color: #333; display: flex; height: 100vh; margin: 0; overflow: hidden; font-family: 'Arial', sans-serif;}
        .left-panel { flex: 2; display: flex; justify-content: center; align-items: center; }
        .right-panel { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #FDFBF7; margin: 20px; border-radius: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); text-align: center;}
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; width: 80vh; height: 80vh; }
        .cell { background: #FFFFFF; border-radius: 15px; display: flex; justify-content: center; align-items: center; font-size: 6rem; font-weight: bold; color: #333; box-shadow: inset 0 0 10px rgba(0,0,0,0.05);}
        .cell.X { color: #e74c3c; } .cell.O { color: #2ecc71; }
        h1 { margin: 0 0 10px 0; font-size: 2.5rem; color: #4a4036; }
        .status-msg { font-size: 2rem; margin-top: 20px; color: #d35400; font-weight: bold; }
        .diff-badge { background: #333; color: white; padding: 5px 15px; border-radius: 20px; font-size: 1rem; margin-bottom: 10px;}
    </style>
    <script>
        setInterval(() => {
            fetch('/status').then(res => res.json()).then(data => {
                data.board.forEach((mark, i) => {
                    const cell = document.getElementById('c' + i);
                    cell.innerText = mark;
                    cell.className = 'cell ' + mark;
                });
                document.getElementById('diff-display').innerText = (data.difficulty ? data.difficulty : "SETUP") + " MODE";
                const msgBox = document.getElementById('msg');
                if (data.winner) {
                    msgBox.innerText = (data.winner === 'Draw') ? "무승부! 🤝" : (data.winner + " 승리! 🎉");
                } else {
                    msgBox.innerText = (data.turn === 'X') ? "PLAYER의 차례 (X)" : "로봇 생각 중... 🤖";
                }
            });
        }, 500); // 0.5초마다 갱신
    </script>
</head>
<body>
    <div class="left-panel">
        <div class="grid">
            <div class="cell" id="c0"></div><div class="cell" id="c1"></div><div class="cell" id="c2"></div>
            <div class="cell" id="c3"></div><div class="cell" id="c4"></div><div class="cell" id="c5"></div>
            <div class="cell" id="c6"></div><div class="cell" id="c7"></div><div class="cell" id="c8"></div>
        </div>
    </div>
    <div class="right-panel">
        <h1>AI vs HUMAN</h1>
        <div class="diff-badge" id="diff-display">SETUP MODE</div>
        <img src="/qrcode" style="width:180px; border-radius:10px;">
        <div style="margin-top:10px; color:#7f8c8d;">QR 스캔하여 접속</div>
        <div class="status-msg" id="msg">대기 중...</div>
    </div>
</body>
</html>
"""

# [핸드폰 화면] 새로고침 제거 & 실시간 연동 적용
CONTROLLER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Arial', sans-serif; text-align: center; background: #F5F5DC; padding: 20px; color: #333; user-select: none; }
        #setup-screen { display: block; margin-top: 50px; }
        .diff-btn { display: block; width: 100%; padding: 20px; margin: 15px 0; font-size: 1.5rem; border: none; border-radius: 15px; cursor: pointer; color: white; box-shadow: 0 5px 10px rgba(0,0,0,0.2);}
        .easy { background-color: #2ecc71; } .hard { background-color: #e74c3c; }
        #game-screen { display: none; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; max-width: 400px; margin: 20px auto; }
        .game-btn { height: 90px; font-size: 2.5rem; border: none; border-radius: 15px; background: white; box-shadow: 0 5px 10px rgba(0,0,0,0.1); transition: 0.1s;}
        .game-btn:active { transform: scale(0.95); }
        .game-btn.X { color: #e74c3c; } .game-btn.O { color: #2ecc71; }
        .reset-btn { margin-top: 30px; padding: 15px 30px; background: #2c3e50; color: white; border-radius: 50px; border:none; font-size:1.2rem;}
        #turn-msg { font-size: 1.2rem; color: #7f8c8d; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div id="setup-screen">
        <h2>PLAYER 1</h2>
        <p>난이도를 선택하세요</p>
        <button class="diff-btn easy" onclick="setDifficulty('EASY')">🐣 쉬움 (Easy)</button>
        <button class="diff-btn hard" onclick="setDifficulty('HARD')">🔥 어려움 (Hard)</button>
    </div>

    <div id="game-screen">
        <h2 id="mode-title">PLAYER 1</h2>
        <p id="turn-msg">당신의 차례입니다 (X)</p>
        <div class="grid" id="grid"></div>
        <button class="reset-btn" onclick="resetGame()">🔄 처음으로</button>
    </div>

    <script>
        // 화면 깜빡임 없이 상태를 계속 확인하는 함수
        setInterval(() => {
            fetch('/status').then(res => res.json()).then(data => {
                updateScreen(data);
            });
        }, 500); // 0.5초마다 서버 확인

        function updateScreen(data) {
            // 난이도가 없으면(초기화 상태) -> 난이도 선택 화면 보여줌
            if (!data.difficulty) {
                document.getElementById('setup-screen').style.display = 'block';
                document.getElementById('game-screen').style.display = 'none';
                return;
            }

            // 게임 중이면 -> 게임 화면 보여줌
            document.getElementById('setup-screen').style.display = 'none';
            document.getElementById('game-screen').style.display = 'block';
            document.getElementById('mode-title').innerText = data.difficulty + " MODE";
            
            // 턴 메시지
            const msg = document.getElementById('turn-msg');
            if (data.winner) msg.innerText = (data.winner === 'Draw') ? "무승부!" : data.winner + " 승리!";
            else msg.innerText = (data.turn === 'X') ? "당신의 차례 (X)" : "로봇이 두는 중...";

            // 보드 그리기 (새로고침 없이 내용만 변경)
            const grid = document.getElementById('grid');
            if (grid.childElementCount === 0) {
                // 버튼이 없으면 9개 생성
                for (let i = 0; i < 9; i++) {
                    const btn = document.createElement('button');
                    btn.className = 'game-btn';
                    btn.id = 'btn-' + i;
                    btn.onclick = () => sendMove(i);
                    grid.appendChild(btn);
                }
            }

            // 버튼 상태 업데이트
            data.board.forEach((mark, i) => {
                const btn = document.getElementById('btn-' + i);
                btn.innerText = mark;
                btn.className = 'game-btn ' + mark;
                // 이미 둔 곳이나 로봇 턴이면 클릭 방지
                btn.disabled = (mark !== '' || data.turn !== 'X' || data.winner !== null);
            });
        }

        function setDifficulty(mode) {
            fetch('/set_difficulty', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ difficulty: mode })
            });
        }

        function sendMove(idx) {
            // 클릭 즉시 버튼 비활성화 (중복 클릭 방지)
            document.getElementById('btn-' + idx).disabled = true;
            fetch('/move', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ index: idx })
            });
        }

        function resetGame() {
            if(confirm("초기 화면으로 돌아가시겠습니까?")) {
                fetch('/reset');
            }
        }
    </script>
</body>
</html>
"""

@app.route('/qrcode')
def qr():
    img = qrcode.make(CONTROLLER_URL)
    buf = io.BytesIO(); img.save(buf); buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/display')
def dp(): return render_template_string(DISPLAY_HTML, host_url=CONTROLLER_URL)

@app.route('/controller')
def cp(): return render_template_string(CONTROLLER_HTML)

@app.route('/status')
def st(): return jsonify({'board':board, 'winner':game_winner, 'turn':turn, 'difficulty':difficulty})

@app.route('/set_difficulty', methods=['POST'])
def set_diff():
    global difficulty, board, game_winner, turn
    board=['']*9; game_winner=None; turn='X'
    difficulty = request.json.get('difficulty')
    move_to_home() 
    return jsonify({'status':'ok'})

@app.route('/move', methods=['POST'])
def mv():
    global turn, game_winner
    idx = request.json.get('index')
    
    # 예외 처리
    if game_winner or turn!='X' or board[idx]!='': 
        return jsonify({'status':'error'})

    board[idx]='X'
    game_winner = check_winner(board)
    
    if not game_winner:
        turn = 'O'
        ai = get_ai_move(board)
        if ai is not None:
            print(f"🤖 로봇 이동: {ai+1}번")
            move_robot_smoothly(ai+1) # 부드럽게 이동
            board[ai]='O'
            game_winner = check_winner(board)
        turn = 'X'

    return jsonify({'status':'ok', 'board':board})

@app.route('/reset')
def rs():
    global board, game_winner, turn, difficulty
    board=['']*9; game_winner=None; turn='X'; difficulty=None # 난이도 초기화
    move_to_home()
    return jsonify({'status':'reset'})

if __name__ == '__main__':
    print(f"\n🚀 서버 시작! 모니터 주소: http://{SERVER_IP}:{SERVER_PORT}/display")
    move_to_home()
    app.run(host='0.0.0.0', port=SERVER_PORT)