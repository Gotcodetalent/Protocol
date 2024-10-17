import matplotlib.pyplot as plt
import numpy as np


def read_afct_results(file_path):
    load_to_afcts = {}
    with open(file_path, "r") as file:
        for line in file:
            data = line.strip().split()
            if len(data) == 2:
                load, afct = map(float, data)
                if load not in load_to_afcts:
                    load_to_afcts[load] = []
                load_to_afcts[load].append(afct)
    return load_to_afcts


def calculate_means(load_to_afcts):
    loads = sorted(load_to_afcts.keys())
    afct_means = [np.mean(load_to_afcts[load]) for load in loads]
    return loads, afct_means


# 讀取ECMP和HULA結果
# ecmp_results = read_afct_results("ecmp_results.txt")
hula_results = read_afct_results("afct_results_web.txt")

# 計算平均AFCT值
# ecmp_loads, ecmp_means = calculate_means(ecmp_results)
hula_loads, hula_means = calculate_means(hula_results)

# 檢查是否有數據
if not hula_loads or not hula_means:
    print("No data to plot. Check the input files for issues.")
else:
    # 繪製圖表
    plt.figure(figsize=(10, 6))

    # 繪製HULA結果
    plt.plot(hula_loads, hula_means, marker="s", label="Myway")

    # 設置X軸刻度為10%的間隔
    plt.xticks(np.arange(10, 101, 10))

    # 設置Y軸刻度
    plt.yticks(np.arange(0.0, max(hula_means) + 0.2, 0.1))

    # 標籤和標題
    plt.xlabel("Network Load (%)")
    plt.ylabel("Average Flow Completion Time (s)")
    plt.title("AFCT of web search under different network load")
    plt.grid(True)

    # 顯示圖例
    plt.legend()

    # 保存圖表
    plt.savefig("load_vs_afct.png")
    plt.show()
