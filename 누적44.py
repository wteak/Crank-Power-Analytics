import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import sys


# ============================================================
# 1Wh ENERGY X-RAY
# 100mWh 체험 미션 버전
# ============================================================


# ============================================================
# 1. 화면 / 한글 설정
# ============================================================

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('dark_background')


# ============================================================
# 2. Arduino 설정
# ============================================================

PORT = 'COM3'
BAUD_RATE = 115200


# ============================================================
# 3. 전자제품 소비전력 비교 기준
# ============================================================

MICROWAVE_POWER_W = 1000.0   # 전자레인지
TV_POWER_W = 100.0           # TV
FAN_POWER_W = 40.0           # 선풍기


# ============================================================
# 4. 목표 설정
#
# 프로젝트 전체 기준 = 1Wh
# 현장 체험 목표 = 100mWh = 0.1Wh
# ============================================================

PROJECT_TARGET_WH = 1.0

MISSION_TARGET_MWH = 100.0
MISSION_TARGET_WH = MISSION_TARGET_MWH / 1000.0


# ============================================================
# 5. 탄소 배출계수
#
# 기존 프로젝트 자료:
# 0.4173 kgCO2eq / kWh
# ============================================================

CARBON_FACTOR = 0.4173


# ============================================================
# 6. 탄소 체감 비교 기준
# ============================================================

# 500mL 일회용 PET 물병 1개의 탄소발자국 비교 기준
# 약 82.8g CO2eq
# 실제 값은 제조 / 운송 / 재활용 조건에 따라 달라질 수 있음
PET_BOTTLE_CO2_G = 82.8

# CO2 기체 환산 기준
# CO2 몰 질량 = 44 g/mol
# 상온에서 기체 1몰 부피 ≈ 24L
CO2_MOLAR_MASS_G = 44.0
CO2_MOLAR_VOLUME_L = 24.0


# ============================================================
# 7. Arduino 연결
# ============================================================

try:

    ser = serial.Serial(
        PORT,
        BAUD_RATE,
        timeout=1
    )

    print("=" * 55)
    print("          100mWh 체험 미션")
    print("=" * 55)

    print("아두이노 연결 성공!")
    print(f"PORT : {PORT}")
    print(f"BAUD : {BAUD_RATE}")

    print("=" * 55)

    # Arduino 리셋 대기
    time.sleep(2)

    ser.reset_input_buffer()


except Exception as e:

    print("\n아두이노 연결 실패")
    print("오류:", e)

    print("\n확인필요.")
    print("1. Arduino IDE 시리얼 모니터가 닫혀있는지")
    print("2. COM 포트 번호가 맞는지")
    print("3. Baud Rate가 115200")

    sys.exit()


# ============================================================
# 8. 화면 생성
# ============================================================

fig = plt.figure(
    figsize=(15, 9)
)

fig.canvas.manager.set_window_title(
    '1Wh Energy X-Ray Dashboard'
)


# ------------------------------------------------------------
# 그래프
# ------------------------------------------------------------

ax_graph = plt.subplot2grid(
    (8, 1),
    (0, 0),
    rowspan=3
)


# ------------------------------------------------------------
# 현재 출력 / 누적량
# ------------------------------------------------------------

ax_energy = plt.subplot2grid(
    (8, 1),
    (3, 0)
)


# ------------------------------------------------------------
# 체험 목표 게이지
# ------------------------------------------------------------

ax_goal = plt.subplot2grid(
    (8, 1),
    (4, 0)
)


# ------------------------------------------------------------
# 전자제품 비교 + 탄소 비교
# ------------------------------------------------------------

ax_compare = plt.subplot2grid(
    (8, 1),
    (5, 0),
    rowspan=3
)


ax_energy.axis('off')
ax_goal.axis('off')
ax_compare.axis('off')


# ============================================================
# 9. 데이터 변수
# ============================================================

x_data = []
y_energy = []

cumulative_energy_J = 0.0

start_time = time.time()
last_time = start_time

mission_announced = False


# ============================================================
# 10. 남은 시간 계산용
#
# 순간 출력은 손 움직임 때문에 너무 흔들리므로
# 최근 출력값의 평균을 사용
# ============================================================

recent_power_values = []

POWER_AVERAGE_COUNT = 20


# ============================================================
# 11. 시간 표시 함수
# ============================================================

def format_time(seconds):

    if seconds <= 0:
        return "0초"

    if seconds < 1:
        return f"{seconds:.2f}초"

    elif seconds < 60:
        return f"{seconds:.1f}초"

    else:

        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)

        return f"{minutes}분 {remaining_seconds}초"


