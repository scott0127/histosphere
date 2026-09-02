-- Formal sample materials for local Supabase.
-- Runtime API code does not read this file. It only reads Supabase tables
-- through the repository layer. IDs are intentionally omitted so Postgres
-- generates normal UUIDs.

DO $$
DECLARE
  v_event_id uuid;
  v_persona_id uuid;
  v_task_id uuid;
BEGIN
  INSERT INTO events (
    canonical_name,
    description,
    century,
    start_year,
    end_year,
    context,
    source_summary
  )
  VALUES (
    '法國大革命',
    '法國大革命是 1789 至 1799 年間法國政治、社會與制度秩序的劇烈轉型。它挑戰舊制度的特權結構，推動《人權和公民權宣言》與近代公民概念，同時也伴隨戰爭、派系衝突與政治暴力。理解此事件時，不能只把它看成人民推翻國王的單線故事，而要同時考慮財政危機、特權制度、代表權爭議、革命戰爭與共和政治實驗所造成的延續與變遷。',
    18,
    1789,
    1799,
    '正式實驗材料聚焦三個判斷點：舊制度危機如何累積、第三等級如何挑戰代表權安排、革命理想為何沒有直接消除政治衝突。',
    '{"provider":"supabase_seed","language":"zh-TW","research_material_version":"formal-simulation-v1","historical_thinking_dimensions":["historical significance","evidence","continuity and change","cause and consequence","historical perspectives","ethical dimension"]}'::jsonb
  )
  ON CONFLICT (canonical_name) DO UPDATE SET
    description = EXCLUDED.description,
    century = EXCLUDED.century,
    start_year = EXCLUDED.start_year,
    end_year = EXCLUDED.end_year,
    context = EXCLUDED.context,
    source_summary = EXCLUDED.source_summary,
    updated_at = now()
  RETURNING id INTO v_event_id;

  UPDATE personas
  SET
    english_name = 'Maximilien Robespierre',
    role = '雅各賓派領袖與國民公會代表',
    biography = '法國大革命期間的重要政治人物，主張共和、德行政治與革命防衛。他適合用來討論革命理念、國民公會、恐怖統治、戰爭壓力與政治暴力之間的複雜關係。',
    expertise_areas = ARRAY['法國大革命','雅各賓派','共和政治','恐怖統治'],
    sources = '[]'::jsonb,
    avatar_url = '/images/personas/maximilien-robespierre.jpg',
    prompt_profile = '{"contract_version":"persona_prompt_v2","speaking_style":"嚴肅、論辯性強，重視共和德行與公共利益。","forms_of_address":"公民","social_position":"雅各賓派領袖與國民公會代表","relationship_to_event":"身處革命政府核心，參與共和政治與革命防衛的爭論","event_timepoint":"1793 年國民公會與革命政府面臨內外危機期間","event_timepoint_year":1793,"event_location":"巴黎","event_vantage_point":"國民公會代表與雅各賓派政治領袖的視角","current_stakes":["共和政體的存續","戰爭壓力","革命防衛與政治暴力的界線"],"event_anchor_terms":["國民公會","共和國","雅各賓派"],"knowledge_cutoff_year":1793,"firsthand_experience_allowed":false,"firsthand_experience_scope":[],"temporal_boundary":"以 1793 年當下可知資訊發言，不得知道熱月政變、本人死亡或其後政局。","geographic_boundary":"以巴黎及國民公會政治網絡中可合理接觸的資訊為限。","knowledge_boundary":"只能使用人物在 1793 年依其身份可合理知道的資訊，不預知後世史學評價。","deliberate_error_enabled":false}'::jsonb,
    active = true,
    sort_order = 0,
    revision_state = 'teacher_modified',
    updated_at = now()
  WHERE event_id = v_event_id AND name = '馬克西米連·羅伯斯比爾'
  RETURNING id INTO v_persona_id;

  IF v_persona_id IS NULL THEN
    INSERT INTO personas (
      event_id,
      name,
      english_name,
      role,
      biography,
      expertise_areas,
      sources,
      avatar_url,
      prompt_profile,
      active,
      sort_order,
      revision_state
    )
    VALUES (
      v_event_id,
      '馬克西米連·羅伯斯比爾',
      'Maximilien Robespierre',
      '雅各賓派領袖與國民公會代表',
      '法國大革命期間的重要政治人物，主張共和、德行政治與革命防衛。他適合用來討論革命理念、國民公會、恐怖統治、戰爭壓力與政治暴力之間的複雜關係。',
      ARRAY['法國大革命','雅各賓派','共和政治','恐怖統治'],
      '[]'::jsonb,
      '/images/personas/maximilien-robespierre.jpg',
      '{"contract_version":"persona_prompt_v2","speaking_style":"嚴肅、論辯性強，重視共和德行與公共利益。","forms_of_address":"公民","social_position":"雅各賓派領袖與國民公會代表","relationship_to_event":"身處革命政府核心，參與共和政治與革命防衛的爭論","event_timepoint":"1793 年國民公會與革命政府面臨內外危機期間","event_timepoint_year":1793,"event_location":"巴黎","event_vantage_point":"國民公會代表與雅各賓派政治領袖的視角","current_stakes":["共和政體的存續","戰爭壓力","革命防衛與政治暴力的界線"],"event_anchor_terms":["國民公會","共和國","雅各賓派"],"knowledge_cutoff_year":1793,"firsthand_experience_allowed":false,"firsthand_experience_scope":[],"temporal_boundary":"以 1793 年當下可知資訊發言，不得知道熱月政變、本人死亡或其後政局。","geographic_boundary":"以巴黎及國民公會政治網絡中可合理接觸的資訊為限。","knowledge_boundary":"只能使用人物在 1793 年依其身份可合理知道的資訊，不預知後世史學評價。","deliberate_error_enabled":false}'::jsonb,
      true,
      0,
      'teacher_modified'
    )
    RETURNING id INTO v_persona_id;
  END IF;

  -- Draft material: researcher review is required before formal collection.
  INSERT INTO event_tasks(event_id, title, story_text, error_elicitation_task_full_text, evaluation_payload, revision_state)
  SELECT v_event_id, '法國大革命初期代表權爭議與三級會議', '',
    '閱讀1789年法國大革命初期的資料，逐題填寫答案與判斷理由。

