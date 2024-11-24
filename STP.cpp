#include <iostream>
#include <cstdlib>
#include <String>
#include <fstream>
#include <limits>
#include <vector>
#include <set>
#include <algorithm>
using namespace std;
const int MAX_NODES = 65536;
int cost(int);
int union_[65536] = {0}; // build up spanning tree時紀錄各個node的root

struct
{
    int m;
    int priority[65536] = {0};      // 紀錄priority
    int cost[65536][65536] = {{0}}; // 紀錄cost
    int port[65536][65536] = {{0}}; // 紀錄port default為block(0), designated port (1) root port(2)
    int spanning_tree[65536][65536] = {{INT_MAX}};

} STP_Switch;

bool cmp1(vector<int> &a, vector<int> &b)
{
    return a[2] < b[2]; // 按照第3個元素的大小来排序
}
bool cmp2(vector<int> &a, vector<int> &b)
{
    return a[1] < b[1]; // 按照第2個元素的大小来排序
}

int cost(int bandwidth)
{

    switch (bandwidth)
    {
    case 4:
        return 250;
    case 10:
        return 100;
    case 16:
        return 62;
    case 45:
        return 39;
    case 100:
        return 19;
    case 155:
        return 14;
    case 1000:
        return 4;
    case 10000:
        return 2;
    default:
        return -1;
    }
}

int union_find(int node)
{
    int root = node;
    while (union_[root] != root)
        root = union_[union_[root]];
    return root;
}

int dijkstraShortestPath(int graph[MAX_NODES][MAX_NODES], int n, int start, int end)
{
    int distances[MAX_NODES]; // 距離起始節點的距離
    bool visited[MAX_NODES];  // 是否已訪問節點

    // 初始化距離和訪問陣列
    for (int i = 0; i < n; ++i)
    {
        distances[i] = numeric_limits<int>::max();
        visited[i] = false;
    }

    distances[start] = 0; // 起始節點到自身的距離為0

    for (int i = 0; i < n - 1; ++i)
    {
        int minDistance = numeric_limits<int>::max();
        int minIndex = -1;

        // 選擇距離起始節點最近的未訪問節點
        for (int j = 0; j < n; ++j)
        {
            if (!visited[j] && distances[j] < minDistance)
            {
                minDistance = distances[j];
                minIndex = j; // 選出距離目前node有最短edge的node
            }
        }
        // 標記節點為已訪問
        visited[minIndex] = true;

        // 更新當前節點相鄰節點的最短距離
        for (int j = 0; j < n; ++j)
        {
            if (!visited[j] && graph[minIndex][j] != 0 && distances[minIndex] != numeric_limits<int>::max())
            {
                int newDistance = distances[minIndex] + graph[minIndex][j];
                if (newDistance < distances[j])
                {
                    distances[j] = newDistance;
                }
            }
        }
    }

    // // 印出最短距離
    // for (int i = 0; i < n; ++i)
    // {
    //     if (distances[i] != INT_MAX)
    //         ofs << "從節點 " << start << " 到節點 " << i << " 的最短距離為 " << distances[i] << endl;
    // }

    return distances[end];
}

int main()
{
    ifstream ifs;
    ofstream ofs;

    string name;
    cin >> name;

    ifs.open(name);
    ofs.open("output.txt");

    int id, priority, n;
    ifs >> id >> priority;
    STP_Switch.priority[id] = priority;

    ifs >> n;
    int STP_id, STP_priority, m, x, y, bandwidth, root_id = id, root_priority = priority;

    //**Initialization**-start
    for (int i = 0; i < n; i++) // n筆node資訊 (switch的id、priority)
    {
        ifs >> STP_id >> STP_priority;

        if (STP_priority < root_priority) // 決定root port
        {
            root_priority = STP_priority;
            root_id = STP_id;
        }
        else if (STP_priority == root_priority && STP_id < root_id)
        {
            root_priority = STP_priority;
            root_id = STP_id;
        }
    }

    ifs >> m;

    vector<vector<int>> link; //<x,y,cost>
    set<int> node;

    for (int j = 0; j < m; j++) // m筆link資訊
    {
        ifs >> x >> y >> bandwidth;
        vector<int> temp;
        temp.push_back(x);
        temp.push_back(y);
        temp.push_back(cost(bandwidth));
        link.push_back(temp);
        STP_Switch.cost[x][y] = STP_Switch.cost[y][x] = cost(bandwidth);
        node.insert(x);
        node.insert(y);
    }

    sort(link.begin(), link.end(), cmp1);

    //**Initialization**-end

    int link_cost;

    int tree_edge = n - 1, i = 0; // n+1 nodes 有 n edges, 但因為要先插入root的最小邊 所以為n - 1
    set<int> temp;

    // union的root初始化成自己

    for (int i = 0; i < 1000; i++)
    {
        union_[i] = i;
    }

    // build up spanning tree
    int f = 0;

    for (int i = 0; i < link.size(); i++) // 把root最短那條先丟進去
    {
        if (link[i][0] == root_id || link[i][1] == root_id)
        {
            x = link[i][0];
            y = link[i][1];
            link_cost = link[i][2];

            temp.insert(x);
            temp.insert(y);
            STP_Switch.port[x][y] = 1;
            STP_Switch.port[y][x] = 1;
            STP_Switch.spanning_tree[x][y] = STP_Switch.spanning_tree[y][x] = link_cost;
            if (x == root_id)
                union_[y] = x;
            else
                union_[x] = y;
            f = 1;
        }
        if (f)
            break;
    }

    int root;

    while (temp != node && tree_edge > 0) // node還沒全部加入或edge還沒找滿時
    {
        f = i = 0;
        while (i < link.size() && tree_edge > 0)
        {
            x = link[i][0];
            y = link[i][1];
            link_cost = link[i][2];

            if ((temp.count(x) || temp.count(y)))
            {
                if (union_find(x) != union_find(y)) // 不能選到會產生cycle的edge
                {
                    union_[y] = union_[x];
                    temp.insert(x);
                    temp.insert(y);
                    STP_Switch.port[x][y] = 1;
                    STP_Switch.port[y][x] = 1;
                    STP_Switch.spanning_tree[x][y] = STP_Switch.spanning_tree[y][x] = link_cost;
                    --tree_edge;
                    f = 1; // 找到新的邊要從頭search->確保minimum
                }
            }
            i++;
            if (f)
                break;
        }
    }

    // 計算shortest-path from id to each node in spanning tree

    int path_sum = dijkstraShortestPath(STP_Switch.spanning_tree, 65536, id, root_id);

    int num_bport = 0, num_dport = 0;
    for (int i = 0; i < 1000; i++)
    {
        if (STP_Switch.cost[id][i] && STP_Switch.port[id][i] == 0)
            ++num_bport;
        else if (STP_Switch.cost[id][i] && STP_Switch.port[id][i] == 1)
            ++num_dport;
    }

    ofs << id << "\n";
    ofs << priority << "\n";
    ofs << root_id << "\n";
    ofs << root_priority << "\n";
    ofs << path_sum << "\n";
    ofs << num_bport << "\n";
    ofs << num_dport << "\n";

    ifs.close();
    ofs.close();

    return 0;
}
