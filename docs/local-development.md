# Local Development And Supabase Ports

最後更新：2026-09-28（內網預設連線、自動列出網址與同源登入）。

## 標準啟動

```powershell
pnpm dev:full
```

此命令會：

1. 使用 repository 內固定版本的 Supabase CLI。
2. 保留 Supabase 官方 local development port 配置。
3. 檢查 Docker daemon 與既有 Supabase stack。
4. 釋放本專案前後端使用的 `3000`、`8000` port。
5. 清理可安全重建的 dev log，再啟動 backend 與 Nuxt frontend。
6. 等待 Supabase、backend 與 frontend readiness，最後輸出實際啟動耗時。
7. 列出本機網址與目前有效網路介面的管理員網址。

`-KillExisting` 已包含在 `dev:full`，不需要先手動找 PID。

## 手機／平板的內網連線

`pnpm dev:full` 預設讓 Nuxt 監聽 `0.0.0.0:3000`，接受目前及之後連上的網路介面；FastAPI 維持 `127.0.0.1:8000`，由 Nuxt 代理 API 與 SSE。單獨執行 `pnpm dev` 也預設開啟內網監聽，但不會啟動後端或 Docker。`0.0.0.0` 是監聽設定，不是瀏覽器應開啟的網址。

受測者可在主機開啟 `http://127.0.0.1:3000`；研究者使用啟動輸出中的 `http://<主機內網 IP>:3000/admin`。IP 由目前有預設閘道且已連線的 IPv4 網路介面取得，不寫死 Wi-Fi 位址。

本次測試使用前端 `3002`、後端 `8002`；若要沿用這組埠，執行：

```powershell
pnpm dev:full -FrontendPort 3002 -BackendPort 8002
```

換 Wi-Fi 後可以重新查詢：

```powershell
pnpm dev:urls -FrontendPort 3002
```

此命令每次重新讀取網路介面，**不會啟動服務，也不檢查服務是否正在運行**。省略 `-FrontendPort` 時顯示預設 `3000`，不會自動尋找已啟動的埠。使用預設的 `0.0.0.0` 監聽時，換網路不需要重設主機 IP；但舊網址不會自動重新導向，手機／平板仍須開啟新的 IP 網址。

如需限定只有本機可使用：

```powershell
pnpm dev:full -HostAddress 127.0.0.1
```

### 登入與網路限制

本地 `VITE_SUPABASE_URL` 保持 Supabase CLI 提供的 loopback 位址。瀏覽器登入經由同源 `/supabase-auth/auth/v1/**`，再由 Nuxt 轉送至本地 Supabase Auth，因此不必隨 Wi-Fi 更換 `VITE_SUPABASE_URL`，手機／平板也不需要直接連到 `54321`。這個代理僅涵蓋 Auth 路徑；雲端 Supabase URL 維持原有直連方式。

目前已在主機使用內網 IP 驗證網站與 `TEST_ACCOUNT` 真實登入。其他裝置只需連到網站埠；Windows 防火牆是否放行該埠、實驗室 Wi-Fi 是否有裝置隔離，仍需在實際裝置與場地驗證。啟動腳本不會自行修改防火牆。

## 保留的官方 Ports

| Service | Port |
| --- | ---: |
| Supabase shadow database | `54320` |
| Supabase API / Kong | `54321` |
| Supabase Postgres | `54322` |
| Supabase Studio | `54323` |
| Local SMTP UI（已配置，`dev:full` 為加速而不啟動） | `54324` |
| Supabase pooler（目前停用） | `54329` |
| Nuxt frontend | `3000` |
| FastAPI backend | `8000` |

不要為了避開 Windows port reservation 任意改動 `supabase/config.toml`。正式處理方式是讓 Windows 不再把 `54320-54329` 動態分配給 WinNAT，再讓 Supabase 使用原本 port。

## Windows Port Release

若 `pnpm dev:full` 顯示 Supabase container healthy，但 `54321` 無法 bind 或被 Windows excluded range 保留，執行：

```powershell
pnpm dev:repair:supabase-ports
```

腳本會要求 Administrator 權限，短暫停止 Docker Desktop 與 WinNAT，將 `54320-54329` 建立為 administrator-managed reservation，再重新啟動服務。這可避免 WinNAT 未來再次把該範圍納入動態 excluded range；它不會改掉 Supabase 官方 port。

這是一次性的作業系統修復。一般啟動不應每次停止 WinNAT，也不應每次重建 reservation。

檢查 excluded range：

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

若 `54320-54329` 出現在帶 `*` 的 administrator-managed range 中，`dev.ps1` 會視為可用；只有未受管理的動態 excluded range 才會阻止啟動。

## 啟動速度策略

- Supabase CLI 固定為 `2.109.1`，避免每次透過 `npx -y supabase@latest` 下載或遇到版本漂移。
- `supabase:start` 不啟動目前未使用的 `edge-runtime`、`imgproxy`、`logflare`、`mailpit`、`realtime`、`vector`。
- 已健康運作的 Supabase stack 直接重用，不重啟資料庫。
- Health check 讀取實際 `supabase status` 與 TCP readiness，不只依賴 container 名稱或單一狀態文字。
- Backend 與 frontend port 只處理實際 listener；釋放後等待 socket 完全關閉再重啟。
- Nuxt 使用 repository 內預設 `.nuxt` build directory，不把生成內容放到 Windows Temp。

## 停止與資料安全

只停止 frontend/backend：

```powershell
pnpm dev:cleanup
```

同時停止 local Supabase：

```powershell
pnpm dev:cleanup:supabase
```

停止 Supabase 時保留 CLI database backup。不要用 `supabase db reset` 當成一般啟動修復手段，因為它會重建 local database；本專案的日常 port/程序清理不應刪除研究資料。

`.dev-logs/llm-usage.jsonl` 是 Admin Token／費用統計的持久帳本，不是用完可刪的暫存。啟動腳本清空的是指定的前後端程序 log，不是整個 `.dev-logs`。也不要隨手刪除 LLM 審查／失敗 audit；換部署主機時需保留所需紀錄。統計範圍見 [研究資料與用量](research-data-export.md)。

## 品質檢查

程式碼層完整檢查：

```powershell
pnpm test:quality:code
```

會依序執行前端單元測試、後端 pytest 與 Nuxt build。

前後端及 Supabase 已由 `pnpm dev:full` 啟動後，可再執行：

```powershell
pnpm test:supabase:schema
pnpm test:runtime:smoke
```

- `test:supabase:schema` 只讀取 PostgREST OpenAPI，檢查 14 個 public tables 與關鍵欄位，不新增、修改或刪除資料。
- `test:runtime:smoke` 檢查首頁、Admin、FastAPI health 與 OpenAPI 是否可連線。
- `pnpm test:quality` 會將以上檢查全部串起來，因此需要服務已經啟動。

## 故障判斷

| 現象 | 處理 |
| --- | --- |
| `3000` 或 `8000` 已被使用 | 直接再跑 `pnpm dev:full`，命令會終止 listener 並等待 port 釋放。 |
| `.dev-logs/*.log` 被鎖定 | `dev:full` 會先終止舊 process tree，再重試清空 log。 |
| Supabase healthy 但 `54321` 無法連線 | 執行一次 `pnpm dev:repair:supabase-ports`。 |
| Docker CLI 尚未 ready | 等 Docker Desktop daemon ready，再執行 `pnpm dev:full`。 |
| Nuxt 出現 `@nuxtjs/tailwindcss/config-ctx` Temp path | 確認 Nuxt 未設定 Windows Temp buildDir，清除本地 `.nuxt` 後重啟。 |