Q01：關於1789年三級會議初期對表決方式的爭議，下列何者正確？{{blank:q01}}

Q02：網球場宣誓的核心目標是制定法國憲法，而不僅是要求國王解決短期財政赤字。請判斷是非。{{blank:q02}}

Q03：1789年6月17日，第三等級與部分教士、貴族代表宣告成立哪個議會？請填寫名稱並說明依據。{{blank:q03}}',
    '{"contract_version": "error_elicitation_v1", "materials": [{"id": "mat_01", "title": "凡爾賽宮博物館：1789年的三級會議與國民議會之整理", "text": "1789年5月，法國在財政與政治危機下召開三級會議，代表包括教士、貴族與第三等級。對表決方式出現爭議：前兩等級要求按等級計票，第三等級要求按人頭計票。6月17日第三等級與部分教士、貴族代表成立國民議會。6月20日代表在網球場宣誓，誓言在制定憲法前不解散。以上依凡爾賽宮博物館說明整理，不是1789年逐字原文。", "source_url": "https://en.chateauversailles.fr/discover/history/key-dates/versailles-heart-french-revolution", "attribution": "凡爾賽宮博物館官方歷史網站摘要（研究者中文編譯摘要）"}], "questions": [{"id": "q01", "type": "multiple_choice", "required": true, "correct_answer": "opt_02", "options": [{"id": "opt_01", "label": "第三等級支持按等級計票，以確保其佔多數的代表名額能發揮影響力。", "value": "opt_01"}, {"id": "opt_02", "label": "前兩等級要求按等級計票，而第三等級則堅持按人頭計票。", "value": "opt_02"}, {"id": "opt_03", "label": "三級會議順利達成共識，全體代表同意不分等級共同投票。", "value": "opt_03"}], "reasoning_criteria": "能根據材料正確區分兩種計票主張，並說明選項如何符合當時代表權爭議。接受其他有依據的合理說明，不要求精確人口比例或特定術語。", "source_text": "對如何投票發生爭議：前兩等級要求按等級計票，第三等級要求按人頭計票。", "accepted_evidence_ids": ["mat_01"]}, {"id": "q02", "type": "true_false", "required": true, "correct_answer": true, "reasoning_criteria": "能把誓言在制定憲法前不解散，連結到建立憲法的政治目標。不能只憑活動名稱或猜測判斷；不必額外列出全部改革背景。", "source_text": "6月20日網球場宣誓與建立憲法有關。", "accepted_evidence_ids": ["mat_01"]}, {"id": "q03", "type": "cloze", "required": true, "correct_answer": ["國民議會", "National Assembly", "國民議會（National Assembly）", "國民議會(National Assembly)"], "reasoning_criteria": "能依6月17日的時間與代表組成，辨認出成立的是國民議會。接受有依據的同義說明，不要求引用固定詞句；不得與之後的國民公會混淆。", "source_text": "6月17日第三等級與部分教士、貴族代表成立國民議會。", "accepted_evidence_ids": ["mat_01"]}], "all_correct_fallback": {"id": "fb_01", "incorrect_claim": "法國大革命初期的權力轉移純粹是一場和平的法律程序，國王與特權階級自願放棄所有政治特權，毫無衝突與爭議。", "correct_interpretation": "雖然初期透過三級會議與國民議會進行了憲政與代表權的爭辯，但這是一個充滿利益衝突、投票爭議與體制對抗的過程，並非毫無阻礙的溫和演變。", "source_text": "法國財政與政治危機促成1789年5月三級會議召開，代表來自教士、貴族與第三等級。對如何投票發生爭議：前兩等級要求按等級計票，第三等級要求按人頭計票。", "evidence_ids": ["mat_01"]}, "draft_review": {"status": "awaiting_researcher_acceptance", "note": "AI生成後經工程驗收修正題意、同義答案與不必要的理由要求；仍待研究者確認難度與內容。"}, "research_material_version": "error-elicitation-draft-20260902"}'::jsonb,
    'teacher_modified'
  WHERE NOT EXISTS (SELECT 1 FROM event_tasks WHERE event_id = v_event_id);
END $$;

-- Local test participants for admin participant dashboard and learner-flow smoke checks.
INSERT INTO participants (id, code, display_name, cohort, condition_list, status, notes, metadata)
VALUES
  ('629c015e-629c-015e-629c-015e629c015e', 'P001', 'Test Participant 01', 'pilot', ARRAY['01','03'], 'active', 'Local test participant seeded by Codex.', '{"seed":"codex","kind":"test"}'::jsonb),
  ('639c02f1-639c-02f1-639c-02f1639c02f1', 'P002', 'Test Participant 02', 'pilot', ARRAY['02','04'], 'active', 'Local test participant seeded by Codex.', '{"seed":"codex","kind":"test"}'::jsonb),
  ('649c0484-649c-0484-649c-0484649c0484', 'P003', 'Test Participant 03', 'pilot', ARRAY['01','02'], 'active', 'Local test participant seeded by Codex.', '{"seed":"codex","kind":"test"}'::jsonb),
  ('659c0617-659c-0617-659c-0617659c0617', 'P004', 'Test Participant 04', 'pilot', ARRAY['03','04'], 'active', 'Local test participant seeded by Codex.', '{"seed":"codex","kind":"test"}'::jsonb),
  ('669c07aa-669c-07aa-669c-07aa669c07aa', 'P005', 'Test Participant 05', 'pilot', ARRAY['01','02','03','04'], 'active', 'Local test participant seeded by Codex.', '{"seed":"codex","kind":"test"}'::jsonb)
