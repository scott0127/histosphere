// ========== 新增：歷史事件相關 ==========

/**
 * 歷史事件 - 完整的歷史事件資訊
 */
export interface HistoricalEvent {
  /** 事件唯一識別碼 */
  id: string;
  /** 事件名稱 */
  name: string;
  /** 事件簡述 (選填) */
  description?: string;
  /** 事件發生的世紀 (如 15, 18, 20) */
  century: number;
  /** 主要地理位置 (如 "歐洲", "美洲大陸") */
  geographic_location: string;
  /** 緯度 */
  latitude?: number;
  /** 經度 */
  longitude?: number;
  /** 詳細時間範圍 (如 "1492-1504"，選填) */
  time_period?: string;
  /** 完整歷史背景 */
  context: string;
  /** 資料來源列表 */
  sources?: { title: string; url?: string }[];
  /** 背景圖片 URL */
  background_url?: string;
  /** 建立時間 */
  created_at: string;
  /** 事件類型 */
  type?: 'historical' | 'legend' | 'invalid';
}

/**
 * 歷史人物 - 基於真實歷史的 Persona
 */
export interface Persona {
  /** 人物唯一識別碼 */
  id: string;
  /** 所屬事件 ID */
  event_id: string;
  /** 人物真實全名 */
  name: string;
  /** 真實歷史角色 */
  role: string;
  /** 基於史實的傳記 */
  biography: string;
  /** 真實專長領域 */
  expertise_areas: string[];
  /** 頭像圖片連結 */
  avatar_url?: string;
  /** 建立時間 */
  created_at: string;
}

/**
 * 對話會話 - 一次完整的對話記錄
 */
export interface Conversation {
  /** 對話唯一識別碼 */
  id: string;
  /** 所屬事件 ID */
  event_id: string;
  /** 建立時間 */
  created_at: string;
  /** 更新時間 */
  updated_at: string;
}

// ========== 原有介面調整 ==========

/**
 * 標註資訊 - 用於解釋對話中的專有名詞
 */
export interface Annotation {
  /** 關鍵詞 (原 term) */
  text: string;
  /** 名詞解釋 */
  explanation: string;
}

/**
 * RAG 來源 - 知識檢索的參考來源
 */
export interface RagSource {
  /** 來源 (如 "wikipedia_zh") */
  source: string;
  /** 區塊標題 */
  section_title: string;
  /** 摘要內容 */
  content: string;
}

/**
 * 聊天訊息 - 對話系統中的單一訊息
 */
export interface ChatMessage {
  /** 訊息角色：使用者或 AI 模型 */
  role: 'user' | 'model';
  /** 訊息內容 */
  content: string;
  /** 發送者類型：使用者、歷史人物或導師 (選填) */
  agent?: 'user' | 'persona' | 'tutor';
  /** 哪位人物回應 (新增，選填) */
  persona_id?: string;
  /** 人物名稱，用於前端顯示 (新增，選填) */
  persona_name?: string;
  /** 訊息中的標註列表 (選填) */
  annotations?: Annotation[];
  /** RAG 來源列表 (選填) */
  rag_sources?: RagSource[];
}

/**
 * 資料來源 - 知識的參考來源
 */
export interface Source {
  /** 網路資源 */
  web?: {
    /** 來源網址 */
    uri: string;
    /** 來源標題 */
    title: string;
  };
}


/**
 * 歷史記錄項目 - 儲存完整的對話記錄
 */
export interface HistoryItem {
  /** 記錄唯一識別碼 */
  id: string;
  /** 對話的歷史人物名稱 */
  persona: string;
  /** 人物背景資訊 */
  context: string;
  /** 完整的聊天歷史 */
  chatHistory: ChatMessage[];
  /** 參考資料來源 */
  sources: Source[];
  /** 建立時間戳記 */
  createdAt: number;
}

// ========== 新增：API 請求/回應型別 ==========

/**
 * 初始化事件請求
 */
export interface InitializeEventRequest {
  /** 歷史事件名稱 */
  event_name: string;
}

/**
 * 初始化事件回應
 */
export interface InitializeEventResponse {
  /** 事件 ID */
  event_id: string;
  /** 對話 ID */
  conversation_id: string;
  /** 事件資訊 */
  event: HistoricalEvent;
  /** 參與的歷史人物 */
  personas: Persona[];
  /** 歡迎訊息 */
  greeting: string;
}

/**
 * 聊天請求
 */
export interface ChatRequest {
  /** 對話 ID */
  conversation_id: string;
  /** 用戶訊息 */
  user_message: string;
  /** 對話歷史 */
  history: ChatMessage[];
}

/**
 * 關聯事件 - 對話中提到的其他歷史事件
 */
export interface RelatedEvent {
  /** 事件名稱 */
  event_name: string;
  /** 事件年份 (可能為 null) */
  event_year: number | null;
  /** 事件 ID (如果資料庫有) */
  event_id?: string;
  /** 關聯原因 */
  relevance_reason: string;
  /** 是否可探索 (資料庫是否有此事件) */
  is_explorable: boolean;
}

/**
 * 聊天回應
 */
export interface ChatResponse {
  /** AI 回應文字 */
  response: string;
  /** 標註列表 */
  annotations: Annotation[];
  /** 選定的回應人物 */
  selected_persona: Persona;
  /** 關聯事件列表 */
  related_events?: RelatedEvent[];
  /** RAG 來源列表 */
  rag_sources?: RagSource[];
}

/**
 * 對話列表項目 - 用於顯示對話列表
 */
export interface ConversationListItem {
  /** 對話 ID */
  id: string;
  /** 事件名稱 */
  event_name: string;
  /** 建立時間 */
  created_at: string;
  /** 最後一則訊息 (選填) */
  last_message?: string;
}
