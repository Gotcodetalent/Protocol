# Protocol
概念性實作EIGRP、STP協定

---

# EIGRP Protocol Simulation

本專案為模擬 EIGRP（Enhanced Interior Gateway Routing Protocol）的 C++ 程式。該協定使用距離向量算法來維護交換器間的路由表，並實現快速的路徑更新與拓撲變更處理。

---

## 程式架構

### **主要類別**
- **`EIGRP_Switch`**  
  表示交換器的資料結構，包含以下成員：
  - `id`：交換器的唯一識別碼。
  - `n`：與交換器相連的鏈接數量。
  - `routing`：65536 個目標節點的路徑資訊，`routing[i][0]` 是到節點 `i` 的下一跳，`routing[i][1]` 是該路徑的成本（cost）。

---

## 程式功能

1. **輸入與初始化**
   - 使用者輸入包含交換器資訊的檔案名稱（如 `input.txt`）。
   - 初始化交換器的路由表，將自身設定為 `next-hop` 並將自身成本設為 0。

2. **處理鄰居的 EIGRP 封包**
   - 每次接收來自鄰居交換器的更新封包，模擬以下場景：
     - 如果鄰居到目標交換器的路徑較短，更新本地路由表。
     - 如果本地到目標的路徑較短，標記鄰居需要更新。
   - 根據是否需要更新本地與鄰居的狀態，輸出 "Hello"、"Update" 或 "Update Hello"。

3. **輸出結果**
   - 輸出交換器的路由表至 `output.txt`，包括目標 ID、下一跳與成本資訊。

---

## 範例輸入與輸出

### **輸入檔案格式**
```txt
<ID> <n> 
<p1> <c1>
<p2> <c2>
...
<m>
<EIGRP_ID1> <k1>
<r1> <c1>
...
```
- `<ID>`：交換器的 ID。
- `<n>`：鏈接數量。
- `<p>` 和 `<c>`：鏈接的節點和成本。
- `<m>`：收到的 EIGRP 封包數。
- `<EIGRP_ID>`：封包發送者 ID。
- `<k>`：封包內鏈接的數量。
- `<r>` 和 `<c>`：封包內路徑資訊。

### **範例輸入**
```txt
1 3
2 10
3 20
4 30
2
2 2
3 15
5 25
3 1
5 10
```

### **範例輸出**
```txt
Hello
Update Hello
Switch ID:1
Path:
ID:1, next hop:1, cost:0
ID:2, next hop:2, cost:10
ID:3, next hop:3, cost:15
ID:4, next hop:4, cost:30
ID:5, next hop:3, cost:40
```

---

## 程式邏輯重點

1. **路由表更新規則**
   - 如果本地沒有到目標節點的路徑，但鄰居有，則採用鄰居的路徑。
   - 如果兩者都有到目標節點的路徑，選擇成本較低的路徑。

2. **封包處理流程**
   - 比較當前節點與鄰居節點的路由表。
   - 動態更新路由表後，依更新情況輸出相應的訊息。

---

## 編譯與執行

1. **編譯程式**
   ```bash
   g++ -o eigrp_simulation eigrp_simulation.cpp
   ```

2. **執行程式**
   ```bash
   ./eigrp_simulation
   ```
   - 輸入檔案名稱（如 `input`），程式會自動處理並生成 `output.txt`。