ON CONFLICT (code) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  cohort = EXCLUDED.cohort,
  condition_list = EXCLUDED.condition_list,
  status = EXCLUDED.status,
  notes = EXCLUDED.notes,
  metadata = EXCLUDED.metadata;

DO $$
DECLARE
  v_event_id uuid;
  v_persona_id uuid;
  v_task_id uuid;
BEGIN
  INSERT INTO events (
    canonical_name,
    description,
    century,
    start_year,
    end_year,
    context,
    source_summary
  )
  VALUES (
    '霧社事件',
    '霧社事件發生於 1930 年 10 月 27 日的臺灣中部山區，是日治時期最受關注的原住民族抗日事件之一。事件爆發地點在今南投仁愛一帶的霧社地區，當時日本殖民政府已透過警察、學校、道路、勞役與部落管控深入山地社會。賽德克族馬赫坡社領袖莫那·魯道與部分族人，在長期壓力、尊嚴受損、地方衝突與殖民治理矛盾下發動攻擊。事件後，日本方面進行大規模軍事鎮壓，造成大量族人死亡，倖存者也面臨隔離、遷徙與社會重組。理解此事件時，需要同時考慮日本殖民政府、賽德克族部落、漢人居民、學校與警察制度等不同位置，並避免用單一善惡或單一民族敘事取代複雜的歷史判斷。',
    20,
    1930,
    1930,
    '事件需要放在日本殖民統治、原住民族社會、警察制度、地方勞役、族群尊嚴與後續記憶政治中理解。',
    '{"provider":"supabase_seed","language":"zh-TW","research_material_version":"formal-simulation-v1","historical_thinking_dimensions":["historical significance","evidence","continuity and change","cause and consequence","historical perspectives","ethical dimension"]}'::jsonb
  )
  ON CONFLICT (canonical_name) DO UPDATE SET
    description = EXCLUDED.description,
    century = EXCLUDED.century,
    start_year = EXCLUDED.start_year,
    end_year = EXCLUDED.end_year,
    context = EXCLUDED.context,
    source_summary = EXCLUDED.source_summary,
    updated_at = now()
  RETURNING id INTO v_event_id;

  UPDATE personas
  SET
    english_name = 'Mona Rudao',
    role = '賽德克族馬赫坡社領袖',
    biography = '霧社事件中的重要原住民族領袖。事件牽涉日本殖民統治、警察治理、勞役、族群尊嚴、地方權力關係與後續軍事鎮壓。',
    expertise_areas = ARRAY['霧社事件','日本殖民統治','臺灣原住民族史','賽德克族','殖民治理'],
    sources = '[]'::jsonb,
    avatar_url = '/images/personas/mona-rudao.jpg',
    prompt_profile = '{"contract_version":"persona_prompt_v2","speaking_style":"沉著、嚴肅，重視族群尊嚴、殖民壓迫與歷史脈絡。","forms_of_address":"族人或來訪者","social_position":"賽德克族馬赫坡社領袖","relationship_to_event":"處於霧社地區殖民治理與族群衝突的核心","event_timepoint":"1930 年 10 月霧社事件爆發期間","event_timepoint_year":1930,"event_location":"霧社地區","event_vantage_point":"馬赫坡社領袖與族人處境的視角","current_stakes":["族群尊嚴","殖民警察治理","族人安全與行動後果"],"event_anchor_terms":["霧社","賽德克族","殖民警察"],"knowledge_cutoff_year":1930,"firsthand_experience_allowed":false,"firsthand_experience_scope":[],"temporal_boundary":"以 1930 年事件當下可知資訊發言，不得預知後續鎮壓結果與後世記憶政治。","geographic_boundary":"以霧社及其周邊部落可合理接觸的資訊為限。","knowledge_boundary":"只能使用事件當下依人物身份可合理知道的資訊，避免後見之明。","deliberate_error_enabled":false}'::jsonb,
    active = true,
    sort_order = 0,
    revision_state = 'teacher_modified',
    updated_at = now()
  WHERE event_id = v_event_id AND name = '莫那·魯道'
  RETURNING id INTO v_persona_id;

  IF v_persona_id IS NULL THEN
    INSERT INTO personas (
      event_id,
      name,
      english_name,
      role,
      biography,
      expertise_areas,
      sources,
      avatar_url,
      prompt_profile,
      active,
      sort_order,
      revision_state
    )
    VALUES (
      v_event_id,
      '莫那·魯道',
      'Mona Rudao',
      '賽德克族馬赫坡社領袖',
      '霧社事件中的重要原住民族領袖。事件牽涉日本殖民統治、警察治理、勞役、族群尊嚴、地方權力關係與後續軍事鎮壓。',
      ARRAY['霧社事件','日本殖民統治','臺灣原住民族史','賽德克族','殖民治理'],
      '[]'::jsonb,
      '/images/personas/mona-rudao.jpg',
      '{"contract_version":"persona_prompt_v2","speaking_style":"沉著、嚴肅，重視族群尊嚴、殖民壓迫與歷史脈絡。","forms_of_address":"族人或來訪者","social_position":"賽德克族馬赫坡社領袖","relationship_to_event":"處於霧社地區殖民治理與族群衝突的核心","event_timepoint":"1930 年 10 月霧社事件爆發期間","event_timepoint_year":1930,"event_location":"霧社地區","event_vantage_point":"馬赫坡社領袖與族人處境的視角","current_stakes":["族群尊嚴","殖民警察治理","族人安全與行動後果"],"event_anchor_terms":["霧社","賽德克族","殖民警察"],"knowledge_cutoff_year":1930,"firsthand_experience_allowed":false,"firsthand_experience_scope":[],"temporal_boundary":"以 1930 年事件當下可知資訊發言，不得預知後續鎮壓結果與後世記憶政治。","geographic_boundary":"以霧社及其周邊部落可合理接觸的資訊為限。","knowledge_boundary":"只能使用事件當下依人物身份可合理知道的資訊，避免後見之明。","deliberate_error_enabled":false}'::jsonb,
      true,
      0,
      'teacher_modified'
    )
    RETURNING id INTO v_persona_id;
  END IF;

  -- Draft material: researcher review is required before formal collection.
  INSERT INTO event_tasks(event_id, title, story_text, error_elicitation_task_full_text, evaluation_payload, revision_state)
  SELECT v_event_id, '霧社事件之歷史脈絡與多重觀點檢視', '',
    '閱讀霧社事件的館藏與出版品介紹，逐題填寫答案與判斷理由。

