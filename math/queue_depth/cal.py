import os
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 14})


def calculate_probability(filename):
    try:
        with open(filename, "r") as file:
            lines = file.readlines()
        total_count = 0
        all_zero_count = 0
        for line in lines:
            # Split the line by spaces and get the queue depths
            parts = line.strip().split()
            if len(parts) >= 5:
                q1 = int(parts[1].split("=")[1])
                q2 = int(parts[2].split("=")[1])
                q3 = int(parts[3].split("=")[1])
                q4 = int(parts[4].split("=")[1])
                total_count += 1
                if q1 == 0 and q2 == 0 and q3 == 0 and q4 == 0:
                    all_zero_count += 1
        probability = all_zero_count / total_count if total_count > 0 else 0
        return probability
    except FileNotFoundError:
        print(f"File '{filename}' not found.")
        return None


# 主程序
load_levels = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
directory = r"C:\Users\KLAY\Desktop\模擬\math\queue_depth"
probabilities = []

for load in load_levels:
    filename = os.path.join(directory, f"queue_depth_{load}.txt")

    # 如果文件不存在，則創建空文件
    if not os.path.exists(filename):
        with open(filename, "w") as file:
            file.write("")
    # 計算並存儲機率
    probability = calculate_probability(filename)
    if probability is not None:
        print(
            f"The probability that all four queues are zero for load {load}% is: {probability:.4f}"
        )
        probabilities.append(probability)

# 數學分析結果
math_probabilities = [
    0.6561,
    0.4096,
    0.2401,
    0.1296,
    0.0625,
    0.0256,
    0.0081,
    0.0016,
    0.0001,
    0.0000,
]

# 繪製負載 vs 機率的曲線
plt.figure(figsize=(10, 6))
# 繪製模擬結果的曲線
plt.plot(
    load_levels, probabilities, marker="o", linestyle="-", color="b", label="Simulation"
)
# 繪製數學分析結果的曲線
plt.plot(
    load_levels, math_probabilities, marker="x", linestyle="--", color="r", label="Math"
)
# 設置 x 軸和 y 軸的刻度
plt.xticks(load_levels)  # x 軸刻度為每 5% 一級
plt.yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], ["0%", "20%", "40%", "60%", "80%", "100%"])
# 添加圖標 (legend)
plt.legend()
# 添加標題和軸標籤
plt.title("Probability that the four queues are empty")
plt.xlabel("Network Load (%)")
plt.ylabel("Probability")
# 添加網格線
plt.grid(True)

# 保存圖形為圖檔 (e.g., PNG格式)
output_path = r"C:\Users\KLAY\Desktop\模擬\math\queue_depth\simulation_result.png"
plt.savefig(output_path)

# 顯示圖形
plt.show()