# ============================================================
# 12. 예상 남은 시간 표시 함수
# ============================================================

def format_remaining_time(seconds):

    if seconds is None:
        return "발전을 시작해주세요!"

    if seconds <= 0:
        return "미션 완료!"

    if seconds < 60:
        return f"약 {int(seconds)}초"

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)

    return f"약 {minutes}분 {remaining_seconds}초"


# ============================================================
# 13. 그래프 Y축 자동 조절
#
# 그래프는 확대해서 보여주되
# 최대 목표인 100mWh까지만 확장
# ============================================================

def get_graph_max(energy_mWh):

    if energy_mWh < 5:
        return 5

    elif energy_mWh < 10:
        return 10

    elif energy_mWh < 20:
        return 20

    elif energy_mWh < 30:
        return 30

    elif energy_mWh < 50:
        return 50

    elif energy_mWh < 75:
        return 75

    else:
        return 100


# ============================================================
# 14. 실시간 업데이트
# ============================================================

def update(frame):

    global cumulative_energy_J
    global last_time
    global mission_announced

    try:

        # ====================================================
        # Arduino 데이터 읽기
        # ====================================================

        line = ser.readline().decode(
            'utf-8',
            errors='ignore'
        ).strip()

        if not line:
            return

        if "Power:" not in line:
            return

        # ====================================================
        # Power 값 추출
        # ====================================================

        parts = line.split(',')

        arduino_power_W = None

        for part in parts:

            if "Power:" in part:

                try:

                    power_mW = float(
                        part.split(':')[1]
                    )

                    # Arduino 데이터
                    # mW → W
                    arduino_power_W = power_mW / 1000.0

                except ValueError:
                    return

                break

        if arduino_power_W is None:
            return

        if arduino_power_W < 0:
            arduino_power_W = 0.0

        # ====================================================
        # 최근 출력 평균
        # ====================================================

        recent_power_values.append(arduino_power_W)

        if len(recent_power_values) > POWER_AVERAGE_COUNT:
            recent_power_values.pop(0)

        average_power_W = (
            sum(recent_power_values)
            / len(recent_power_values)
        )

        # ====================================================
        # 시간 계산
        # ====================================================

        current_time = time.time()

        dt = current_time - last_time
        last_time = current_time

        elapsed = current_time - start_time

        # 비정상적인 시간 증가 방지
        if dt > 2.0:
            dt = 0

        # ====================================================
        # 누적 에너지
        #
        # W × s = J
        # ====================================================

        cumulative_energy_J += (
            arduino_power_W * dt
        )

        # ====================================================
        # J → Wh
        # ====================================================

        cumulative_energy_Wh = (
            cumulative_energy_J / 3600.0
        )

        # ====================================================
        # Wh → mWh
        # ====================================================

        cumulative_energy_mWh = (
            cumulative_energy_Wh * 1000.0
        )

        # ====================================================
        # 체험 목표 진행률
        # ====================================================

        mission_progress = (
            cumulative_energy_mWh / MISSION_TARGET_MWH
        ) * 100.0

        gauge_percent = min(
            mission_progress,
            100.0
        )

        # ====================================================
        # 1Wh 기준 진행률
        # ====================================================

        project_progress = (
            cumulative_energy_Wh / PROJECT_TARGET_WH
        ) * 100.0

        # ====================================================
        # 예상 남은 시간
        # ====================================================

        remaining_mWh = max(
            0,
            MISSION_TARGET_MWH - cumulative_energy_mWh
        )

        # mWh → Wh
        remaining_Wh = (
            remaining_mWh / 1000.0
        )

        # ----------------------------------------------------
        # 시간(h) = Energy(Wh) / Power(W)
        # ----------------------------------------------------

        if average_power_W > 0.3:

            remaining_hours = (
                remaining_Wh / average_power_W
            )

            remaining_seconds = (
                remaining_hours * 3600.0
            )

        else:
            remaining_seconds = None

        # ====================================================
        # 전자제품 사용 가능 시간
        # ====================================================

        microwave_seconds = (
            cumulative_energy_J / MICROWAVE_POWER_W
        )

        tv_seconds = (
            cumulative_energy_J / TV_POWER_W
        )

        fan_seconds = (
            cumulative_energy_J / FAN_POWER_W
        )

        # ====================================================
        # 탄소 저감량 계산
        # ====================================================

        cumulative_energy_kWh = (
            cumulative_energy_Wh / 1000.0
        )

        carbon_saved_kg = (
            cumulative_energy_kWh * CARBON_FACTOR
        )

        carbon_saved_g = (
            carbon_saved_kg * 1000.0
        )

        carbon_saved_mg = (
            carbon_saved_g * 1000.0
        )

        # ====================================================
        # 탄소 저감량 → CO2 기체 부피 환산
        # ====================================================

        co2_moles = (
            carbon_saved_g / CO2_MOLAR_MASS_G
        )

        co2_volume_L = (
            co2_moles * CO2_MOLAR_VOLUME_L
        )

        co2_volume_mL = (
            co2_volume_L * 1000.0
        )

        # ====================================================
        # 탄소 저감량 → PET 물병 탄소발자국과 비교
        # ====================================================

        pet_bottle_equivalent = (
            carbon_saved_g / PET_BOTTLE_CO2_G
        )

        pet_bottle_percent = (
            pet_bottle_equivalent * 100.0
        )

        # ====================================================
        # 그래프 데이터
        # ====================================================

        x_data.append(elapsed)
        y_energy.append(cumulative_energy_mWh)

        # 최근 150개 데이터 표시
        x_show = x_data[-150:]
        y_show = y_energy[-150:]

        # ====================================================
        # 15. 그래프 그리기
        # ====================================================

        ax_graph.clear()

        ax_graph.plot(
            x_show,
            y_show,
            color='#00FF66',
            linewidth=4
        )

        ax_graph.fill_between(
            x_show,
            y_show,
            color='#00FF66',
            alpha=0.25
        )

        ax_graph.set_title(
            "⚡ 내가 직접 만들고 있는 에너지",
            fontsize=21,
            fontweight='bold',
            pad=15
        )

        ax_graph.set_ylabel(
            "누적 생산 에너지 (mWh)",
            fontsize=13
        )

        ax_graph.set_xlabel(
            "발전 시간 (초)",
            fontsize=12
        )

        ax_graph.grid(
            True,
            linestyle='--',
            alpha=0.30
        )

        # ====================================================
        # Y축 자동 확대
        # ====================================================

        graph_max = get_graph_max(cumulative_energy_mWh)

        ax_graph.set_ylim(
            0,
            graph_max
        )

        # ====================================================
        # 목표를 항상 화면에 표시
        # ====================================================

        ax_graph.text(
            0.98,
            0.93,
            "🎯 체험 목표\n100 mWh",
            transform=ax_graph.transAxes,
            ha='right',
            va='top',
            fontsize=16,
            fontweight='bold',
            color='#00FFFF',
            bbox=dict(
                boxstyle='round,pad=0.5',
                facecolor='#111111',
                edgecolor='#00FFFF',
                alpha=0.9
            )
        )

        # ====================================================
        # 현재값 점
        # ====================================================

        if len(x_show) > 0:

            ax_graph.scatter(
                x_show[-1],
                y_show[-1],
                s=90,
                color='#00FFFF',
                zorder=5
            )

            ax_graph.text(
                x_show[-1],
                y_show[-1] + graph_max * 0.05,
                f"{cumulative_energy_mWh:.1f} mWh",
                fontsize=13,
                fontweight='bold',
                color='#00FFFF',
                ha='right'
            )

        # ====================================================
        # 16. 현재 출력 / 누적량
        # ====================================================

        ax_energy.clear()
        ax_energy.axis('off')

        ax_energy.set_xlim(0, 1)
        ax_energy.set_ylim(0, 1)

        # 현재 출력
        ax_energy.text(
            0.03,
            0.55,
            f"⚡ 현재 발전 출력   {arduino_power_W:.2f} W",
            fontsize=17,
            fontweight='bold',
            color='white'
        )

        # 누적 생산량
        ax_energy.text(
            0.50,
            0.55,
            f"누적 생산 에너지   {cumulative_energy_mWh:.1f} mWh",
            ha='center',
            fontsize=23,
            fontweight='bold',
            color='#00FFFF'
        )

        # Wh
        ax_energy.text(
            0.97,
            0.55,
            f"{cumulative_energy_Wh:.4f} Wh",
            ha='right',
            fontsize=15,
            fontweight='bold',
            color='#AAAAAA'
        )

        # ====================================================
        # 17. 체험 목표 게이지
        # ====================================================

        ax_goal.clear()
        ax_goal.axis('off')

        ax_goal.set_xlim(0, 1)
        ax_goal.set_ylim(-0.5, 1)

        gauge_width = 0.80

        filled_width = (
            gauge_width * gauge_percent / 100.0
        )

        # 배경
        ax_goal.barh(
            0.3,
            gauge_width,
            left=0.10,
            height=0.20,
            color='#333333'
        )

        # 진행량
        ax_goal.barh(
            0.3,
            filled_width,
            left=0.10,
            height=0.20,
            color='#00FFFF'
        )

        # ====================================================
        # 목표 / 진행률
        # ====================================================

        ax_goal.text(
            0.50,
            0.75,
            f"🎯 100mWh 체험 미션   {cumulative_energy_mWh:.1f} / 100 mWh",
            ha='center',
            fontsize=18,
            fontweight='bold',
            color='#FFFF00'
        )

        ax_goal.text(
            0.25,
            -0.15,
            f"진행률  {mission_progress:.1f}%",
            ha='center',
            fontsize=15,
            fontweight='bold',
            color='white'
        )

        # ====================================================
        # 예상 남은 시간
        # ====================================================

        ax_goal.text(
            0.75,
            -0.15,
            f"⏱ 현재 페이스 예상 {format_remaining_time(remaining_seconds)}",
            ha='center',
            fontsize=15,
            fontweight='bold',
            color='#00FF66'
        )

        # ====================================================
        # 1Wh와 관계
        # ====================================================

        ax_goal.text(
            0.50,
            -0.42,
            f"100mWh = 1Wh의 10%   |   현재 1Wh 기준 {project_progress:.1f}%",
            ha='center',
            fontsize=11,
            color='#AAAAAA'
        )

        # ====================================================
        # 18. 전자제품 + 탄소 비교
        # ====================================================

        ax_compare.clear()
        ax_compare.axis('off')

        compare_text = (
            "내가 만든 전기로 무엇을 할 수 있을까?\n\n"
            f"🍚  전자레인지 (1,000W)   →   {format_time(microwave_seconds)}\n"
            f"📺  TV (100W)             →   {format_time(tv_seconds)}\n"
            f"🌀  선풍기 (40W)           →   {format_time(fan_seconds)}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌱  탄소 저감 효과         →   {carbon_saved_mg:.2f} mg CO₂eq\n"
            f"💨  CO₂ 기체로 환산        →   약 {co2_volume_mL:.1f} mL\n"
            f"🧴  500mL 페트병 기준      →   1개 탄소발자국의 약 {pet_bottle_percent:.3f}%"
        )

        ax_compare.text(
            0.50,
            0.66,
            compare_text,
            ha='center',
            va='center',
            fontsize=14,
            fontweight='bold',
            color='white',
            linespacing=1.20
        )

        # 설명
        ax_compare.text(
            0.50,
            0.06,
            "※ 전자제품 소비전력과 PET병 탄소발자국은 비교를 위한 기준값이며, "
            "제품·제조·사용 환경에 따라 실제 값은 달라질 수 있습니다.",
            ha='center',
            fontsize=9,
            color='#AAAAAA'
        )

        # ====================================================
        # 19. 100mWh 미션 성공
        # ====================================================

        if cumulative_energy_mWh >= MISSION_TARGET_MWH:

            ax_goal.text(
                0.50,
                1.12,
                "🎉 100mWh 성공! 🎉",
                ha='center',
                fontsize=25,
                fontweight='bold',
                color='#00FF66'
            )

            if not mission_announced:

                print()
                print("=" * 55)
                print("       🎉 100mWh 성공! 🎉")
                print("=" * 55)

                print(
                    "생산 에너지:",
                    f"{cumulative_energy_mWh:.1f} mWh"
                )

                print(
                    "전자레인지 (1000W):",
                    format_time(microwave_seconds)
                )

                print(
                    "TV (100W):",
                    format_time(tv_seconds)
                )

                print(
                    "선풍기 (40W):",
                    format_time(fan_seconds)
                )

                print()

                print(
                    "탄소 저감 효과:",
                    f"{carbon_saved_mg:.2f}",
                    "mg CO2eq"
                )

                print(
                    "CO2 기체 부피 환산:",
                    f"{co2_volume_mL:.1f}",
                    "mL"
                )

                print(
                    "500mL PET병 탄소발자국 대비:",
                    f"{pet_bottle_percent:.3f}%"
                )

                print("=" * 55)

                mission_announced = True

    except Exception as e:

        print("데이터 처리 오류:", e)


# ============================================================
# 20. 프로그램 종료
# ============================================================

def on_close(event):

    try:

        if ser.is_open:
            ser.close()
            print("\n시리얼 포트를 종료했습니다.")

    except Exception:
        pass


fig.canvas.mpl_connect(
    'close_event',
    on_close
)


# ============================================================
# 21. 애니메이션 실행
# ============================================================

ani = animation.FuncAnimation(
    fig,
    update,
    interval=200,
    cache_frame_data=False
)

plt.tight_layout(
    rect=[0.02, 0.03, 0.98, 0.98]
)

plt.show()