Q01：關於這些資料可以支持的判斷，下列哪個說法最適當？{{blank:q01}}

Q02：只要讀完日方軍事記錄，就能完整掌握當時每一位當地族人的生活經驗與立場。請判斷是非。{{blank:q02}}

Q03：館藏介紹指出，霧社事件發生在西元哪一年？請填寫年份，並說明你判斷的依據。{{blank:q03}}',
    '{"contract_version": "error_elicitation_v1", "materials": [{"id": "source_1", "title": "國立臺灣歷史博物館：霧社事件與館藏說明之整理", "text": "館藏〈霧社事件始末〉為中文書寫的事件敘述。博物館介紹記載：霧社事件發生於1930年10月27日，有賽德克族六社參與，莫那魯道為重要領袖；霧社公學校運動會發生攻擊，日方軍警隨後鎮壓。以上為館藏介紹摘要，不是當事人原話。", "source_url": "https://collections.nmth.gov.tw/CollectionContent.aspx?a=132&rno=2017.025.0196.0039", "attribution": "國立臺灣歷史博物館（研究員摘要整理）"}, {"id": "source_2", "title": "國立臺灣歷史博物館：《霧社事件日文史料翻譯》內容介紹之整理", "text": "《霧社事件日文史料翻譯》於2010年出版，收錄日方軍事相關記錄，內容包含軍事行動與後勤補給。本段為出版品介紹摘要，不是軍事記錄的完整原文。", "source_url": "https://www.nmth.gov.tw/jp/News_Publish_Content.aspx?n=4414&s=139464", "attribution": "國立臺灣歷史博物館（出版品介紹摘要整理）"}], "questions": [{"id": "q01", "type": "multiple_choice", "required": true, "correct_answer": "opt_2", "reasoning_criteria": "支援答案的理由必須指出歷史資料（如館藏說明或日方軍事記錄）具有特定的作者觀點、編纂目的或侷限性，不能直接等同於所有當事人的全面經驗。常見的無效推論包括認為單一史料或博物館藏品已代表所有族人的親身心境，或認為官方與館藏記錄完全客觀而無任何編纂立場。", "options": [{"id": "opt_1", "label": "博物館藏品說明與日方軍事記錄皆能完整還原所有族人的真實心境，且不帶任何作者觀點。", "value": "opt_1"}, {"id": "opt_2", "label": "博物館藏品說明或日方軍事記錄反映了特定作者的觀點與記錄目的，不能將單一記述直接視為全體族人的共同經驗。", "value": "opt_2"}, {"id": "opt_3", "label": "莫那·魯道親自撰寫並留下了完整的事件自傳，因此不需要參考其他日方或館藏記錄。", "value": "opt_3"}], "source_text": "館藏〈霧社事件始末〉是中文書寫的事件敘述；其存在不表示它沒有作者觀點，也不能把單一記述當作所有族人經驗。日方軍事記錄的記錄目的和涵蓋範圍，不能代替所有當地族人的生活經驗與立場。", "accepted_evidence_ids": ["source_1", "source_2"]}, {"id": "q02", "type": "true_false", "required": true, "correct_answer": false, "reasoning_criteria": "支援答案的理由必須指出軍方記錄或官方史料主要反映統治者、軍事行動或特定管理視角，其範圍與目的受限於官方紀錄，無法直接涵蓋與替代在地原住民族群多元的生活經驗與內部立場。常見的無效推論為假設官方軍事檔案能平衡且無遺漏地呈現雙方所有個體的真實經歷。", "source_text": "這部2010年出版的史料翻譯集收錄日方軍事相關記錄，包含軍事行動與後勤補給。資料有助研究軍事處置，但軍方記錄的記錄目的和涵蓋範圍，不能代替所有當地族人的生活經驗與立場。", "accepted_evidence_ids": ["source_1", "source_2"]}, {"id": "q03", "type": "cloze", "required": true, "correct_answer": ["1930", "1930年", "一九三零", "一九三零年", "一九三〇", "一九三〇年"], "reasoning_criteria": "能指出年份來自提供的館藏介紹所記錄的事件日期。接受其他可核對的正確年代依據；不能把2010年出版日期當作事件發生年份。不需要額外分析殖民政策才算通過。", "source_text": "館藏介紹記錄霧社事件發生於1930年10月27日。", "accepted_evidence_ids": ["source_1", "source_2"]}], "all_correct_fallback": {"id": "fb_01", "incorrect_claim": "霧社事件純粹是由單一外來因素偶然引發的衝突，且所有參與者的動機與歷史記錄完全一致，無須透過多重史料與脈絡來檢視。", "correct_interpretation": "霧社事件是在日本殖民政府長期透過警察、學校、道路與勞役深入山地社會的結構下，族人面對尊嚴受損與治理矛盾所發動的複雜抗日事件；相關史料與館藏說明各自具有不同的作者觀點與記錄侷限，必須從多重角度進行歷史判斷。", "source_text": "事件爆發地點在今南投仁愛一帶的霧社地區，當時日本殖民政府已透過警察、學校、道路、勞役與部落管控深入山地社會。賽德克族馬赫坡社領袖莫那·魯道與部分族人，在長期壓力、尊嚴受損、地方衝突與殖民治理矛盾下發動攻擊。", "evidence_ids": ["source_1", "source_2"]}, "draft_review": {"status": "awaiting_researcher_acceptance", "note": "AI生成後經工程驗收修正題意、同義答案與不必要的理由要求；仍待研究者確認難度與內容。"}, "research_material_version": "error-elicitation-draft-20260902"}'::jsonb,
    'teacher_modified'
  WHERE NOT EXISTS (SELECT 1 FROM event_tasks WHERE event_id = v_event_id);
