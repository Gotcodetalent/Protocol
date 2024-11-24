# Protocol
概念性模擬EIGRP、STP協定


# **EIGRP Protocol Simulation**

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


# **Spanning Tree Protocol 模擬程式**

## **概述**
此程式模擬生成樹協議 (STP) 的運作過程，透過以下幾個步驟生成最小生成樹 (Minimum Spanning Tree)：
1. 決定根橋 (Root Bridge)。
2. 建立初始鏈接並選擇最低成本的邊作為樹的一部分。
3. 檢測並移除循環，確保拓撲為無環圖。
4. 計算各節點到根橋的最短路徑。

此模擬程式的實作重點包括：
- **Kruskal 演算法**：用於計算最小生成樹。
- **Dijkstra 演算法**：計算節點到根橋的最短路徑。
- **聯集-尋找結構 (Union-Find)**：避免循環的有效工具。

---

## **主要功能與邏輯說明**

### **1. 初始化與輸入**
- **輸入檔案格式**：
  1. 第一行包含交換器 ID 和優先權 (Priority)。
  2. 第二行為其他交換器的數量與資訊。
  3. 接下來包含所有交換器間的鏈接資訊（起點、終點及頻寬）。
- **初始化資料結構**：
  - 使用 `vector` 儲存鏈接資訊（節點 x, 節點 y, 成本）。
  - 使用 `set` 儲存所有出現的節點，用以確認生成樹是否包含所有節點。

---

### **2. root bridge的選擇**
- 根據優先權選擇根橋，優先權較低者成為根橋。
- 若優先權相同，則選擇 ID 較小的節點作為根橋。

---

### **3. Kruskal 演算法**
- 根據邊的成本排序，優先加入最小成本的邊。
- 利用 `union-find` 檢測循環，避免形成環。
- 將邊的資訊更新到生成樹結構 `spanning_tree` 中。

---

### **4. 計算最短路徑**
- 使用 `Dijkstra` 演算法計算節點到根橋的最短路徑。
- 儲存結果並輸出到檔案。

---

### **5. 生成樹中的埠分類**
- 根據生成樹中的邊狀態，將埠分為：
  - **R port (Root Port)**: 直接連接根橋的埠。
  - **D port (Designated Port)**: 負責傳輸數據的埠。
  - **B port (Blocked Port)**: 不參與傳輸的埠。

---

## **輸出**
- 程式將結果輸出到 `output.txt`，包含：
  1. root ID && priority。
  2. 最短路徑成本總和。
  3. 各種port的數量。

---

### **使用到的演算法**

#### Kruskal ：
```cpp
while (temp != node && tree_edge > 0) {
    for (int i = 0; i < link.size(); ++i) {
        x = link[i][0];
        y = link[i][1];
        link_cost = link[i][2];

        if (union_find(x) != union_find(y)) { // 避免形成循環
            union_[y] = union_[x];
            temp.insert(x);
            temp.insert(y);
            STP_Switch.port[x][y] = 1;
            --tree_edge;
            break;
        }
    }
}
```

#### Dijkstra ：
```cpp
for (int i = 0; i < n - 1; ++i) {
    int minDistance = numeric_limits<int>::max();
    int minIndex = -1;

    for (int j = 0; j < n; ++j) {
        if (!visited[j] && distances[j] < minDistance) {
            minDistance = distances[j];
            minIndex = j;
        }
    }

    visited[minIndex] = true;

    for (int j = 0; j < n; ++j) {
        if (!visited[j] && graph[minIndex][j] != 0) {
            int newDistance = distances[minIndex] + graph[minIndex][j];
            if (newDistance < distances[j]) {
                distances[j] = newDistance;
            }
        }
    }
}

