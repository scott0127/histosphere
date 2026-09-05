-- 由 canonical JSON 的霧社題組產生；只新增版本，不改既有活動。
-- source_sha256: d064d408a0d6d5650fb40ae1de44ff7f87c41f0a174cee1315f74518a4077f9c
-- 保留其他三個事件、舊題組、作答及聊天；同版本重跑不重複建立。

DO $do$
DECLARE
  v_task JSONB;
  v_event_id UUID;
  v_version TEXT;
BEGIN
  FOR v_task IN
    SELECT value
    FROM jsonb_array_elements(
      ($json${
  "tasks": [
    {
      "event_name": "霧社事件",
      "title": "霧社事件：照片裡與照片外",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "校刊準備製作霧社事件專頁。編輯桌上放著一本中文史料集，以及一張附有日文圖說的舊照片。有人想寫部隊的行動與物資安排，有人想談照片如何呈現事件，也有人想了解各部落居民在衝突中的生活。\n\n版面有限，編輯必須先決定：手上的材料適合寫哪些內容，哪些部分還得繼續找資料？請根據兩份材料與照片，回答下面三題。\n\nQ01｜只憑本文介紹的兩組資料，哪一項研究最需要補充其他人的紀錄或訪談？\n{{blank:q01}}\n\nQ02｜有人說：「軍事紀錄的中文譯本在 2010 年出版，因此它不能包含日治時期軍方留下的紀錄。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果要先查找軍方如何安排物資供應，而不只是它如何在影像中呈現行動，應優先閱讀「軍事紀錄」或「攝影資料」？請填其中一項，並說明選擇的依據與限制。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "wushe_military_records",
            "title": "軍事紀錄",
            "caption": "《霧社事件日文史料翻譯》，國立臺灣歷史博物館，2010 年出版。",
            "text": "1930 年 10 月 27 日，莫那魯道與霧社地區六個部落的賽德克族人發動抗日行動，日本軍警隨後進行鎮壓。除了戰鬥，部隊的調動與物資供應也留下了文字紀錄。\n\n《霧社事件日文史料翻譯》收錄的文件包括《霧社事件陣中日誌》、《霧社事件關係陸軍大臣官房書類綴》，以及《昭和五年臺灣霧社事件給養史》。其中「昭和五年」是 1930 年，「給養」指部隊所需的糧食、物資等供應。這些日文文件涉及日本軍方的軍事行動與後勤補給。\n\n這本中文出版品於 2010 年由國立臺灣歷史博物館出版，除了上述文件的譯文，也收錄學者春山明哲對事件的解說。編輯先從書名與收錄文件名稱建立索引，準備進一步查找部隊行動、物資供應等紀錄。",
            "source_url": "https://www.nmth.gov.tw/jp/News_Publish_Content.aspx?n=4414&s=139464",
            "attribution": "國立臺灣歷史博物館《霧社事件日文史料翻譯》出版介紹；事件背景另核對臺史博典藏〈霧社事件始末〉。本文不是軍方日誌的逐字節錄。"
          },
          {
            "id": "wushe_photographic_records",
            "title": "攝影資料",
            "caption": "霧社本部前整理行李，約 1930 年。收錄於佐藤政藏編《第一第二霧社事件誌》（1931 年）；攝影者不詳。",
            "image_url": "/images/materials/wushe-headquarters-1930.jpg",
            "text": "照片中，幾名穿制服的人站立或俯身在一批行李旁，地上可見箱子與包裹，後方是建築物。這張照片後來收入《第一第二霧社事件誌》，該書由佐藤政藏編輯，1931 年由實業時代社中部支社出版部出版。\n\n原書圖說：\n「霧社本部前にて第三大隊の滿期除隊兵歸隊の為め荷物の整理中」\n圖說大意：在霧社本部前，為第三大隊服役期滿的士兵歸隊整理行李。\n\n編輯打算把這張照片放在專頁中央，保留圖說，旁邊再配上一段文字。他面前已有部隊活動的影像，也有可以繼續查閱的軍事文件；接下來要決定的，是這一頁究竟能向讀者說明什麼。",
            "source_url": "https://dl.lib.ntu.edu.tw/s/photo/item/103879",
            "attribution": "臺大圖書館臺灣舊照片資料庫，同名照片，出處《第一第二霧社事件誌》（1931）。圖片檔取自 Wikimedia Commons 公有領域版本，未裁切、生成或修補；日文圖說據臺大書目核對，中文為圖說大意，不推定拍攝者或精確拍攝日期。"
          }
        ],
        "questions": [
          {
            "id": "q01",
            "type": "multiple_choice",
            "required": true,
            "options": [
              {
                "id": "a",
                "label": "日文軍事文件記錄了哪些補給安排。",
                "value": "A"
              },
              {
                "id": "b",
                "label": "被選入照片的軍事活動有哪些類型。",
                "value": "B"
              },
              {
                "id": "c",
                "label": "不同部落居民如何理解衝突及生活變動。",
                "value": "C"
              },
              {
                "id": "d",
                "label": "照片圖說如何介紹其呈現的軍事行動。",
                "value": "D"
              }
            ],
            "correct_answer": "C",
            "source_text": "兩組材料主要涉及軍方行動、補給與軍事影像；要理解不同居民的主觀經驗，仍需其他相關紀錄或訪談，不能以軍方材料替代所有人的聲音。",
            "accepted_evidence_ids": [
              "wushe_military_records",
              "wushe_photographic_records"
            ],
            "reasoning_criteria": "通過：指出現有材料以軍事行動或成果為中心，缺少能直接支持不同居民如何理解及經歷事件的敘述，因此需補充其他觀點的資料。不必列出特定訪談人名，不把後來口述預設為必定正確。不通過：只說資料少而未連結研究問題，或因材料來自軍方就認定所有內容都是假的。"
          },
          {
            "id": "q02",
            "type": "true_false",
            "required": true,
            "correct_answer": false,
            "source_text": "2010 年是中文譯本出版時間，原始軍事文件來自較早的事件相關紀錄；兩者不是同一個時間概念。",
            "accepted_evidence_ids": [
              "wushe_military_records"
            ],
            "reasoning_criteria": "通過：區分原始文件形成的時間與後來整理翻譯出版的時間，說明晚出版不代表原文件也在同年首次撰寫。可舉陣中日誌或給養紀錄支持，但不強制列出文件名。不通過：只說博物館出版所以可信，或反過來認為譯本每一句都一定是 1930 年當事人的原話。"
          },
          {
            "id": "q03",
            "type": "cloze",
            "required": true,
            "correct_answer": [
              "軍事紀錄",
              "軍事記錄",
              "《霧社事件日文史料翻譯》",
              "霧社事件日文史料翻譯",
              "給養紀錄",
              "給養記錄"
            ],
            "source_text": "軍事紀錄包含給養及後勤補給，較直接對應物資安排；攝影資料主要呈現被選出的軍事場景，不能單靠影像確定完整補給安排。",
            "accepted_evidence_ids": [
              "wushe_military_records",
              "wushe_photographic_records"
            ],
            "reasoning_criteria": "通過：指出給養或後勤紀錄直接對應物資供應，並指出至少一項限制，例如紀錄偏向軍方、安排不等於每次實際落實，或照片不能提供完整補給細節。無須使用史料批判等術語。不通過：只說文字比照片可靠、所有軍方文件都絕對真實，或未說明其與物資問題的關係。"
          }
        ],
        "all_correct_fallback": {
          "id": "wushe_records_cover_everyone",
          "evidence_ids": [
            "wushe_military_records",
            "wushe_photographic_records"
          ],
          "incorrect_claim": "只要把軍方紀錄與軍事照片合在一起，就能完整還原所有部落居民當時的想法與經驗。",
          "correct_interpretation": "兩種資料形式不同，但都可能集中在軍事面向；理解不同居民經驗仍需相關的其他紀錄或訪談，並核對各資料的形成背景與限制。",
          "source_text": "軍事文件的收錄範圍，以及霧社本部前整理行李的照片與圖說；這些材料沒有收錄不同居民對衝突及生活變動的完整敘述。"
        },
        "authoring": {
          "method": "researcher_curated_with_ai_assistance",
          "version": "wushe-reading-20260905-v2",
          "review_status": "awaiting_researcher_acceptance",
          "sources": [
            "https://www.nmth.gov.tw/jp/News_Publish_Content.aspx?n=4414&s=139464",
            "https://collections.nmth.gov.tw/CollectionContent.aspx?a=132&rno=2017.025.0196.0039",
            "https://dl.lib.ntu.edu.tw/s/photo/item/103879",
            "https://commons.wikimedia.org/wiki/File:In_front_of_Musha_Headquarters,_sorting_out_luggage_for_the_3rd_Battalion%27s_full-term_discharge_corps_circa_1930.jpg"
          ],
          "image_provenance": {
            "path": "/images/materials/wushe-headquarters-1930.jpg",
            "sha256": "4e625113bc0b0db638121741f0f85937df4278c8d6951f227afa378186f235fb",
            "license": "Public domain (Commons: PD-Japan-oldphoto; PD-1996)",
            "checked_at": "2026-09-05"
          },
          "note": "本題組以真實文件名稱、出版資料及歷史照片編製；校刊編輯情境為虛構教學情境，不冒充歷史事件。軍事紀錄段落是出版介紹的改寫，未宣稱讀取或引用日誌內頁；日文圖說為原文，其餘敘述不是當事人的逐字發言。三題答案與通過標準沿用前版，尚待研究者驗收，不宣稱難度等值。出版與典藏年代不是人物的親身記憶，Persona 不得把 2010 年出版品或 1931 年編輯行為說成生前讀物或經歷。"
        }
      }
    }
  ]
}$json$::jsonb)->'tasks'
    )
  LOOP
    SELECT id
    INTO v_event_id
    FROM events
    WHERE canonical_name = v_task->>'event_name'
    LIMIT 1;

    -- 全新環境先建事件，config.toml 再依序重播題組資料。
    IF v_event_id IS NULL THEN
      CONTINUE;
    END IF;

    v_version := v_task #>> '{evaluation_payload,authoring,version}';

    IF NOT EXISTS (
      SELECT 1
      FROM event_tasks
      WHERE event_id = v_event_id
        AND evaluation_payload #>> '{authoring,version}' = v_version
    ) THEN
      INSERT INTO event_tasks (
        event_id,
        title,
        story_text,
        error_elicitation_task_full_text,
        evaluation_payload,
        revision_state
      )
      VALUES (
        v_event_id,
        v_task->>'title',
        COALESCE(v_task->>'story_text', ''),
        v_task->>'error_elicitation_task_full_text',
        v_task->'evaluation_payload',
        COALESCE(v_task->>'revision_state', 'teacher_modified')
      );
    END IF;
  END LOOP;
END;
$do$;