END $$;

DO $$
DECLARE
  v_event_id uuid;
  v_persona_id uuid;
  v_task_id uuid;
BEGIN
  INSERT INTO events (
    canonical_name,
    description,
    century,
    start_year,
    end_year,
    context,
    source_summary
  )
  VALUES (
    '鴉片戰爭',
    '鴉片戰爭通常指 1839 至 1842 年間清帝國與英國之間的第一次鴉片戰爭。十九世紀初，英國商人為了扭轉對華貿易中的白銀流出，透過印度鴉片輸入中國，造成嚴重的社會、財政與公共健康問題。清廷派林則徐到廣東禁煙，1839 年虎門銷煙成為衝突升高的重要象徵。英國政府以商業利益、外交待遇與人身財產安全為理由出兵，戰爭沿著中國東南沿海推進。1842 年《南京條約》簽訂後，香港割讓、五口通商、賠款等安排改變了清帝國與西方列強的關係。理解此事件時，需要避免只用落後或侵略兩個詞概括全部問題，而要把林則徐、英國商人、清廷、沿海居民與國際貿易秩序放在同一個分析框架中。',
    19,
    1839,
    1842,
    '事件需要放在鴉片貿易、清朝禁煙、英國帝國商業利益、海防差距、南京條約與條約體系擴張中理解。',
    '{"provider":"supabase_seed","language":"zh-TW","research_material_version":"formal-simulation-v1","historical_thinking_dimensions":["historical significance","evidence","continuity and change","cause and consequence","historical perspectives","ethical dimension"]}'::jsonb
  )
  ON CONFLICT (canonical_name) DO UPDATE SET
    description = EXCLUDED.description,
    century = EXCLUDED.century,
    start_year = EXCLUDED.start_year,
    end_year = EXCLUDED.end_year,
    context = EXCLUDED.context,
    source_summary = EXCLUDED.source_summary,
    updated_at = now()
  RETURNING id INTO v_event_id;

  UPDATE personas
  SET
    english_name = 'Lin Zexu',
    role = '清朝欽差大臣與禁煙政策推動者',
    biography = '林則徐奉道光帝命令前往廣東查禁鴉片，主持虎門銷煙。他的行動成為鴉片戰爭前夕中英衝突的重要節點，也使後人得以討論禁煙、帝國貿易、主權、法律與國際秩序的複雜關係。',
    expertise_areas = ARRAY['鴉片戰爭','清朝外交','虎門銷煙','南京條約','近代中國史'],
    sources = '[]'::jsonb,
    avatar_url = '/images/personas/lin-zexu.jpg',
    prompt_profile = '{"contract_version":"persona_prompt_v2","speaking_style":"謹慎、重視制度與道德責任，會強調禁煙、國家主權與官員職責。","forms_of_address":"閣下","social_position":"清朝欽差大臣與禁煙官員","relationship_to_event":"奉命在廣東查禁鴉片並處理對外衝突","event_timepoint":"1839 年虎門銷煙與中英衝突升高期間","event_timepoint_year":1839,"event_location":"廣東虎門與廣州","event_vantage_point":"奉命禁煙的清朝官員視角","current_stakes":["禁煙成效","國家主權","對外衝突與官員責任"],"event_anchor_terms":["虎門銷煙","廣州","鴉片"],"knowledge_cutoff_year":1839,"firsthand_experience_allowed":false,"firsthand_experience_scope":[],"temporal_boundary":"以 1839 年當下可知資訊發言，不得預知 1842 年條約結果或後世評價。","geographic_boundary":"以廣東禁煙事務與清廷官員可取得的資訊為限。","knowledge_boundary":"只能使用 1839 年依欽差大臣身份可合理知道的資訊，不預知戰爭結果。","deliberate_error_enabled":false}'::jsonb,
    active = true,
    sort_order = 0,
    revision_state = 'teacher_modified',
    updated_at = now()
  WHERE event_id = v_event_id AND name = '林則徐'
  RETURNING id INTO v_persona_id;

  IF v_persona_id IS NULL THEN
    INSERT INTO personas (
      event_id,
      name,
      english_name,
      role,
      biography,
      expertise_areas,
      sources,
      avatar_url,
      prompt_profile,
      active,
      sort_order,
      revision_state
    )
    VALUES (
      v_event_id,
      '林則徐',
      'Lin Zexu',
      '清朝欽差大臣與禁煙政策推動者',
      '林則徐奉道光帝命令前往廣東查禁鴉片，主持虎門銷煙。他的行動成為鴉片戰爭前夕中英衝突的重要節點，也使後人得以討論禁煙、帝國貿易、主權、法律與國際秩序的複雜關係。',
      ARRAY['鴉片戰爭','清朝外交','虎門銷煙','南京條約','近代中國史'],
      '[]'::jsonb,
      '/images/personas/lin-zexu.jpg',
      '{"contract_version":"persona_prompt_v2","speaking_style":"謹慎、重視制度與道德責任，會強調禁煙、國家主權與官員職責。","forms_of_address":"閣下","social_position":"清朝欽差大臣與禁煙官員","relationship_to_event":"奉命在廣東查禁鴉片並處理對外衝突","event_timepoint":"1839 年虎門銷煙與中英衝突升高期間","event_timepoint_year":1839,"event_location":"廣東虎門與廣州","event_vantage_point":"奉命禁煙的清朝官員視角","current_stakes":["禁煙成效","國家主權","對外衝突與官員責任"],"event_anchor_terms":["虎門銷煙","廣州","鴉片"],"knowledge_cutoff_year":1839,"firsthand_experience_allowed":false,"firsthand_experience_scope":[],"temporal_boundary":"以 1839 年當下可知資訊發言，不得預知 1842 年條約結果或後世評價。","geographic_boundary":"以廣東禁煙事務與清廷官員可取得的資訊為限。","knowledge_boundary":"只能使用 1839 年依欽差大臣身份可合理知道的資訊，不預知戰爭結果。","deliberate_error_enabled":false}'::jsonb,
      true,
      0,
      'teacher_modified'
    )
    RETURNING id INTO v_persona_id;
  END IF;

  -- Draft material: researcher review is required before formal collection.
  INSERT INTO event_tasks(event_id, title, story_text, error_elicitation_task_full_text, evaluation_payload, revision_state)
  SELECT v_event_id, '第一次鴉片戰爭與《南京條約》之歷史脈絡探究', '',
    '閱讀《南京條約》節錄的整理，逐題填寫答案與判斷理由。

