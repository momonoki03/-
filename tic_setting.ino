#include <Servo.h>

// 1. 사용할 서보모터 3개만 선언
Servo base;     // 몸통 (맨 밑)
Servo shoulder; // 어깨 (중간)
Servo elbow;    // 팔꿈치 (끝부분)

// 2. 핀 번호 설정 (사용자님 환경: 4, 5, 6번)
int pin_base = 4;      // 몸통 -> 4번 핀에 연결
int pin_shoulder = 5;  // 어깨 -> 5번 핀에 연결
int pin_elbow = 6;     // 팔꿈치 -> 6번 핀에 연결

String inputString = ""; 

void setup() {
  Serial.begin(115200); // 통신 속도 (파이썬과 동일)

  // 3. 핀 연결
  base.attach(pin_base);
  shoulder.attach(pin_shoulder);
  elbow.attach(pin_elbow);

  // 4. 초기 위치 잡기 (안전하게 90도)
  base.write(90);
  shoulder.write(90);
  elbow.write(90);
}

void loop() {
  // 파이썬에서 데이터가 오면 읽기
  if (Serial.available() > 0) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n') {
      // 엔터키(줄바꿈)를 만나면 해석 시작
      parseCommand(inputString);
      inputString = ""; // 비워주기
    } else {
      inputString += inChar;
    }
  }
}

void parseCommand(String data) {
  // 데이터 형태: "90,90,90,90" (파이썬은 4개를 보냄)
  // 콤마(,) 위치 찾기
  int firstComma = data.indexOf(',');
  int secondComma = data.indexOf(',', firstComma + 1);
  int thirdComma = data.indexOf(',', secondComma + 1);

  // 데이터가 정상적으로 4개가 왔다면?
  if (firstComma > 0 && secondComma > 0 && thirdComma > 0) {
    // 숫자로 변환
    int val1 = data.substring(0, firstComma).toInt();
    int val2 = data.substring(firstComma + 1, secondComma).toInt();
    int val3 = data.substring(secondComma + 1, thirdComma).toInt();
    
    // 4번째 값(집게)은 읽긴 하지만 모터가 없으므로 무시함
    // int val4 = data.substring(thirdComma + 1).toInt(); 

    // 5. 실제 모터 움직이기 (각도 제한 0~180 안전장치 포함)
    base.write(constrain(val1, 0, 180));     // 4번 핀
    shoulder.write(constrain(val2, 0, 180)); // 5번 핀
    elbow.write(constrain(val3, 0, 180));    // 6번 핀
  }
}
