import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time

# ---------------- [설정 부분] ----------------
# 1. 아두이노 포트 번호 입력 (예: 'COM3')
PORT = 'COM3' 
# 아두이노 코드의 Serial.begin(115200) 속도와 일치시킴
BAUD_RATE = 115200 

# 2. AI 기반 가전기기 데이터 (예: 전자레인지 1200W)
TARGET_POWER = 1200 
CARBON_COEF = 0.45  # 전력 탄소 배출계수 (kg CO2/kWh)
# ---------------------------------------------

# 시리얼 포트 연결
try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
    print(f"{PORT} 포트에 정상적으로 연결되었습니다.")
except Exception as e:
    print(f"포트 연결 실패: {e}")
    exit()

fig, ax = plt.subplots(figsize=(10, 6))
fig.canvas.manager.set_window_title('Maker Faire 2026 - Energy Dashboard')

x_data, y_arduino, y_target = [], [], []
start_time = time.time()

def update(frame):
    try:
        # 아두이노에서 전송한 데이터 한 줄 읽기
        line = ser.readline().decode('utf-8').strip()
        
        # 데이터가 비어있지 않고, "Power:" 문자열이 포함된 경우에만 실행
        if line and "Power:" in line:
            # 1. 문자열을 쉼표(,) 기준으로 분리 (예: ['Current:1.5', 'Voltage:3.0', 'Power:4.5'])
            parts = line.split(',')
            
            arduino_power_W = 0.0
            
            # 2. 분리된 항목 중 "Power"가 있는 부분을 찾아 값 추출
            for part in parts:
                if "Power:" in part:
                    # 'Power:4.5' -> ':' 기준으로 나누고 두 번째 값(인덱스 1)을 float로 변환
                    power_mW_str = part.split(':')[1]
                    power_mW = float(power_mW_str)
                    
                    # 3. 아두이노는 mW 단위이므로 W 단위로 변환 (1000으로 나눔)
                    arduino_power_W = power_mW / 1000.0
                    break
            
            current_time = time.time() - start_time
            
            # 데이터 리스트에 추가
            x_data.append(current_time)
            y_arduino.append(arduino_power_W)
            y_target.append(TARGET_POWER) 
            
            # 최근 60개 데이터만 슬라이싱하여 출력
            x_show = x_data[-60:]
            y_ard_show = y_arduino[-60:]
            y_tar_show = y_target[-60:]
            
            ax.clear()
            
            # 그래프 그리기
            ax.plot(x_show, y_ard_show, label='Generator Power (W)', color='blue', linewidth=2)
            ax.plot(x_show, y_tar_show, label='Microwave Power (1200W)', color='red', linestyle='--', linewidth=2)
            
            # 시간 및 탄소량 계산
            time_required_mins = (TARGET_POWER / arduino_power_W) if arduino_power_W > 0 else 0
            carbon_emission = (TARGET_POWER / 1000) * (1 / 60) * CARBON_COEF 

            # 화면 텍스트 설정
            title_text = (
                f"[ Energy Production vs Consumption ]\n\n"
                f"Generator: {arduino_power_W:.3f} W  |  Microwave: {TARGET_POWER} W\n"
                f"1분 사용하려면 발전기를 {time_required_mins:.0f}분 돌려야 합니다.\n"
                f"전자레인지 1분 가동 시 탄소 배출량: {carbon_emission:.4f} kg CO2"
            )
            ax.set_title(title_text, fontsize=12, fontweight='bold', pad=15)
            ax.set_xlabel("Time (Seconds)", fontsize=10)
            ax.set_ylabel("Power (Watt)", fontsize=10)
            ax.set_ylim(0, TARGET_POWER + 200) 
            ax.legend(loc='center right')
            
    except ValueError:
        pass
    except Exception as e:
        print(f"오류 발생: {e}")

ani = animation.FuncAnimation(fig, update, interval=200) # 아두이노 delay(200)과 간격 동기화

plt.tight_layout()
plt.show()