Q01：關於條約簽訂後的經商安排，下列何者正確？{{blank:q01}}

Q02：條約列出五處准許英國人居住經商的口岸，因此可以斷定當時中國所有城市均已開放英商居住經商。請判斷是非。{{blank:q02}}

Q03：條約第二款列出廣州、廈門、福州、寧波及另一處通商口岸。請填寫第五處城市名稱，並說明依據。{{blank:q03}}',
    '{"contract_version": "error_elicitation_v1", "materials": [{"id": "mat_01", "title": "哥倫比亞大學 Asia for Educators：《南京條約》節錄之整理", "text": "清朝在第一次鴉片戰爭戰敗後，於1842年簽訂《南京條約》。第二款列出廣州、廈門、福州、寧波、上海五處，准許英國人居住經商；第三款割讓香港島。第五款取消英商只能透過公行交易的限制。以上為條約節錄的中文整理，不是原文引句。", "source_url": "https://afe.easia.columbia.edu/ps/china/nanjing.pdf", "attribution": "Columbia University - Asia for Educators (Researcher Summary)"}], "questions": [{"id": "q01", "type": "multiple_choice", "required": true, "correct_answer": "opt_2", "options": [{"id": "opt_1", "label": "條約簽訂後，雙方在完全平等的國際法地位下協商互惠貿易條件。", "value": "opt_1"}, {"id": "opt_2", "label": "條約取消了原本限制英商只能透過公行進行對外貿易的制度。", "value": "opt_2"}, {"id": "opt_3", "label": "條約內容僅規範香港島全境之行政管轄權，未涉及其他沿海城市。", "value": "opt_3"}], "reasoning_criteria": "能以第五款取消公行交易限制，說明為何第二個選項成立。接受對制度改變的合理同義解釋；不強制再分析所有戰爭背景或國際法。", "source_text": "1842年清朝在第一次鴉片戰爭戰敗後簽訂南京條約...第五款取消英商只能透過公行交易的限制。條文記錄制度安排，不能單憑和平友好等措辭推斷雙方權力完全平等。", "accepted_evidence_ids": ["mat_01"]}, {"id": "q02", "type": "true_false", "required": true, "correct_answer": false, "reasoning_criteria": "能說明資料只列五處口岸，不能由部分城市開放推出所有城市開放。接受其他符合條文範圍的合理說明；不以未提供的全部中國城市資料為必要條件。", "source_text": "第二款列出廣州、廈門、福州、寧波、上海五處，沒有宣布中國所有城市均開放。", "accepted_evidence_ids": ["mat_01"]}, {"id": "q03", "type": "cloze", "required": true, "correct_answer": ["上海"], "reasoning_criteria": "支持的理由應依據《南京條約》第二款所列出的五處經商口岸紀錄來回答，指認出廣州、廈門、福州、寧波之外的第五個城市。常見無效推論為混淆近代其他開埠通商口岸（如天津或漢口），未能對照條約節錄中明列的五處南方與東南沿海據點。", "source_text": "第二款列出廣州、廈門、福州、寧波、上海五處，准許英國人居住經商。", "accepted_evidence_ids": ["mat_01"]}], "all_correct_fallback": {"id": "fb_01", "incorrect_claim": "《南京條約》的簽訂完全是由於單純的文化誤解與偶發衝突所致，與當時英國的全球帝國商業擴張及清朝原有的閉關貿易體制無關。", "correct_interpretation": "鴉片戰爭及《南京條約》是十九世紀全球資本主義擴張、英國對華貿易逆差、清朝傳統朝貢與公行貿易體制衝突，以及軍事武力落差交織而成的結構性歷史事件。", "source_text": "事件需要放在鴉片貿易、清朝禁煙、英國帝國商業利益、海防差距、南京條約與條約體系擴張中理解。", "evidence_ids": ["mat_01"]}, "draft_review": {"status": "awaiting_researcher_acceptance", "note": "AI生成後經工程驗收修正題意、同義答案與不必要的理由要求；仍待研究者確認難度與內容。"}, "research_material_version": "error-elicitation-draft-20260902"}'::jsonb,
    'teacher_modified'
  WHERE NOT EXISTS (SELECT 1 FROM event_tasks WHERE event_id = v_event_id);
END $$;

DO $$
DECLARE
  v_event_id uuid;
  v_persona_id uuid;
  v_task_id uuid;
