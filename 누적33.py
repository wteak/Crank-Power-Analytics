import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import sys

# ---------------- [설정 부분] ----------------
PORT = 'COM3' 
BAUD_RATE = 115200 

# 목표치: 전자레인지(1200W)를 1분(60초) 가동하기 위한 필요 에너지 (Joule = W * s)
TARGET_POWER_W = 1200
TARGET_TIME_S = 60
TARGET_ENERGY_J = TARGET_POWER_W * TARGET_TIME_S  # 72,000 J

CARBON_COEF = 0.45  # 전력 탄소 배출계수 (kg CO2/kWh)
# ---------------------------------------------

try:
    ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
    print(f"{PORT} 포트 연결 완료.")
except Exception as e:
    print(f"포트 연결 실패: {e}")
    sys.exit()

fig, ax = plt.subplots(figsize=(10, 6))
fig.canvas.manager.set_window_title('Maker Faire 2026 - Cumulative Energy Dashboard')

x_data, y_energy = [], []
cumulative_energy_J = 0.0
start_time = time.time()
last_time = start_time

def update(frame):
    global cumulative_energy_J, last_time
    try:
        line = ser.readline().decode('utf-8').strip()
        
        if line and "Power:" in line:
            parts = line.split(',')
            arduino_power_W = 0.0
            
            # 아두이노 전력 데이터 파싱 (mW -> W)
            for part in parts:
                if "Power:" in part:
                    power_mW = float(part.split(':')[1])
                    arduino_power_W = power_mW / 1000.0
                    break
            
            # 시간 간격(dt) 계산
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            elapsed_time = current_time - start_time
            
            # 실시간 누적 에너지 계산 (Joule = W * s)
            cumulative_energy_J += arduino_power_W * dt
            
            x_data.append(elapsed_time)
            y_energy.append(cumulative_energy_J)
            
            # 최근 100개의 데이터 포인트만 화면에 출력
            x_show = x_data[-100:]
            y_show = y_energy[-100:]
            
            ax.clear()
            
            # 누적 에너지 그래프 및 목표치 가이드라인
            ax.plot(x_show, y_show, label='누적 생산 에너지 (J)', color='green', linewidth=3)
            ax.axhline(y=TARGET_ENERGY_J, color='red', linestyle='--', label=f'목표치 ({TARGET_ENERGY_J} J)')
            
            # 진행률 및 통계 연산
            progress_percent = (cumulative_energy_J / TARGET_ENERGY_J) * 100
            avg_power = cumulative_energy_J / elapsed_time if elapsed_time > 0 else 0
            
            # 남은 예상 시간 연산
            remaining_time_s = (TARGET_ENERGY_J - cumulative_energy_J) / avg_power if avg_power > 0 else 0
            
            # 탄소 절감량 연산 (생산한 에너지를 kWh로 환산 후 계수 적용)
            # 1 J = 1/3,600,000 kWh
            carbon_saved = (cumulative_energy_J / 3600000.0) * CARBON_COEF
            
            # 대시보드 텍스트 출력
            title_text = (
                f"[ 누적 발전 에너지 대시보드 ]\n\n"
                f"현재 출력: {arduino_power_W:.3f} W  |  평균 출력: {avg_power:.3f} W\n"
                f"누적 에너지: {cumulative_energy_J:.1f} J / 목표 {TARGET_ENERGY_J} J ({progress_percent:.3f}% 달성)\n"
                f"이 속도로 전자레인지 1분 분량 채우기까지 남은 시간: {remaining_time_s:.0f} 초\n"
                f"화석연료 대체 탄소 감축량: {carbon_saved:.6f} kg CO2"
            )
            
            ax.set_title(title_text, fontsize=12, fontweight='bold', pad=15)
            ax.set_xlabel("Time (Seconds)", fontsize=10)
            ax.set_ylabel("Cumulative Energy (Joules)", fontsize=10)
            
            # Y축 상한선 동적 조정 (그래프가 위로 뚫고 나가지 않도록)
            ax.set_ylim(0, max(100, cumulative_energy_J * 1.2))
            ax.legend(loc='upper left')
            
    except ValueError:
        pass
    except Exception:
        pass

# 0.2초(200ms) 간격으로 그래프 갱신
ani = animation.FuncAnimation(fig, update, interval=200)

plt.tight_layout()
plt.show()