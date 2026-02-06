#include <Servo.h>

Servo servos[4];

// [중요] 사용 중인 핀 번호로 수정하세요! (사용자님 환경: 3, 5, 6, 9 예상)
// PDF 문서 기준은 4, 5, 6, 7 이지만 실제 연결에 맞춰야 합니다.
int pins[4] = {4, 5, 6, 7}; 
int angles[4] = {90, 90, 90, 90}; // 현재 각도 저장

void setup() {
  // 통신 속도 115200 (파이썬과 속도가 같아야 합니다!)
  Serial.begin(115200);
  
  for(int i=0; i<4; i++){
    servos[i].attach(pins[i]);
    servos[i].write(angles[i]);
  }
}

void loop() {
  // PC에서 데이터가 들어오면?
  if (Serial.available() > 0) {
    // 줄바꿈 문자('\n')가 나올 때까지 읽음
    String data = Serial.readStringUntil('\n');
    
    // 콤마(,)를 기준으로 숫자 4개를 쪼개서 읽음
    int firstComma = data.indexOf(',');
    int secondComma = data.indexOf(',', firstComma + 1);
    int thirdComma = data.indexOf(',', secondComma + 1);
    
    // 데이터가 정상적일 때만 모터 움직임
    if(firstComma > 0 && secondComma > 0 && thirdComma > 0) {
      angles[0] = data.substring(0, firstComma).toInt();
      angles[1] = data.substring(firstComma + 1, secondComma).toInt();
      angles[2] = data.substring(secondComma + 1, thirdComma).toInt();
      angles[3] = data.substring(thirdComma + 1).toInt();
      
      // 모터에 각도 적용
      for(int i=0; i<4; i++) {
        servos[i].write(angles[i]);
      }
    }
  }
}