BEGIN
  INSERT INTO events (
    canonical_name,
    description,
    century,
    start_year,
    end_year,
    context,
    source_summary
  )
  VALUES (
    '黑船事件到明治維新',
    '黑船事件到明治維新指的是 1853 年培里率領美國艦隊抵達浦賀後，日本從德川幕府末期走向明治新政府成立的一連串政治、外交與社會轉型。黑船來航暴露了幕府面對西方軍事與外交壓力時的限制，1854 年《神奈川條約》與後續通商條約使日本被迫面對開港、領事裁判權、關稅與國際秩序的新問題。這些外部壓力與日本內部既有矛盾結合，激化尊王攘夷、開國、倒幕與改革的政治運動。1868 年後的新政府推動版籍奉還、廢藩置縣、徵兵、地租改正、教育制度與產業政策，建立中央集權的近代國家，但改革也帶來士族失業、農民負擔、社會衝突與日後對外擴張。',
    19,
    1853,
    1868,
    '事件需要放在黑船來航、不平等條約、幕府權威下降、尊王攘夷、倒幕運動、戊辰戰爭與明治新政府制度改革中理解。',
    '{"provider":"supabase_seed","language":"zh-TW","research_material_version":"formal-simulation-v1","historical_thinking_dimensions":["historical significance","evidence","continuity and change","cause and consequence","historical perspectives","ethical dimension"]}'::jsonb
  )
  ON CONFLICT (canonical_name) DO UPDATE SET
    description = EXCLUDED.description,
    century = EXCLUDED.century,
    start_year = EXCLUDED.start_year,
    end_year = EXCLUDED.end_year,
    context = EXCLUDED.context,
    source_summary = EXCLUDED.source_summary,
    updated_at = now()
  RETURNING id INTO v_event_id;

  UPDATE personas
  SET
    english_name = 'Sakamoto Ryoma',
    role = '幕末改革派志士與薩長同盟促成者之一',
    biography = '坂本龍馬活動於幕末動盪時期，主張吸收海軍與商業知識，參與促成反幕府勢力合作。他適合用來討論黑船來航後日本內部政治選擇、開國壓力與明治維新之間的關係。',
    expertise_areas = ARRAY['黑船來航','幕末政治','薩長同盟','明治維新','近代日本史'],
    sources = '[]'::jsonb,
    avatar_url = '/images/personas/sakamoto-ryoma.jpg',
    prompt_profile = '{"contract_version":"persona_prompt_v2","speaking_style":"開放、務實，重視制度轉型、海權、商業與不同政治勢力之間的協商。","forms_of_address":"朋友","social_position":"土佐藩出身的幕末志士與海援隊領袖","relationship_to_event":"參與幕末政治協商，思考開國、海權與政權轉型","event_timepoint":"1867 年大政奉還前後的幕末政局","event_timepoint_year":1867,"event_location":"京都","event_vantage_point":"推動薩長協調與政權和平轉型的幕末志士視角","current_stakes":["幕府與朝廷的權力轉移","內戰風險","海權與對外開放"],"event_anchor_terms":["大政奉還","幕府","海援隊"],"knowledge_cutoff_year":1867,"firsthand_experience_allowed":false,"firsthand_experience_scope":[],"temporal_boundary":"以 1867 年當下可知資訊發言，不得知道本人遇刺後或明治政府成立後的結果。","geographic_boundary":"以京都、土佐及海援隊政治商業網絡中可合理取得的資訊為限。","knowledge_boundary":"只能使用 1867 年依人物經歷與網絡可合理知道的資訊，不預知明治政府成立後的發展。","deliberate_error_enabled":false}'::jsonb,
    active = true,
    sort_order = 0,
    revision_state = 'teacher_modified',
    updated_at = now()
  WHERE event_id = v_event_id AND name = '坂本龍馬'
  RETURNING id INTO v_persona_id;

  IF v_persona_id IS NULL THEN
    INSERT INTO personas (
      event_id,
      name,
      english_name,
      role,
      biography,
      expertise_areas,
      sources,
      avatar_url,
      prompt_profile,
      active,
      sort_order,
      revision_state
    )
    VALUES (
      v_event_id,
      '坂本龍馬',
      'Sakamoto Ryoma',
      '幕末改革派志士與薩長同盟促成者之一',
      '坂本龍馬活動於幕末動盪時期，主張吸收海軍與商業知識，參與促成反幕府勢力合作。他適合用來討論黑船來航後日本內部政治選擇、開國壓力與明治維新之間的關係。',
      ARRAY['黑船來航','幕末政治','薩長同盟','明治維新','近代日本史'],
      '[]'::jsonb,
      '/images/personas/sakamoto-ryoma.jpg',
      '{"contract_version":"persona_prompt_v2","speaking_style":"開放、務實，重視制度轉型、海權、商業與不同政治勢力之間的協商。","forms_of_address":"朋友","social_position":"土佐藩出身的幕末志士與海援隊領袖","relationship_to_event":"參與幕末政治協商，思考開國、海權與政權轉型","event_timepoint":"1867 年大政奉還前後的幕末政局","event_timepoint_year":1867,"event_location":"京都","event_vantage_point":"推動薩長協調與政權和平轉型的幕末志士視角","current_stakes":["幕府與朝廷的權力轉移","內戰風險","海權與對外開放"],"event_anchor_terms":["大政奉還","幕府","海援隊"],"knowledge_cutoff_year":1867,"firsthand_experience_allowed":false,"firsthand_experience_scope":[],"temporal_boundary":"以 1867 年當下可知資訊發言，不得知道本人遇刺後或明治政府成立後的結果。","geographic_boundary":"以京都、土佐及海援隊政治商業網絡中可合理取得的資訊為限。","knowledge_boundary":"只能使用 1867 年依人物經歷與網絡可合理知道的資訊，不預知明治政府成立後的發展。","deliberate_error_enabled":false}'::jsonb,
      true,
      0,
      'teacher_modified'
    )
    RETURNING id INTO v_persona_id;
  END IF;

  -- Draft material: researcher review is required before formal collection.
  INSERT INTO event_tasks(event_id, title, story_text, error_elicitation_task_full_text, evaluation_payload, revision_state)
  SELECT v_event_id, '黑船事件到明治維新：初期政治轉型與制度構想任務', '',
    '閱讀日本幕末到明治初期的政治構想資料，逐題填寫答案與判斷理由。

