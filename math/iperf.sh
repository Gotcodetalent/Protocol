#!/bin/bash
# 定義主機IP映射
declare -A host_ips=(
  [h1]="10.1.1.2"
  [h2]="10.1.2.2"
  [h3]="10.6.3.2"
  [h4]="10.6.4.2"
)
# 設定 queue depth 和 queue rate
queue_depth=50
queue_rate=60
# 配置交換器列表
switches=("s1" "s2" "s3" "s4" "s5" "s6")
for switch in "${switches[@]}"; do
  thrift_port=$((9090 + ${switch: -1} - 1))
  simple_switch_CLI --thrift-port $thrift_port <<EOF
  set_queue_depth $queue_depth
  set_queue_rate $queue_rate
EOF
done
# 啟動 iperf 伺服器（TCP）
echo "Starting iperf TCP servers..."
for i in {1..4}; do
  mx h$i iperf -s -i 1 -p 5555 &
done
sleep 5  # 確保伺服器有足夠的時間啟動
# 確保文件目錄存在
mkdir -p ./iperf_results
# 等待所有流量完成
wait_for_flows_to_finish() {
  for i in {1..4}; do
    while pgrep -f "iperf -c ${host_ips[h$i]} -p 5555" > /dev/null; do
      sleep 1
    done
  done
}
# 定義隨機種子
seeds=(01423 123456 85346 69530 34567 45678 56789 66666 78901 89012 33225 23485 54321 39812 12987 87654 23489 90876 56743 43210 
       11021 12034 13045 14056 15067 16078 17089 18090 19012 20023 21034 22045 23056 24067 25078 26089 27090 28012 29023 30034 
       31045 32056 33067 34078 35089 36090 37012 38023 39034 40045 41056 42067 43078 44089 45090 46012 47023 48034 49045 50056 
       51067 52078 53089 54090 55012 56023 57034 58045 59056 60067 61078 62089 63090 64012 65023 66034 67045 68056 69067 70078 
       71089 72090 73012 74023 75034 76045 77056 78067 79078 80089 81090 82012 83023 84034 85045 86056 87067 88078 89089 90012)
# 重複測試
for load in {5..50..5}; do
  echo "Starting tests for load $load%"
  # 為每個負載層級創建單獨的結果文件
  result_file="./iperf_results/qdepth_${load}.txt"
  > $result_file
  load_bandwidth=$(echo "scale=2; 24.0 * ($load / 100.0)" | bc)
  # 根據負載層級計算 lambda 值
  avg_request_size_kb=118  # 平均每個iperf請求的大小根據分佈計算為118KB
  lambda=$(echo "scale=2; ($load_bandwidth * 1000 ) / (($avg_request_size_kb * 8) + (($load/5.0) - 1) * 2.0)" | bc -l)
  for ((rep=1; rep<=20; rep++)); do
    echo "Repetition $rep"
    # 使用對應的隨機種子
    RANDOM=${seeds[$rep-1]}
    current_bandwidth=0
    transmit_time=20
    while (( $(echo "$current_bandwidth < $load_bandwidth" | bc -l) )); do
      rand_size=$((RANDOM % 100))
      if [ $rand_size -lt 63 ]; then
        size=$((RANDOM % 10 + 1))  # 0KB-10KB (63%)
      elif [ $rand_size -lt 81 ]; then
        size=$((RANDOM % 91 + 10))  # 10KB到100KB (18%)
      else
        size=$((RANDOM % 901 + 100))  # 100KB到1MB (19%)
      fi
      size_bytes=$((size * 1024))  # 將大小轉換為byte
      # 計算對應的bw
      bandwidth=$(awk "BEGIN {printf \"%.2f\", ($size_bytes * 8 * $transmit_time) / ($transmit_time * 1000000)}")
      calculated_bandwidth=$(echo "scale=2; $bandwidth / 1.0" | bc)
      # h1 隨機選擇 h3 或 h4 發送流量
      target1=$((3 + RANDOM % 2))
      mx h1 iperf -c ${host_ips[h$target1]} -b ${calculated_bandwidth}M -l 125 -t $transmit_time -p 5555 &
      # h2 隨機選擇 h3 或 h4 發送流量
      target2=$((3 + RANDOM % 2))
      mx h2 iperf -c ${host_ips[h$target2]} -b ${calculated_bandwidth}M -l 125 -t $transmit_time -p 5555 &
      # h3 隨機選擇 h1 或 h2 發送流量
      target3=$((1 + RANDOM % 2))
      mx h3 iperf -c ${host_ips[h$target3]} -b ${calculated_bandwidth}M -l 125 -t $transmit_time -p 5555 &
      # h4 隨機選擇 h1 或 h2 發送流量
      target4=$((1 + RANDOM % 2))
      mx h4 iperf -c ${host_ips[h$target4]} -b ${calculated_bandwidth}M -l 125 -t $transmit_time -p 5555 &
      current_bandwidth=$(echo "$current_bandwidth + $bandwidth * 4" | bc)
      interval=$(python3 -c "import numpy as np; lmbd=float($lambda); print(np.random.exponential(1.0 / lmbd))")
      [ -z "$interval" ] && interval=$(echo "scale=4; 1.0 / ($load)" | bc)
      sleep $interval
    done
    echo "Completed repetition $rep for load $load% with total bandwidth usage: $current_bandwidth Mb"
    
    # 啟動監控腳本
    ./monitor.sh >> $result_file &
    monitor_script_pid=$!
    sleep 12
    kill $monitor_script_pid
    wait $monitor_script_pid 2>/dev/null
    
    # 等待所有流量傳輸完成
    wait_for_flows_to_finish
  done
  # 在進行下一個負載層級測試之前，關閉所有正在執行的 iperf 請求
  pkill -f "iperf -c"
done
# 終止 iperf TCP 伺服器
for i in {1..4}; do
  mx h$i killall iperf
done
echo "All repetitions completed."
