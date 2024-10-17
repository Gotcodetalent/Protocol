#!/bin/bash
CLI_PATH=/usr/local/bin/simple_switch_CLI
# 获取当前时间（毫秒级）
prev_time=$(date +%s%N | cut -b1-13)
sleep 0.1
while true; do
  # 读取 9090 的 index 0 和 1
  qlen_0_9090=$(echo "register_read qdepth 0" | $CLI_PATH --thrift-port 9090 | grep qdepth | awk '{print $3}')
  qlen_1_9090=$(echo "register_read qdepth 1" | $CLI_PATH --thrift-port 9090 | grep qdepth | awk '{print $3}')
  
  # 读取 9095 的 index 0 和 1
  qlen_0_9095=$(echo "register_read qdepth 0" | $CLI_PATH --thrift-port 9095 | grep qdepth | awk '{print $3}')
  qlen_1_9095=$(echo "register_read qdepth 1" | $CLI_PATH --thrift-port 9095 | grep qdepth | awk '{print $3}')
  # 计算时间间隔
  now=$(date +%s%N | cut -b1-13)
  time=$(echo "scale=2; ($now - $prev_time) / 1000" | bc -l)
  # 输出时间间隔和四个队列的长度
  echo "$time q1=$qlen_0_9090 q2=$qlen_1_9090 q3=$qlen_0_9095 q4=$qlen_1_9095"
  # 休眠 0.1 秒
  sleep 0.1
done