Q01：黑船來航與開國之後，日本國內對政體的討論呈現何種情況？請選出最適當的敘述。{{blank:q01}}

Q02：1868年《五箇條御誓文》主張設置會議、以公議決定政事，所以僅憑這段主張就能證明日本當時已實施現代普選民主。請判斷是非。{{blank:q02}}

Q03：資料中1867年大政奉還的政權構想，以哪個政治機構為中心？請填寫機構名稱並說明理由。{{blank:q03}}',
    '{"contract_version": "error_elicitation_v1", "materials": [{"id": "source_1", "title": "日本國立國會圖書館：近代日本的政治制度構想之整理", "text": "1853年培里黑船來航與其後開國，促使日本廣泛討論政體。1867年大政奉還提出以朝廷為中心、以公議為名的政治構想。1868年《五箇條御誓文》主張設置會議、以公議決定政事。幕末到明治初期存在不同的政治方案。本段依日本國立國會圖書館展覽說明整理，不是歷史人物原話。", "source_url": "https://www.ndl.go.jp/modern/e/cha1/", "attribution": "日本國立國會圖書館近代日本展覽說明（中文摘要）"}], "questions": [{"id": "q01", "type": "multiple_choice", "required": true, "correct_answer": "B", "options": [{"id": "opt_a", "label": "當時僅有單一的倒幕派政治主張，並無其他不同方案", "value": "A"}, {"id": "opt_b", "label": "社會各界針對政體與開國引發了廣泛且多樣的政治討論", "value": "B"}, {"id": "opt_c", "label": "幕府順利透過鎖國政策完全封鎖了所有外來政治思潮", "value": "C"}], "reasoning_criteria": "支持B選項的理由必須指出黑船來航與開國壓力促使日本國內出現不同的政治方案與廣泛討論，而非單一聲音或成功鎖國。常見無效推理包括誤以為外力直接決定一切改革，或認為當時已形成現代政黨政治。", "source_text": "1853年培里黑船來航與其後開國，促使日本廣泛討論政體。幕府末期到明治初期有不同政治方案...", "accepted_evidence_ids": ["source_1"]}, {"id": "q02", "type": "true_false", "required": true, "correct_answer": false, "reasoning_criteria": "支持錯誤（False）的理由必須說明《五箇條御誓文》雖提出公議與會議，但不能將其直接等同於現代普選民主的落實。常見無效推理為因看到「設置會議」和「公議」等字眼，便直接將其與20世紀或當代的普選民主劃上等號。", "source_text": "1868年五箇條御誓文主張設置會議、以公議決定政事... 不能把這些主張直接等同現代普選民主已经落實...", "accepted_evidence_ids": ["source_1"]}, {"id": "q03", "type": "cloze", "required": true, "correct_answer": ["朝廷", "日本朝廷", "天皇朝廷", "天皇", "以朝廷為中心"], "reasoning_criteria": "能依材料指出政治權威中心是朝廷或天皇，而不是把公議這種決策原則當成機構名稱。接受其他正確且有依據的說明，不要求固定用語。", "source_text": "1867年大政奉還以朝廷為中心、公議為名提出政權構想...", "accepted_evidence_ids": ["source_1"]}], "all_correct_fallback": {"id": "fb_01", "incorrect_claim": "幕府末期到明治初期的所有政治變革與制度構想，皆是由外國列強直接擬定並強加給日本的結果。", "correct_interpretation": "雖然外國帶來的壓力是促使日本開國與轉型的外部背景，但國內政治轉型與制度構想（如大政奉還與五箇條御誓文）是由日本內部不同政治力量與思想激盪下所發展出來的多元方案，不能將後續所有改革完全歸咎或歸功於外國直接決定。", "source_text": "不能只因外力先到便斷定後續所有改革都由外國決定。", "evidence_ids": ["source_1"]}, "draft_review": {"status": "awaiting_researcher_acceptance", "note": "AI生成後經工程驗收修正題意、同義答案與不必要的理由要求；仍待研究者確認難度與內容。"}, "research_material_version": "error-elicitation-draft-20260902"}'::jsonb,
    'teacher_modified'
  WHERE NOT EXISTS (SELECT 1 FROM event_tasks WHERE event_id = v_event_id);
END $$;

-- 研究介面使用可讀的翻譯語體；保留人物差異，但不捏造名言、方言或現代教師話術。
with persona_voice_defaults(name, translated_style) as (
  values
    (
      '馬克西米連·羅伯斯比爾',
      '使用可讀的繁體中文翻譯法國革命政治語體；正式、克制而具論辯性，常從公民、共和、德行、公共利益與政治責任辨析問題。句子可以堅定但不可像現代教師講課，不模仿後世宣傳，也不捏造本人名言。'
    ),
    (
      '莫那·魯道',
      '使用可讀的繁體中文作為翻譯語體；句子短而直接，少用學術分類與抽象口號，從族人、土地、勞役、警察權力、尊嚴與行動後果說話。語氣克制而堅定，不像教師講課；不得捏造賽德克語原句或把後世概念說成當時用語。'
    ),
    (
      '林則徐',
      '使用可讀的繁體中文翻譯清代官員語體；持重、簡練，先辨法度、職責、利害與民生，再談禁煙及對外關係。不堆砌文言、不冒充奏摺原文，也不使用現代教師或政策系統話術。'
    ),
    (
      '坂本龍馬',
      '使用可讀的繁體中文翻譯幕末人物語體；直率、務實並帶商議感，常從海路、貿易、藩與幕府、政治協調及避免內戰談問題。不套用現代管理術語，不捏造土佐方言或後世流傳名言。'
    )
)
update personas as persona
set prompt_profile = jsonb_set(
  coalesce(persona.prompt_profile, '{}'::jsonb),
  '{speaking_style}',
  to_jsonb(defaults.translated_style),
  true
)
from persona_voice_defaults as defaults
where persona.name = defaults.name;
