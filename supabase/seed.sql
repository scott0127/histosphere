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
    prompt_profile = '{"voice":"嚴肅、論辯性強，重視共和德行與公共利益。","knowledge_boundary":"只能以法國大革命時期及其可合理追溯的脈絡發言，不預知後世史學評價。","deliberate_error_enabled":false}'::jsonb,
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
      '{"voice":"嚴肅、論辯性強，重視共和德行與公共利益。","knowledge_boundary":"只能以法國大革命時期及其可合理追溯的脈絡發言，不預知後世史學評價。","deliberate_error_enabled":false}'::jsonb,
      true,
      0,
      'teacher_modified'
    )
    RETURNING id INTO v_persona_id;
  END IF;

  UPDATE event_tasks
  SET
    story_text = '1789 年以前，法國舊制度面臨財政危機、特權階級免稅、糧食價格上漲與代表權不平等。第三等級在三級會議中主張以人數而不是等級表決，並逐步形成國民議會。1789 年 7 月 14 日，巴黎群眾攻占巴士底監獄，象徵王權威信受到挑戰。革命後，《人權和公民權宣言》提出自由、平等與公民權利，但戰爭、派系衝突與恐怖統治也顯示革命並非單純走向穩定共和。',
    display_text = '1789 年以前，法國舊制度面臨{{blank:q01}}、特權階級免稅、糧食價格上漲與代表權不平等。第三等級在三級會議中主張以{{blank:q02}}而不是等級表決，並逐步形成國民議會。1789 年 7 月 14 日，巴黎群眾攻占{{blank:q03}}，象徵王權威信受到挑戰。革命後，《人權和公民權宣言》提出自由、平等與公民權利，但戰爭、派系衝突與恐怖統治也顯示：{{blank:q04}}',
    evaluation_payload = '{"rubric":"評估學生是否能辨識法國大革命的結構性原因、代表權爭議、關鍵事件象徵，並能避免把革命簡化為單線性的民主勝利故事。","target_misconceptions":["把法國大革命簡化為人民單純推翻國王","忽略財政危機、特權制度與代表權爭議的結構性因素","認為共和理念出現後政治暴力與權力集中問題就自然消失"],"questions":[{"id":"q01","blank_id":"q01","type":"cloze","prompt":"請填入一個舊制度面臨的結構性危機。","placeholder":"例如：財政危機","required":true,"correct_answer":"財政危機","source_text":"財政危機","explanation":"這題用來觀察學生是否能從事件前的制度條件解釋革命爆發。"},{"id":"q02","blank_id":"q02","type":"multiple_choice","prompt":"第三等級主張三級會議應以哪一種方式表決？","required":true,"options":[{"id":"a","label":"人數","value":"人數"},{"id":"b","label":"等級","value":"等級"},{"id":"c","label":"國王任命","value":"國王任命"}],"correct_answer":"人數","source_text":"人數","explanation":"這題檢查學生是否理解代表權衝突，而不只記得革命口號。"},{"id":"q03","blank_id":"q03","type":"cloze","prompt":"1789 年 7 月 14 日巴黎群眾攻占哪一個象徵王權的地點？","placeholder":"請輸入地點","required":true,"correct_answer":"巴士底監獄","source_text":"巴士底監獄","explanation":"這題檢查學生能否把關鍵事件與其象徵意義連結。"},{"id":"q04","blank_id":"q04","type":"true_false","prompt":"法國大革命建立共和理念後，政治衝突與暴力就完全消失。","required":true,"correct_answer":false,"source_text":"革命並非單純走向穩定共和","explanation":"這題用來捕捉學生是否把革命敘事過度簡化為線性進步。"}]}'::jsonb,
    revision_state = 'teacher_modified',
    updated_at = now()
  WHERE event_id = v_event_id AND title = '法國大革命：舊制度危機與革命轉折'
  RETURNING id INTO v_task_id;

  IF v_task_id IS NULL THEN
    INSERT INTO event_tasks (
      event_id,
      title,
      story_text,
      display_text,
      evaluation_payload,
      revision_state
    )
    VALUES (
      v_event_id,
      '法國大革命：舊制度危機與革命轉折',
      '1789 年以前，法國舊制度面臨財政危機、特權階級免稅、糧食價格上漲與代表權不平等。第三等級在三級會議中主張以人數而不是等級表決，並逐步形成國民議會。1789 年 7 月 14 日，巴黎群眾攻占巴士底監獄，象徵王權威信受到挑戰。革命後，《人權和公民權宣言》提出自由、平等與公民權利，但戰爭、派系衝突與恐怖統治也顯示革命並非單純走向穩定共和。',
      '1789 年以前，法國舊制度面臨{{blank:q01}}、特權階級免稅、糧食價格上漲與代表權不平等。第三等級在三級會議中主張以{{blank:q02}}而不是等級表決，並逐步形成國民議會。1789 年 7 月 14 日，巴黎群眾攻占{{blank:q03}}，象徵王權威信受到挑戰。革命後，《人權和公民權宣言》提出自由、平等與公民權利，但戰爭、派系衝突與恐怖統治也顯示：{{blank:q04}}',
      '{"rubric":"評估學生是否能辨識法國大革命的結構性原因、代表權爭議、關鍵事件象徵，並能避免把革命簡化為單線性的民主勝利故事。","target_misconceptions":["把法國大革命簡化為人民單純推翻國王","忽略財政危機、特權制度與代表權爭議的結構性因素","認為共和理念出現後政治暴力與權力集中問題就自然消失"],"questions":[{"id":"q01","blank_id":"q01","type":"cloze","prompt":"請填入一個舊制度面臨的結構性危機。","placeholder":"例如：財政危機","required":true,"correct_answer":"財政危機","source_text":"財政危機","explanation":"這題用來觀察學生是否能從事件前的制度條件解釋革命爆發。"},{"id":"q02","blank_id":"q02","type":"multiple_choice","prompt":"第三等級主張三級會議應以哪一種方式表決？","required":true,"options":[{"id":"a","label":"人數","value":"人數"},{"id":"b","label":"等級","value":"等級"},{"id":"c","label":"國王任命","value":"國王任命"}],"correct_answer":"人數","source_text":"人數","explanation":"這題檢查學生是否理解代表權衝突，而不只記得革命口號。"},{"id":"q03","blank_id":"q03","type":"cloze","prompt":"1789 年 7 月 14 日巴黎群眾攻占哪一個象徵王權的地點？","placeholder":"請輸入地點","required":true,"correct_answer":"巴士底監獄","source_text":"巴士底監獄","explanation":"這題檢查學生能否把關鍵事件與其象徵意義連結。"},{"id":"q04","blank_id":"q04","type":"true_false","prompt":"法國大革命建立共和理念後，政治衝突與暴力就完全消失。","required":true,"correct_answer":false,"source_text":"革命並非單純走向穩定共和","explanation":"這題用來捕捉學生是否把革命敘事過度簡化為線性進步。"}]}'::jsonb,
      'teacher_modified'
    )
    RETURNING id INTO v_task_id;
  END IF;
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
    prompt_profile = '{"voice":"沉著、嚴肅，重視族群尊嚴、殖民壓迫與歷史脈絡。","knowledge_boundary":"以 1930 年前後霧社事件相關脈絡發言，避免後見之明。","deliberate_error_enabled":false}'::jsonb,
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
      '{"voice":"沉著、嚴肅，重視族群尊嚴、殖民壓迫與歷史脈絡。","knowledge_boundary":"以 1930 年前後霧社事件相關脈絡發言，避免後見之明。","deliberate_error_enabled":false}'::jsonb,
      true,
      0,
      'teacher_modified'
    )
    RETURNING id INTO v_persona_id;
  END IF;

  UPDATE event_tasks
  SET
    story_text = '1930 年 10 月 27 日清晨，臺灣中部山區的霧社地區正在準備公學校運動會。一名記錄地方新聞的第三方觀察者若站在霧社街道旁，會看見日本警察、學校職員、族人、孩童與外來居民聚集，也會聽見殖民秩序下長期累積的緊張。莫那·魯道與部分賽德克族人發動攻擊，事件迅速從地方衝突變成殖民政府高度重視的軍事與政治危機。後續鎮壓、隔離與記憶書寫，使霧社事件不只是一次武力衝突，而是理解殖民治理、族群尊嚴、證據差異、延續與變遷、歷史同理與倫理判斷的重要案例。',
    display_text = '1930 年 10 月 27 日清晨，臺灣中部山區的{{blank:w01}}正在準備公學校運動會。一名記錄地方新聞的第三方觀察者若站在霧社街道旁，會看見日本警察、學校職員、族人、孩童與外來居民聚集，也會聽見殖民秩序下長期累積的緊張。{{blank:w02}}與部分賽德克族人發動攻擊，事件迅速從地方衝突變成殖民政府高度重視的軍事與政治危機。研究者不能只讀單一官方材料，也需要比較{{blank:w03}}；追問原因時，不能只說是個人衝突，而要把{{blank:w04}}放進脈絡。若有人主張霧社事件只是單純暴動，完全不需要理解殖民者與被殖民者的處境差異，這個判斷是{{blank:w05}}。',
    evaluation_payload = '{"rubric":"評估學生是否能從歷史重要性、證據、延續與變遷、原因與後果、歷史觀點取替、倫理維度六個面向理解霧社事件，而不是把事件簡化為單一暴力或單一族群立場。","target_misconceptions":["把霧社事件簡化為單純暴動","忽略殖民治理與警察權力脈絡","只採用官方紀錄而忽略口述與地方記憶","用當代立場直接替所有行動者貼上單一善惡標籤"],"questions":[{"id":"w01","blank_id":"w01","type":"cloze","prompt":"請填入事件發生的主要地點。","placeholder":"請輸入地點","required":true,"correct_answer":"霧社地區","source_text":"霧社地區","explanation":"人事時地物中的地，也讓學生把事件放回具體空間。"},{"id":"w02","blank_id":"w02","type":"cloze","prompt":"請填入事件中最常被提及的賽德克族領袖。","placeholder":"請輸入人物","required":true,"correct_answer":"莫那·魯道","source_text":"莫那·魯道","explanation":"人事時地物中的人，但仍避免把事件完全歸因於單一英雄敘事。"},{"id":"w03","blank_id":"w03","type":"multiple_choice","prompt":"研究者比較事件證據時，最適合同時參考哪一組材料？","required":true,"options":[{"id":"a","label":"官方報告、報紙紀錄與口述記憶","value":"官方報告、報紙紀錄與口述記憶"},{"id":"b","label":"只看殖民政府公告","value":"只看殖民政府公告"},{"id":"c","label":"只看後來的影視作品","value":"只看後來的影視作品"}],"correct_answer":"官方報告、報紙紀錄與口述記憶","source_text":"官方報告、報紙紀錄與口述記憶","explanation":"對應 historical evidence，提醒學生證據來源會影響敘事。"},{"id":"w04","blank_id":"w04","type":"multiple_choice","prompt":"下列哪個脈絡最能說明事件的長期原因？","required":true,"options":[{"id":"a","label":"殖民治理、警察權力與勞役壓力","value":"殖民治理、警察權力與勞役壓力"},{"id":"b","label":"單一偶發口角","value":"單一偶發口角"},{"id":"c","label":"歐洲戰爭直接引發","value":"歐洲戰爭直接引發"}],"correct_answer":"殖民治理、警察權力與勞役壓力","source_text":"殖民治理、警察權力與勞役壓力","explanation":"對應 causes and consequences，要求學生區分近因與結構原因。"},{"id":"w05","blank_id":"w05","type":"true_false","prompt":"霧社事件只是單純暴動，完全不需要理解殖民者與被殖民者的處境差異。","required":true,"correct_answer":false,"source_text":"錯誤","explanation":"對應 historical perspectives 與 ethical dimension，避免扁平化判斷。"}]}'::jsonb,
    revision_state = 'teacher_modified',
    updated_at = now()
  WHERE event_id = v_event_id AND title = '霧社事件：殖民治理、族群尊嚴與歷史判斷'
  RETURNING id INTO v_task_id;

  IF v_task_id IS NULL THEN
    INSERT INTO event_tasks (
      event_id,
      title,
      story_text,
      display_text,
      evaluation_payload,
      revision_state
    )
    VALUES (
      v_event_id,
      '霧社事件：殖民治理、族群尊嚴與歷史判斷',
      '1930 年 10 月 27 日清晨，臺灣中部山區的霧社地區正在準備公學校運動會。一名記錄地方新聞的第三方觀察者若站在霧社街道旁，會看見日本警察、學校職員、族人、孩童與外來居民聚集，也會聽見殖民秩序下長期累積的緊張。莫那·魯道與部分賽德克族人發動攻擊，事件迅速從地方衝突變成殖民政府高度重視的軍事與政治危機。後續鎮壓、隔離與記憶書寫，使霧社事件不只是一次武力衝突，而是理解殖民治理、族群尊嚴、證據差異、延續與變遷、歷史同理與倫理判斷的重要案例。',
      '1930 年 10 月 27 日清晨，臺灣中部山區的{{blank:w01}}正在準備公學校運動會。一名記錄地方新聞的第三方觀察者若站在霧社街道旁，會看見日本警察、學校職員、族人、孩童與外來居民聚集，也會聽見殖民秩序下長期累積的緊張。{{blank:w02}}與部分賽德克族人發動攻擊，事件迅速從地方衝突變成殖民政府高度重視的軍事與政治危機。研究者不能只讀單一官方材料，也需要比較{{blank:w03}}；追問原因時，不能只說是個人衝突，而要把{{blank:w04}}放進脈絡。若有人主張霧社事件只是單純暴動，完全不需要理解殖民者與被殖民者的處境差異，這個判斷是{{blank:w05}}。',
      '{"rubric":"評估學生是否能從歷史重要性、證據、延續與變遷、原因與後果、歷史觀點取替、倫理維度六個面向理解霧社事件，而不是把事件簡化為單一暴力或單一族群立場。","target_misconceptions":["把霧社事件簡化為單純暴動","忽略殖民治理與警察權力脈絡","只採用官方紀錄而忽略口述與地方記憶","用當代立場直接替所有行動者貼上單一善惡標籤"],"questions":[{"id":"w01","blank_id":"w01","type":"cloze","prompt":"請填入事件發生的主要地點。","placeholder":"請輸入地點","required":true,"correct_answer":"霧社地區","source_text":"霧社地區","explanation":"人事時地物中的地，也讓學生把事件放回具體空間。"},{"id":"w02","blank_id":"w02","type":"cloze","prompt":"請填入事件中最常被提及的賽德克族領袖。","placeholder":"請輸入人物","required":true,"correct_answer":"莫那·魯道","source_text":"莫那·魯道","explanation":"人事時地物中的人，但仍避免把事件完全歸因於單一英雄敘事。"},{"id":"w03","blank_id":"w03","type":"multiple_choice","prompt":"研究者比較事件證據時，最適合同時參考哪一組材料？","required":true,"options":[{"id":"a","label":"官方報告、報紙紀錄與口述記憶","value":"官方報告、報紙紀錄與口述記憶"},{"id":"b","label":"只看殖民政府公告","value":"只看殖民政府公告"},{"id":"c","label":"只看後來的影視作品","value":"只看後來的影視作品"}],"correct_answer":"官方報告、報紙紀錄與口述記憶","source_text":"官方報告、報紙紀錄與口述記憶","explanation":"對應 historical evidence，提醒學生證據來源會影響敘事。"},{"id":"w04","blank_id":"w04","type":"multiple_choice","prompt":"下列哪個脈絡最能說明事件的長期原因？","required":true,"options":[{"id":"a","label":"殖民治理、警察權力與勞役壓力","value":"殖民治理、警察權力與勞役壓力"},{"id":"b","label":"單一偶發口角","value":"單一偶發口角"},{"id":"c","label":"歐洲戰爭直接引發","value":"歐洲戰爭直接引發"}],"correct_answer":"殖民治理、警察權力與勞役壓力","source_text":"殖民治理、警察權力與勞役壓力","explanation":"對應 causes and consequences，要求學生區分近因與結構原因。"},{"id":"w05","blank_id":"w05","type":"true_false","prompt":"霧社事件只是單純暴動，完全不需要理解殖民者與被殖民者的處境差異。","required":true,"correct_answer":false,"source_text":"錯誤","explanation":"對應 historical perspectives 與 ethical dimension，避免扁平化判斷。"}]}'::jsonb,
      'teacher_modified'
    )
    RETURNING id INTO v_task_id;
  END IF;
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
    prompt_profile = '{"voice":"謹慎、重視制度與道德責任，會強調禁煙、國家主權與官員職責。","knowledge_boundary":"以清朝禁煙與第一次鴉片戰爭前後脈絡發言，不預知後世政治評價。","deliberate_error_enabled":false}'::jsonb,
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
      '{"voice":"謹慎、重視制度與道德責任，會強調禁煙、國家主權與官員職責。","knowledge_boundary":"以清朝禁煙與第一次鴉片戰爭前後脈絡發言，不預知後世政治評價。","deliberate_error_enabled":false}'::jsonb,
      true,
      0,
      'teacher_modified'
    )
    RETURNING id INTO v_persona_id;
  END IF;

  UPDATE event_tasks
  SET
    story_text = '1839 年至 1842 年間，清帝國與英國之間的衝突從廣州禁煙、虎門銷煙、海上軍事壓力，逐步擴大為鴉片戰爭。一名停留在廣州十三行附近的第三方觀察者，可能同時看見清朝官員查禁鴉片、英國商人要求貿易保障、地方百姓承受毒品與戰爭壓力、外國軍艦沿海北上。林則徐、道光帝、英國商人、英國政府與沿海居民都位於不同權力位置。戰爭結果以 1842 年《南京條約》作為重要轉折，香港割讓、通商口岸開放、賠款與後續治外法權安排，改變了中國與西方列強的互動方式。',
    display_text = '1839 年至 1842 年間，清帝國與英國之間的衝突從廣州禁煙、{{blank:o01}}、海上軍事壓力，逐步擴大為鴉片戰爭。一名停留在廣州十三行附近的第三方觀察者，可能同時看見清朝官員查禁鴉片、英國商人要求貿易保障、地方百姓承受毒品與戰爭壓力、外國軍艦沿海北上。{{blank:o02}}、道光帝、英國商人、英國政府與沿海居民都位於不同權力位置。若要判斷事件證據，研究者應比較{{blank:o03}}，而不是只讀勝利者或失敗者的一方說法。分析後果時，1842 年的{{blank:o04}}使香港割讓、通商口岸開放與賠款成為重要轉折。若有人說鴉片戰爭只是一場普通商業糾紛，與主權、毒品與不平等條約無關，這個判斷是{{blank:o05}}。',
    evaluation_payload = '{"rubric":"評估學生是否能從歷史重要性、證據、延續與變遷、原因與後果、歷史觀點取替、倫理維度六個面向理解鴉片戰爭，避免把事件簡化為清朝落後或英國自由貿易。","target_misconceptions":["把鴉片戰爭簡化為清朝單純落後","忽略鴉片貿易與毒品倫理","只把南京條約視為一般外交協議","忽略英國商人、清朝官員與沿海居民的不同處境"],"questions":[{"id":"o01","blank_id":"o01","type":"cloze","prompt":"請填入 1839 年禁煙行動中最具象徵性的事件。","placeholder":"請輸入事件","required":true,"correct_answer":"虎門銷煙","source_text":"虎門銷煙","explanation":"對應 historical significance，讓學生辨認事件轉折點。"},{"id":"o02","blank_id":"o02","type":"cloze","prompt":"請填入禁煙政策中最重要的清朝官員。","placeholder":"請輸入人物","required":true,"correct_answer":"林則徐","source_text":"林則徐","explanation":"人事時地物中的人，也讓學生思考官員職責與政策限制。"},{"id":"o03","blank_id":"o03","type":"multiple_choice","prompt":"研究者比較鴉片戰爭證據時，哪一組材料最適合互相參照？","required":true,"options":[{"id":"a","label":"清朝奏摺、英方商務紀錄、條約文本與地方記載","value":"清朝奏摺、英方商務紀錄、條約文本與地方記載"},{"id":"b","label":"只看英國議會說法","value":"只看英國議會說法"},{"id":"c","label":"只看後來的民族主義敘事","value":"只看後來的民族主義敘事"}],"correct_answer":"清朝奏摺、英方商務紀錄、條約文本與地方記載","source_text":"清朝奏摺、英方商務紀錄、條約文本與地方記載","explanation":"對應 evidence，提醒學生證據互證與來源位置。"},{"id":"o04","blank_id":"o04","type":"cloze","prompt":"請填入 1842 年結束第一次鴉片戰爭的重要條約。","placeholder":"請輸入條約名稱","required":true,"correct_answer":"南京條約","source_text":"南京條約","explanation":"對應 continuity and change，條約標示中國對外關係制度性變化。"},{"id":"o05","blank_id":"o05","type":"true_false","prompt":"鴉片戰爭只是一場普通商業糾紛，與主權、毒品與不平等條約無關。","required":true,"correct_answer":false,"source_text":"錯誤","explanation":"對應 cause/consequence、historical perspectives 與 ethical dimension。"}]}'::jsonb,
    revision_state = 'teacher_modified',
    updated_at = now()
  WHERE event_id = v_event_id AND title = '鴉片戰爭：貿易、主權與不平等條約'
  RETURNING id INTO v_task_id;

  IF v_task_id IS NULL THEN
    INSERT INTO event_tasks (
      event_id,
      title,
      story_text,
      display_text,
      evaluation_payload,
      revision_state
    )
    VALUES (
      v_event_id,
      '鴉片戰爭：貿易、主權與不平等條約',
      '1839 年至 1842 年間，清帝國與英國之間的衝突從廣州禁煙、虎門銷煙、海上軍事壓力，逐步擴大為鴉片戰爭。一名停留在廣州十三行附近的第三方觀察者，可能同時看見清朝官員查禁鴉片、英國商人要求貿易保障、地方百姓承受毒品與戰爭壓力、外國軍艦沿海北上。林則徐、道光帝、英國商人、英國政府與沿海居民都位於不同權力位置。戰爭結果以 1842 年《南京條約》作為重要轉折，香港割讓、通商口岸開放、賠款與後續治外法權安排，改變了中國與西方列強的互動方式。',
      '1839 年至 1842 年間，清帝國與英國之間的衝突從廣州禁煙、{{blank:o01}}、海上軍事壓力，逐步擴大為鴉片戰爭。一名停留在廣州十三行附近的第三方觀察者，可能同時看見清朝官員查禁鴉片、英國商人要求貿易保障、地方百姓承受毒品與戰爭壓力、外國軍艦沿海北上。{{blank:o02}}、道光帝、英國商人、英國政府與沿海居民都位於不同權力位置。若要判斷事件證據，研究者應比較{{blank:o03}}，而不是只讀勝利者或失敗者的一方說法。分析後果時，1842 年的{{blank:o04}}使香港割讓、通商口岸開放與賠款成為重要轉折。若有人說鴉片戰爭只是一場普通商業糾紛，與主權、毒品與不平等條約無關，這個判斷是{{blank:o05}}。',
      '{"rubric":"評估學生是否能從歷史重要性、證據、延續與變遷、原因與後果、歷史觀點取替、倫理維度六個面向理解鴉片戰爭，避免把事件簡化為清朝落後或英國自由貿易。","target_misconceptions":["把鴉片戰爭簡化為清朝單純落後","忽略鴉片貿易與毒品倫理","只把南京條約視為一般外交協議","忽略英國商人、清朝官員與沿海居民的不同處境"],"questions":[{"id":"o01","blank_id":"o01","type":"cloze","prompt":"請填入 1839 年禁煙行動中最具象徵性的事件。","placeholder":"請輸入事件","required":true,"correct_answer":"虎門銷煙","source_text":"虎門銷煙","explanation":"對應 historical significance，讓學生辨認事件轉折點。"},{"id":"o02","blank_id":"o02","type":"cloze","prompt":"請填入禁煙政策中最重要的清朝官員。","placeholder":"請輸入人物","required":true,"correct_answer":"林則徐","source_text":"林則徐","explanation":"人事時地物中的人，也讓學生思考官員職責與政策限制。"},{"id":"o03","blank_id":"o03","type":"multiple_choice","prompt":"研究者比較鴉片戰爭證據時，哪一組材料最適合互相參照？","required":true,"options":[{"id":"a","label":"清朝奏摺、英方商務紀錄、條約文本與地方記載","value":"清朝奏摺、英方商務紀錄、條約文本與地方記載"},{"id":"b","label":"只看英國議會說法","value":"只看英國議會說法"},{"id":"c","label":"只看後來的民族主義敘事","value":"只看後來的民族主義敘事"}],"correct_answer":"清朝奏摺、英方商務紀錄、條約文本與地方記載","source_text":"清朝奏摺、英方商務紀錄、條約文本與地方記載","explanation":"對應 evidence，提醒學生證據互證與來源位置。"},{"id":"o04","blank_id":"o04","type":"cloze","prompt":"請填入 1842 年結束第一次鴉片戰爭的重要條約。","placeholder":"請輸入條約名稱","required":true,"correct_answer":"南京條約","source_text":"南京條約","explanation":"對應 continuity and change，條約標示中國對外關係制度性變化。"},{"id":"o05","blank_id":"o05","type":"true_false","prompt":"鴉片戰爭只是一場普通商業糾紛，與主權、毒品與不平等條約無關。","required":true,"correct_answer":false,"source_text":"錯誤","explanation":"對應 cause/consequence、historical perspectives 與 ethical dimension。"}]}'::jsonb,
      'teacher_modified'
    )
    RETURNING id INTO v_task_id;
  END IF;
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
    prompt_profile = '{"voice":"開放、務實，重視制度轉型、海權、商業與不同政治勢力之間的協商。","knowledge_boundary":"以幕末到明治維新前後脈絡發言，避免過度預知後世國家發展。","deliberate_error_enabled":false}'::jsonb,
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
      '{"voice":"開放、務實，重視制度轉型、海權、商業與不同政治勢力之間的協商。","knowledge_boundary":"以幕末到明治維新前後脈絡發言，避免過度預知後世國家發展。","deliberate_error_enabled":false}'::jsonb,
      true,
      0,
      'teacher_modified'
    )
    RETURNING id INTO v_persona_id;
  END IF;

  UPDATE event_tasks
  SET
    story_text = '1853 年，美國海軍准將培里率領黑船進入浦賀附近海域，要求德川幕府開港。一名站在江戶灣岸邊的第三方觀察者，可能看見蒸汽軍艦、砲口、幕府官員、沿岸民眾與各藩武士同時面對陌生的軍事與外交壓力。1854 年《神奈川條約》使日本開港，後續通商條約又激化尊王攘夷、開國、倒幕與改革等爭論。從黑船來航到 1868 年明治維新，歷史變化並不是單純由外國船艦造成，也不是單純由少數英雄推動，而是外部壓力、幕府權威下降、藩政改革、思想動員、內戰與制度重組共同作用。',
    display_text = '1853 年，美國海軍准將{{blank:b01}}率領黑船進入浦賀附近海域，要求德川幕府開港。一名站在江戶灣岸邊的第三方觀察者，可能看見{{blank:b02}}、砲口、幕府官員、沿岸民眾與各藩武士同時面對陌生的軍事與外交壓力。1854 年{{blank:b03}}使日本開港，後續通商條約又激化尊王攘夷、開國、倒幕與改革等爭論。研究者若要判斷證據，應比較{{blank:b04}}；若要分析延續與變遷，則要注意幕府權威下降、各藩改革、內戰與中央集權如何相互連動。若有人主張明治維新只是日本主動走向現代化，與外部壓力、內部衝突和普通民眾負擔無關，這個判斷是{{blank:b05}}。',
    evaluation_payload = '{"rubric":"評估學生是否能從歷史重要性、證據、延續與變遷、原因與後果、歷史觀點取替、倫理維度六個面向理解黑船事件到明治維新的轉型，而不是把它簡化為外國逼迫或日本自動現代化。","target_misconceptions":["把明治維新看成單純成功現代化故事","忽略黑船來航與不平等條約的外部壓力","忽略幕末內戰與社會成本","把改革只歸功於少數英雄人物"],"questions":[{"id":"b01","blank_id":"b01","type":"cloze","prompt":"請填入 1853 年率領黑船來航的美國海軍准將。","placeholder":"請輸入人物","required":true,"correct_answer":"培里","source_text":"培里","explanation":"人事時地物中的人，同時標示事件的重要觸發點。"},{"id":"b02","blank_id":"b02","type":"cloze","prompt":"請填入事件中最具象徵性的物件。","placeholder":"請輸入物件","required":true,"correct_answer":"蒸汽軍艦","source_text":"蒸汽軍艦","explanation":"人事時地物中的物，也連到軍事科技與外壓。"},{"id":"b03","blank_id":"b03","type":"cloze","prompt":"請填入 1854 年日本與美國簽訂的開港條約。","placeholder":"請輸入條約","required":true,"correct_answer":"神奈川條約","source_text":"神奈川條約","explanation":"對應 historical significance 與 continuity/change。"},{"id":"b04","blank_id":"b04","type":"multiple_choice","prompt":"研究者比較黑船到明治維新證據時，哪一組材料最合適？","required":true,"options":[{"id":"a","label":"條約文本、幕府文書、藩士日記與外國觀察","value":"條約文本、幕府文書、藩士日記與外國觀察"},{"id":"b","label":"只看明治政府後來的宣傳","value":"只看明治政府後來的宣傳"},{"id":"c","label":"只看外國軍艦紀錄","value":"只看外國軍艦紀錄"}],"correct_answer":"條約文本、幕府文書、藩士日記與外國觀察","source_text":"條約文本、幕府文書、藩士日記與外國觀察","explanation":"對應 evidence，避免單一來源支配敘事。"},{"id":"b05","blank_id":"b05","type":"true_false","prompt":"明治維新只是日本主動走向現代化，與外部壓力、內部衝突和普通民眾負擔無關。","required":true,"correct_answer":false,"source_text":"錯誤","explanation":"對應 cause/consequence、historical perspectives 與 ethical dimension。"}]}'::jsonb,
    revision_state = 'teacher_modified',
    updated_at = now()
  WHERE event_id = v_event_id AND title = '黑船事件到明治維新：外壓、內戰與制度重組'
  RETURNING id INTO v_task_id;

  IF v_task_id IS NULL THEN
    INSERT INTO event_tasks (
      event_id,
      title,
      story_text,
      display_text,
      evaluation_payload,
      revision_state
    )
    VALUES (
      v_event_id,
      '黑船事件到明治維新：外壓、內戰與制度重組',
      '1853 年，美國海軍准將培里率領黑船進入浦賀附近海域，要求德川幕府開港。一名站在江戶灣岸邊的第三方觀察者，可能看見蒸汽軍艦、砲口、幕府官員、沿岸民眾與各藩武士同時面對陌生的軍事與外交壓力。1854 年《神奈川條約》使日本開港，後續通商條約又激化尊王攘夷、開國、倒幕與改革等爭論。從黑船來航到 1868 年明治維新，歷史變化並不是單純由外國船艦造成，也不是單純由少數英雄推動，而是外部壓力、幕府權威下降、藩政改革、思想動員、內戰與制度重組共同作用。',
      '1853 年，美國海軍准將{{blank:b01}}率領黑船進入浦賀附近海域，要求德川幕府開港。一名站在江戶灣岸邊的第三方觀察者，可能看見{{blank:b02}}、砲口、幕府官員、沿岸民眾與各藩武士同時面對陌生的軍事與外交壓力。1854 年{{blank:b03}}使日本開港，後續通商條約又激化尊王攘夷、開國、倒幕與改革等爭論。研究者若要判斷證據，應比較{{blank:b04}}；若要分析延續與變遷，則要注意幕府權威下降、各藩改革、內戰與中央集權如何相互連動。若有人主張明治維新只是日本主動走向現代化，與外部壓力、內部衝突和普通民眾負擔無關，這個判斷是{{blank:b05}}。',
      '{"rubric":"評估學生是否能從歷史重要性、證據、延續與變遷、原因與後果、歷史觀點取替、倫理維度六個面向理解黑船事件到明治維新的轉型，而不是把它簡化為外國逼迫或日本自動現代化。","target_misconceptions":["把明治維新看成單純成功現代化故事","忽略黑船來航與不平等條約的外部壓力","忽略幕末內戰與社會成本","把改革只歸功於少數英雄人物"],"questions":[{"id":"b01","blank_id":"b01","type":"cloze","prompt":"請填入 1853 年率領黑船來航的美國海軍准將。","placeholder":"請輸入人物","required":true,"correct_answer":"培里","source_text":"培里","explanation":"人事時地物中的人，同時標示事件的重要觸發點。"},{"id":"b02","blank_id":"b02","type":"cloze","prompt":"請填入事件中最具象徵性的物件。","placeholder":"請輸入物件","required":true,"correct_answer":"蒸汽軍艦","source_text":"蒸汽軍艦","explanation":"人事時地物中的物，也連到軍事科技與外壓。"},{"id":"b03","blank_id":"b03","type":"cloze","prompt":"請填入 1854 年日本與美國簽訂的開港條約。","placeholder":"請輸入條約","required":true,"correct_answer":"神奈川條約","source_text":"神奈川條約","explanation":"對應 historical significance 與 continuity/change。"},{"id":"b04","blank_id":"b04","type":"multiple_choice","prompt":"研究者比較黑船到明治維新證據時，哪一組材料最合適？","required":true,"options":[{"id":"a","label":"條約文本、幕府文書、藩士日記與外國觀察","value":"條約文本、幕府文書、藩士日記與外國觀察"},{"id":"b","label":"只看明治政府後來的宣傳","value":"只看明治政府後來的宣傳"},{"id":"c","label":"只看外國軍艦紀錄","value":"只看外國軍艦紀錄"}],"correct_answer":"條約文本、幕府文書、藩士日記與外國觀察","source_text":"條約文本、幕府文書、藩士日記與外國觀察","explanation":"對應 evidence，避免單一來源支配敘事。"},{"id":"b05","blank_id":"b05","type":"true_false","prompt":"明治維新只是日本主動走向現代化，與外部壓力、內部衝突和普通民眾負擔無關。","required":true,"correct_answer":false,"source_text":"錯誤","explanation":"對應 cause/consequence、historical perspectives 與 ethical dimension。"}]}'::jsonb,
      'teacher_modified'
    )
    RETURNING id INTO v_task_id;
  END IF;
END $$;
