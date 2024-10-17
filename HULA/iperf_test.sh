#!/bin/bash

# 定義主機IP映射
declare -A host_ips=(
  [h1]="10.13.1.2"
  [h2]="10.13.2.2"
  [h3]="10.14.3.2"
  [h4]="10.14.4.2"
  [h5]="10.15.5.2"
  [h6]="10.15.6.2"
  [h7]="10.16.7.2"
  [h8]="10.16.8.2"
  [h9]="10.17.9.2"
  [h10]="10.17.10.2"
  [h11]="10.18.11.2"
  [h12]="10.18.12.2"
  [h13]="10.19.13.2"
  [h14]="10.19.14.2"
  [h15]="10.20.15.2"
  [h16]="10.20.16.2"
)

# 啟動 iperf 伺服器（TCP）
echo "Starting iperf TCP servers..."
for i in {1..16}; do
  mx h$i iperf -s -i 1 -p 5555 &
done

sleep 5  # 確保伺服器有足夠的時間啟動

# 清空結果文件
> ./afct_results.txt
> ./afct_99th_results.txt
> ./afct_small_flows.txt
> ./afct_large_flows.txt

# 創建資料夾以保存結果
mkdir -p ./iperf_results

# 總的帶寬為24條鏈路 * 1 Mb = 24 Mb，扣除探測流量後的實際可用帶寬為總帶寬的98%
total_bandwidth=24  # 單位為 Mb
usable_bandwidth=$(echo "$total_bandwidth * 0.98" | bc)

# 基準到達率
base_lambda=5  # 每秒5次事件

# 重複測試次數
repetitions=20

# 定義隨機種子
seeds=(90123 123456 12345 23456 34567 45678 56789 67890 78901 89012 34543 23412 54321 34567 12987 87654 23489 90876 56743 43210)

# 等待流量完成的函數
wait_for_flows_to_finish() {
  for i in {1..16}; do
    while pgrep -f "iperf -c ${host_ips[h$i]} -p 5555" > /dev/null; do
      sleep 1
    done
  done
}

