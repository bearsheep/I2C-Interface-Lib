# 如何把 I2C-Interface-Lib 當作 git submodule 使用

這份教學記錄了把這個共用 repo 接進一個專案（例如 Python-CMIS）的完整手動步驟，
之後要接進 RD6012P、SCP_Project_Spica5 等其他專案時可以照抄。

Remote: `git@github.com:bearsheep/I2C-Interface-Lib.git`

---

## 1. 把共用 repo 加為 submodule

在目標專案（例如 Python-CMIS）的根目錄下執行：

```bash
git submodule add git@github.com:bearsheep/I2C-Interface-Lib.git I2C_Interface
```

- `I2C_Interface` 是這個 submodule 在你專案裡的資料夾名稱，可以自己取，
  之後 import 時就是 `from I2C_Interface.i2c_iss import I2C_ISS` 這樣用。
- 執行後會自動：
  - clone 整個 I2C-Interface-Lib 到 `I2C_Interface/`
  - 在專案根目錄產生 `.gitmodules`（記錄 submodule 路徑與 url）
  - `git add` 好 `.gitmodules` 跟 `I2C_Interface`（這是一個特殊的 commit 指標，不是真的資料夾內容）

接著照平常方式 commit：
```bash
git commit -m "Add I2C-Interface-Lib as submodule"
```

---

## 2. Clone 一個已經有 submodule 的專案

如果專案已經設定好 submodule，直接 `git clone` 不會自動抓 submodule 內容，
`I2C_Interface/` 資料夾會是空的。要用下面其中一種方式：

**方法 A：clone 的時候順便抓**
```bash
git clone --recurse-submodules git@github.com:bearsheep/Python-CMIS.git
```

**方法 B：clone 完之後補抓**
```bash
git clone git@github.com:bearsheep/Python-CMIS.git
cd Python-CMIS
git submodule update --init --recursive
```

---

## 3. 共用 repo 有更新時，如何同步到你的專案

I2C-Interface-Lib 本身有新 commit 之後（例如加了新的裝置 wrapper），
你的專案裡的 submodule **不會自動更新**，要手動拉：

```bash
cd I2C_Interface
git checkout main      # submodule 預設會停在 detached HEAD，先切回 main
git pull origin main
cd ..
git add I2C_Interface  # 記錄新的 submodule commit 指標
git commit -m "Bump I2C_Interface submodule"
```

或者一行版本（等同上面前三行）：
```bash
git submodule update --remote I2C_Interface
```

**重點**：submodule 的更新分兩層 —
1. `I2C_Interface/` 資料夾裡的內容要 pull 到新版本
2. 你的專案（外層 repo）要 commit 這個新的「submodule 指標」

兩層都要做，只做第 1 步的話，`git status` 會一直顯示 `I2C_Interface` 有未 commit 的變更。

---

## 4. 要修改共用 repo 的程式碼時

直接在 submodule 資料夾裡改，它就是一個完整的 git repo：

```bash
cd I2C_Interface
# 編輯檔案...
git add -A
git commit -m "Fix xxx"
git push origin main
cd ..
git add I2C_Interface   # 外層專案也要記錄新指標，否則別人 clone 你的專案時還是舊版本
git commit -m "Bump I2C_Interface submodule"
```

---

## 5. 常見狀況

- **`fatal: not a git repository` 在 I2C_Interface 資料夾裡**：忘記 `git submodule update --init`。
- **`git status` 一直顯示 submodule 有變更，但你什麼都沒改**：通常是 submodule 停在
  detached HEAD、或指到了跟外層記錄不同的 commit。用 `git submodule update` 校正回外層記錄的版本，
  或如果你是故意要用新版本，照第 3 節流程 bump 指標。
- **多個專案同時在改 submodule**：每個專案各自的「submodule 指標」是獨立的，
  A 專案 bump 到新版本不會影響 B 專案，B 專案要自己執行第 3 節的步驟才會跟進。
