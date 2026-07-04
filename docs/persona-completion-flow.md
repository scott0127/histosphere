

Learner message
  ↓
Load event / persona / source / history
  ↓
General Prompt
  ├─ historical accuracy
  ├─ language policy
  ├─ uncertainty policy
  └─ no fabrication
  ↓
independent_1 Prompt
  └─ persona first-person identity
  ↓
independent_2 Prompt
  └─ direct or EBL interaction style
  ↓
Persona Context
  ├─ identity
  ├─ social position
  ├─ time boundary
  ├─ knowledge scope
  └─ forbidden knowledge
  ↓
LLM call
  ↓
Persona completion
  ↓
store message + prompt metadata

## 每個模組的責任

### General Prompt

`General Prompt` 是所有 2x2 condition 都會使用的共用規則。它不負責決定是否 role-play，也不負責決定是否使用 EBL，而是提供最低限度的研究與史實安全邊界。

它應負責：

- 要求輸出使用繁體中文。
- 要求史實準確優先。
- 要求明確標示不確定性。
- 禁止捏造史料、引文、私人心理、親身經歷或不存在的事件。
- 禁止將複雜歷史事件簡化成單一原因或單一立場。
- 禁止時代錯置與地理、文化、人物知識錯置。

### independent_1 Prompt: Response Identity

`independent_1 Prompt` 決定回覆者的身分模式。它是 2x2 中 role-play 軸的 prompt module。

在 `generic assistant mode` 中，模型應：

- 不扮演歷史人物。
- 不使用歷史人物第一人稱。
- 以一般 AI assistant 或 tutor 的身份回覆。
- 可以解釋歷史脈絡，但不能假裝自己身處歷史事件中。

在 `historical persona mode` 中，模型應：

- 扮演指定的 primary historical persona。
- 使用第一人稱回應。
- 用當代清楚繁體中文表達，但保留該人物的社會位置、價值觀、限制與視角。
- 只使用該人物在其時代與位置中可合理知道的資訊。
- 遇到超出人物資訊邊界的問題時，以角色內方式說明限制，而不是切換成全知旁白。

### independent_2 Prompt: Interaction Mode

`independent_2 Prompt` 決定互動方式。它是 2x2 中 EBL / non-EBL 軸的 prompt module。

在 `direct interaction` 中，模型可以：

- 直接回答學習者問題。
- 給出清楚、簡潔的歷史脈絡。
- 不刻意使用蘇格拉底式追問。
- 不刻意把錯誤當成 productive error 來引導。

但 direct interaction 仍不能降低史實要求。它只是互動方式直接，不代表可以忽略歷史準確性。

在 `EBL + historical thinking interaction` 中，模型應：

- 優先誘發學習者自己修正理解。
- 使用 historical thinking skill 引導互動。
- 在學習者尚未找到正確方向前，避免直接揭露完整結論。
- 透過問題、比較、證據提示與脈絡提示促進思考。

可使用的 historical thinking skill 包含但不限於：

- causation
- contextualization
- change and continuity
- evidence
- perspective-taking
- historical significance

### Persona Context

`Persona Context` 是動態資料，不是固定規則。它提供指定歷史人物的內容邊界。

它應包含：

- 人物名稱、英文名、身份與簡傳。
- 人物在事件中的社會位置與政治、文化、制度位置。
- 人物可合理知道的時間範圍。
- 人物可合理知道的地理與文化範圍。
- 人物可討論的知識範圍。
- 人物不可知道或不可聲稱知道的內容。
- 人物語氣與立場。
- 人物被選為 primary persona 的理由。

Persona Context 不應讓模型變成全知歷史旁白。它的作用是縮小角色可說話的範圍，而不是讓角色取得更多不屬於他的知識。

### Runtime / LLM Call Policy

`Runtime / LLM Call Policy` 決定本次 completion 的 API 呼叫行為。

Persona 相關呼叫理想上應拆成三類：

- `persona_generation`：生成或修正 persona profile，應使用較低 temperature，重點是穩定、保守、可驗證。
- `persona_greeting`：產生對話開場，應使用中低 temperature，重點是自然但不新增角色設定。
- `persona_chat`：正式對話回覆，可保留適度彈性，但仍需受 persona boundary 與 general prompt 約束。

此層可控制：

- model
- fallback model
- temperature
- max tokens
- timeout
- provider-specific options

## Completion 結束後應保存的資料

Persona completion 產生後，後端不應只保存自然語言回覆。為了研究可追蹤性，至少應考慮保存以下資訊：

- 實際顯示給 learner 的 message。
- `speaker_type` 與 `speaker_name`。
- 使用的 persona id。
- persona profile version 或 profile hash。
- prompt module version 或 prompt hash。
- LLM provider 與 model。
- condition key。
- completion metadata。

這些資料可以讓後續研究者確認：同一個 condition 是否使用一致的 prompt 組合、persona 是否被修改過、不同模型或 fallback 是否影響回覆。

## 後續待討論

這份文件先建立 persona completion 的抽象流程。後續仍需要繼續討論並形成更正式的規格：

- `persona_profile_v1` 的固定 JSON schema。
- `General Prompt` 的正式英文 prompt 文字與中文註解。
- `independent_1 Prompt` 的 generic / persona 兩種正式 prompt。
- `independent_2 Prompt` 的 direct / EBL historical thinking 兩種正式 prompt。
- persona 越界回應規則。
- prompt hash 與 persona profile version 如何保存到資料庫。
- admin UI 如何從 raw JSON 改成欄位式 persona editor。
- prompt preview 如何呈現每個 module，而不是只顯示最終大 prompt。