# 重複測試
for ((rep=1; rep<=repetitions; rep++)); do
  echo "Repetition $rep"
  
  # 每輪使用不同的隨機種子
  RANDOM=${seeds[$rep-1]}

  # 執行多次 iperf 測試並記錄結果
  for load in {10..100..10}; do
    echo "Starting tests for load $load%"
    load_bandwidth=$(echo "$usable_bandwidth * $load / 100" | bc)  # 當前負載的總帶寬
    echo "Total bandwidth for $load% load: $load_bandwidth Mb"

    total_fct=0
    flow_count=0
    small_flow_fct=0
    small_flow_count=0
    large_flow_fct=0
    large_flow_count=0
    all_afcts=()

    result_file="./iperf_results/iperf_tcp_results_${load}_rep${rep}.txt"
    > $result_file

    # 動態調整到達率，負載越大，到達率越大
    lambda=$(echo "$base_lambda * $load / 10" | bc -l)

    # 在當前負載層級中循環直到達到預期的負載
    current_bandwidth=0

    # 在每個負載層級開始時重置隨機種子
    RANDOM=${seeds[$rep-1]}

    while (( $(echo "$current_bandwidth < $load_bandwidth" | bc -l) )); do
      # 使用不同的隨機種子生成一對主機
      host1=$((RANDOM % 16 + 1))
      host2=$((RANDOM % 16 + 1))
      while [ $host1 -eq $host2 ]; do
        host2=$((RANDOM % 16 + 1))
      done

      # 使用不同的隨機種子生成流量大小
      rand_size=$((RANDOM % 100))
      if [ $rand_size -lt 63 ]; then
        # 63%的機率選擇0-10KB的流量
        size=$((RANDOM % 10 + 1))
      elif [ $rand_size -lt 81 ]; then
        # 18%的機率選擇10KB-100KB的流量
        size=$((RANDOM % 91 + 10))
      else
        # 19%的機率選擇100KB-1MB的流量
        size=$((RANDOM % 901 + 100))
      fi
      size_bytes=$((size * 1024))  # 將大小轉換為字節數

      # 計算該流量的帶寬（單位：Mbit/s）
      bandwidth=$(awk "BEGIN {printf \"%.2f\", ($size_bytes * 8) / 1000000}")

      # 檢查是否超過當前負載的總帶寬
      if (( $(echo "$current_bandwidth + $bandwidth > $load_bandwidth" | bc -l) )); then
        break
      fi

      echo "Running iperf TCP test from h$host1 to h$host2 with size ${size}KB ($size_bytes bytes)..."
      # 將結果存入變數
      result=$(mx h$host1 iperf -c ${host_ips[h$host2]} -n $size_bytes -p 5555 | grep sec)
      echo "$result" >> $result_file

      # 提取流完成時間 (FCT)
      if [ ! -z "$result" ];then
        start_time=$(echo "$result" | awk '{print $3}' | cut -d'-' -f1)
        end_time=$(echo "$result" | awk '{print $3}' | cut -d'-' -f2)
        fct=$(echo "$end_time - $start_time" | bc)
        total_fct=$(echo "$total_fct + $fct" | bc)
        flow_count=$((flow_count + 1))
        all_afcts+=($fct)

        # 根據流量大小記錄不同的 FCT
        if [ $size -le 100 ]; then
          small_flow_fct=$(echo "$small_flow_fct + $fct" | bc)
          small_flow_count=$((small_flow_count + 1))
        else
          large_flow_fct=$(echo "$large_flow_fct + $fct" | bc)
          large_flow_count=$((large_flow_count + 1))
        fi
      fi

      # 使用泊松過程生成時間間隔，動態調整到達率
      interval=$(python3 -c "import numpy as np; print(np.random.exponential(1.0 / $lambda))")
      if [ -z "$interval" ]; then
        interval=0.1
      fi
      sleep $interval

      current_bandwidth=$(echo "$current_bandwidth + $bandwidth" | bc)
      echo "Current bandwidth: $current_bandwidth Mb / $load_bandwidth Mb"
    done

    # 計算並記錄 AFCT
    if [ $flow_count -ne 0 ];then
      afct=$(echo "scale=4; $total_fct / $flow_count" | bc)
    else
      afct=0
    fi
    echo "$load $afct" >> ./afct_results.txt

    # 計算並記錄小於 100KB 的 AFCT
    if [ $small_flow_count -ne 0 ];then
      small_afct=$(echo "scale=4; $small_flow_fct / $small_flow_count" | bc)
    else
      small_afct=0
    fi
    echo "$load $small_afct" >> ./afct_small_flows.txt

    # 計算並記錄大於 100KB 的 AFCT
    if [ $large_flow_count -ne 0 ];then
      large_afct=$(echo "scale=4; $large_flow_fct / $large_flow_count" | bc)
    else
      large_afct=0
    fi
    echo "$load $large_afct" >> ./afct_large_flows.txt

    # 計算 99th 百分位 AFCT 並記錄
    if [ ${#all_afcts[@]} -ne 0 ];then
      sorted_afcts=($(printf '%s\n' "${all_afcts[@]}" | sort -n))
      index_99th=$(((${#sorted_afcts[@]} - 1) * 99 / 100))
      afct_99th=${sorted_afcts[$index_99th]}
    else
      afct_99th=0
    fi
    echo "$load $afct_99th" >> ./afct_99th_results.txt

    echo "Completed tests for load $load% with total bandwidth usage: $current_bandwidth Mb"

    # 更新 current_bandwidth 為當前負載層級的帶寬
    current_bandwidth=$load_bandwidth
  done
done

# 終止 iperf TCP 伺服器
for i in {1..16}; do
  mx h$i killall iperf
done
