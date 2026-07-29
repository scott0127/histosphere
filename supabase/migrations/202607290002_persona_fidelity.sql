-- 將既有預設人物改用可追溯的史料肖像，並補強人物語體。
-- 只覆蓋空值或舊版預設值，保留 Admin 已自訂的圖片與 speaking_style。
with persona_defaults(name, avatar_url, legacy_style, translated_style) as (
  values
    (
      '馬克西米連·羅伯斯比爾',
      '/images/personas/maximilien-robespierre.jpg',
      '嚴肅、論辯性強，重視共和德行與公共利益。',
      '使用可讀的繁體中文翻譯法國革命政治語體；正式、克制而具論辯性，常從公民、共和、德行、公共利益與政治責任辨析問題。句子可以堅定但不可像現代教師講課，不模仿後世宣傳，也不捏造本人名言。'
    ),
    (
      '莫那·魯道',
      '/images/personas/mona-rudao.jpg',
      '沉著、嚴肅，重視族群尊嚴、殖民壓迫與歷史脈絡。',
      '使用可讀的繁體中文作為翻譯語體；句子短而直接，少用學術分類與抽象口號，從族人、土地、勞役、警察權力、尊嚴與行動後果說話。語氣克制而堅定，不像教師講課；不得捏造賽德克語原句或把後世概念說成當時用語。'
    ),
    (
      '林則徐',
      '/images/personas/lin-zexu.jpg',
      '謹慎、重視制度與道德責任，會強調禁煙、國家主權與官員職責。',
      '使用可讀的繁體中文翻譯清代官員語體；持重、簡練，先辨法度、職責、利害與民生，再談禁煙及對外關係。不堆砌文言、不冒充奏摺原文，也不使用現代教師或政策系統話術。'
    ),
    (
      '坂本龍馬',
      '/images/personas/sakamoto-ryoma.jpg',
      '開放、務實，重視制度轉型、海權、商業與不同政治勢力之間的協商。',
      '使用可讀的繁體中文翻譯幕末人物語體；直率、務實並帶商議感，常從海路、貿易、藩與幕府、政治協調及避免內戰談問題。不套用現代管理術語，不捏造土佐方言或後世流傳名言。'
    )
)
update public.personas as persona
set
  avatar_url = case
    when coalesce(persona.avatar_url, '') in (
      '',
      replace(defaults.avatar_url, '.jpg', '.png')
    ) then defaults.avatar_url
    else persona.avatar_url
  end,
  prompt_profile = case
    when coalesce(persona.prompt_profile ->> 'speaking_style', '') in ('', defaults.legacy_style)
      then jsonb_set(
        coalesce(persona.prompt_profile, '{}'::jsonb),
        '{speaking_style}',
        to_jsonb(defaults.translated_style),
        true
      )
    else persona.prompt_profile
  end,
  updated_at = now()
from persona_defaults as defaults
where persona.name = defaults.name;
