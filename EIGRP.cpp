#include <iostream>
#include <cstdlib>
#include <String>
#include <fstream>
#include <vector>
using namespace std;

class EIGRP_Switch *s;
class EIGRP_Switch
{
public:
    int id;
    int n;                         // 有多少條link
    int routing[65536][2] = {{0}}; // 第一格代表到index switch的路徑的next-hop(第一步), 第二格代表該路徑的cost; 動態分配則使用unordered_map

    EIGRP_Switch() = default;
    EIGRP_Switch(int id_, int n_)
    {
        id = id_;
        n = n_;
    };
};

int main()
{
    ifstream ifs;
    ofstream ofs;

    string name;
    cin >> name;
    name += ".txt";

    ifs.open(name);
    ofs.open("output.txt");

    int n, id, p, q;
    ifs >> id >> n;

    EIGRP_Switch s;

    s.routing[id][0] = id; // next hop
    s.routing[id][1] = 0;  // cost

    for (int i = 0; i < n; i++) // 輸入n個link的cost pair
    {
        ifs >> p >> q;
        s.routing[p][0] = p;
        s.routing[p][1] = q;
    }

    int m, EIGRP_id, k, r, c;            // 會收到m個EIGRP ms, 送出的switch的id, k個link的cost pair
    int update_neighbor, update_starter; // boolean value 表示是否要更新

    ofs << "Hello"
        << "\n";
    ifs >> m;
    for (int i = 0; i < m; i++)
    {
        int compare[65536] = {0}; // 用來比較的switch
        ifs >> EIGRP_id >> k;
        for (int l = 0; l < k; l++)
        {
            ifs >> r >> c;
            compare[r] = c;
        }

        update_neighbor = 0;
        update_starter = 0;

        for (int j = 0; j < 65536; j++) // 檢查全部交換器
        {
            if (s.routing[j][0] == 0 && compare[j] > 0) // starter到j交換器沒有path, 但EIGRP_id交換器有
            {
                s.routing[j][0] = EIGRP_id;                            // 設定next hop
                s.routing[j][1] = s.routing[EIGRP_id][1] + compare[j]; // 設定starter到j交換器的距離
                update_starter = 1;                                    // starter需要更新
            }

            else if (s.routing[j][0] > 0 && compare[j] == 0) // starter上有到j交換器的path, 但EIGRP_id交換器沒有
            {
                update_neighbor = 1; // neighbor需要更新
            }

            else if (s.routing[j][0] > 0 && compare[j] > 0) // 兩個都有到j交換器的路徑, 找出最小距離
            {
                if (s.routing[j][1] > compare[id] + compare[j]) // neighbor到j比較近
                {
                    s.routing[j][1] = compare[id] + compare[j];
                    s.routing[j][0] = EIGRP_id;
                    update_starter = 1; // 更新starter
                }
                else if (s.routing[j][1] < compare[id] + compare[j]) // starter到j比較近
                    update_neighbor = 1;                             // 更新neighbor
            }
        }

        if (update_neighbor && update_starter)
            ofs << "Update Hello"
                << "\n";
        else if (update_neighbor)
            ofs << "Update"
                << "\n";
        else if (update_starter)
            ofs << "Hello"
                << "\n";
    }

    ofs << "Switch ID:" << id << "\n";
    ofs << "Path:"
        << "\n";

    for (int i = 0; i < 65536; i++)
    {
        if (s.routing[i][0]) // starter到i交換器有path的話
            ofs << "ID:" << i << ", "
                << "next hop:" << s.routing[i][0] << ", "
                << "cost:" << s.routing[i][1] << "\n";
    }

    ifs.close();
    ofs.close();

    return 0;
}
