-- Source-checked content revision. Add task versions; retain all existing task/answer/session records.
-- source_sha256: bb68de734854d7592ea160826de1cbecb77b7e7be6e2d1bf08b9f8f09e96f34a
DO $do$
DECLARE
  v_changes JSONB := $json${
  "version": "reading-materials-20260917-v5",
  "events": [
    {
      "canonical_name": "黑船事件到明治維新",
      "description": "1853 年，美國海軍將領培里率艦抵達浦賀，要求日本接受美國總統關於交往與通商的國書。幕府於 1854 年簽訂《神奈川條約》，開放下田、箱館供美國船隻停泊及補給；1858 年《日美修好通商條約》進一步規定通商口岸、領事裁判權與協定關稅。對外關係的變化，也使幕府、朝廷與各藩對國家決策權的爭論加劇。1867 年德川慶喜大政奉還後，新的權力安排仍未確定，坂本龍馬、西周等人提出不同的政體構想。1868 年以朝廷為中心的新政府成立，隨後與舊幕府勢力發生戊辰戰爭。維新改革並未在這一年全部完成：例如廢藩置縣於 1871 年實施，中央政府才進一步取代各藩的地方統治。",
      "context": "本事件聚焦 1853 年黑船來航至 1868 年新政府成立之間的開國與政權重組。題組材料集中在 1867 年的政體草案；後來的新政府制度與 1871 年廢藩置縣屬後續發展。",
      "personas": [
        {
          "name": "坂本龍馬",
          "biography": "坂本龍馬出身土佐，脫藩後追隨勝海舟，接觸海軍與航海事業。1865 年在長崎成立龜山社中，後發展為海援隊，從事貿易與運輸。他參與促成 1866 年薩長同盟，並在 1867 年與土佐藩的後藤象二郎商議大政奉還及新政體構想，留下《新政府綱領八策》。",
          "sources": [
            {
              "title": "坂本竜馬｜近代日本人の肖像",
              "url": "https://www.ndl.go.jp/portrait/datas/89",
              "organization": "日本國立國會圖書館"
            },
            {
              "title": "坂本龍馬の政体構想",
              "url": "https://www.ndl.go.jp/modern/cha1/description02.html",
              "organization": "日本國立國會圖書館"
            },
            {
              "title": "新政府綱領八策：史料釋文",
              "url": "https://www.ndl.go.jp/modern/img_t/M011/M011-001tx.html",
              "organization": "日本國立國會圖書館"
            }
          ],
          "prompt_profile": {
            "event_timepoint": "1867 年大政奉還後、本人遇刺前的幕末政局（公曆 1867 年 12 月 10 日以前）",
            "temporal_boundary": "以大政奉還後、1867 年 12 月 10 日遇刺前的可知資訊發言，不得預知本人遇刺、1868 年新政府成立與戊辰戰爭，或後來的維新改革結果。西周草案只能依使用者當次提供的材料內容討論；不得聲稱曾收到、讀過該草案，或與西周討論過它。",
            "knowledge_boundary": "以人物經歷、往來書信與政治商業網絡可合理得知的資訊為限。區分所提供材料的內容與個人記憶，不把館方後設解說當成親身見聞。《新政府綱領八策》伏字所指人物並無定論，不得斷言龍馬已排除德川慶喜或確定指定山內容堂。"
          },
          "expertise_areas": [
            "幕末政治",
            "土佐藩",
            "海援隊",
            "薩長同盟",
            "大政奉還",
            "政體構想"
          ]
        }
      ],
      "start_year": 1853,
      "end_year": 1868,
      "century": 19,
      "content_review": {
        "version": "reading-materials-20260917-v5",
        "checked_at": "2026-09-17",
        "status": "source_checked_pending_researcher_review",
        "sources": [
          "https://www.ndl.go.jp/modern/e/cha1/description01.html",
          "https://www.ndl.go.jp/modern/cha1/description02.html",
          "https://www.ndl.go.jp/modern/img_t/M011/M011-001tx.html",
          "https://www.ndl.go.jp/modern/cha1/description03.html",
          "https://www.ndl.go.jp/modern/img_t/003/003-001tx.html",
          "https://www.archives.go.jp/exhibition/digital/bakumatsu/contents/20.html",
          "https://www.archives.go.jp/ayumi/kobetsu/m01_1868_01.html",
          "https://www.archives.go.jp/exhibition/digital/modean_state/contents/return/index.html",
          "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第二冊/第二冊第五章"
        ],
        "curriculum_reference": {
          "publisher": "三民書局",
          "curriculum": "108 課綱普通型高中歷史",
          "scope": "公開自學教材相關頁面；頁碼依本次下載版本，不推定等於所有學年度的版本。",
          "volume": 2,
          "chapter": "第5章 傳統與現代的交會",
          "section": "第1節 東亞國家對西力衝擊的回應",
          "pages": [
            124,
            125,
            126
          ],
          "source_url": "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第二冊/第二冊第五章",
          "pdf_url": "https://drive.google.com/file/d/1Ss_YUEauXuV86XHAZZbYqWXFdNaqR7Rw/view"
        },
        "note": "課本作課程範圍與基本脈絡對照；具體文件、圖像與年代另與所列典藏來源互校。"
      }
    },
    {
      "canonical_name": "霧社事件",
      "description": "1930 年 10 月 27 日，霧社地區的賽德克族馬赫坡社等六社族人，以莫那·魯道為重要領導者，攻擊警察駐在所及霧社公學校運動會上的日本人，造成嚴重傷亡。事件發生於日本殖民統治下，與長期的警察管控、繁重勞役及部落生活受到的衝擊有關。日本軍警隨後展開鎮壓，起事部落死傷慘重。1931 年 4 月，日方利用部落對立，收容中的倖存者再遭敵對部落襲擊，史稱第二次霧社事件；同年 5 月，日方將六社餘生者強制遷往川中島，也就是今日的清流部落。",
      "start_year": 1930,
      "end_year": 1931,
      "context": "日治時期臺灣山地的警察管控與勞役，1930 年霧社地區六社起事及軍警鎮壓，以及 1931 年第二次霧社事件與川中島強制遷移。",
      "personas": [
        {
          "name": "莫那·魯道",
          "biography": "莫那·魯道是霧社地區賽德克族馬赫坡社領袖，也是 1930 年霧社事件的重要領導者。當時部落長期承受警察管控與繁重勞役，他與其他起事部落族人投入抗日行動。本活動將角色設定在 1930 年 10 月事件爆發期間。",
          "sources": [
            {
              "url": "https://collections.nmth.gov.tw/CollectionContent.aspx?a=132&rno=2017.025.0196.0039"
            },
            {
              "url": "https://collections.nmth.gov.tw/CollectionContent.aspx?a=132&rno=2017.025.0187.0036"
            },
            {
              "url": "https://www.th.gov.tw/EpaperSend/113/75/"
            }
          ],
          "prompt_profile": {}
        }
      ],
      "century": 20,
      "content_review": {
        "version": "reading-materials-20260917-v5",
        "checked_at": "2026-09-17",
        "status": "source_checked_pending_researcher_review",
        "sources": [
          "https://gpi.culture.tw/books/1009903033",
          "https://collections.nmth.gov.tw/CollectionContent.aspx?a=132&rno=2017.025.0196.0039",
          "https://dl.lib.ntu.edu.tw/s/photo/item/103879",
          "https://dl.lib.ntu.edu.tw/s/photo/item?Search=&property%5B0%5D%5Bproperty%5D=33&property%5B0%5D%5Btext%5D=2014960&property%5B0%5D%5Btype%5D=eq",
          "https://commons.wikimedia.org/wiki/File:In_front_of_Musha_Headquarters,_sorting_out_luggage_for_the_3rd_Battalion%27s_full-term_discharge_corps_circa_1930.jpg",
          "https://www.nantou.gov.tw/upload/142126_5.pdf",
          "https://www.th.gov.tw/EpaperSend/113/75/",
          "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第一冊/第一冊序篇-第一章"
        ],
        "curriculum_reference": {
          "publisher": "三民書局",
          "curriculum": "108 課綱普通型高中歷史",
          "scope": "公開自學教材相關頁面；頁碼依本次下載版本，不推定等於所有學年度的版本。",
          "volume": 1,
          "chapter": "第1章 臺灣最早的住民",
          "pages": [
            28,
            29
          ],
          "source_url": "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第一冊/第一冊序篇-第一章",
          "pdf_url": "https://drive.google.com/file/d/1aNdbDVYlD5y4xVcPeLlLGXBCYk7MsxAA/view"
        },
        "note": "課本作課程範圍與基本脈絡對照；具體文件、圖像與年代另與所列典藏來源互校。"
      }
    },
    {
      "canonical_name": "鴉片戰爭",
      "description": "本事件從 1839 年的禁煙衝突談起，介紹清朝與英國之間的第一次鴉片戰爭。十九世紀前期，英國商人將印度鴉片走私到中國，鴉片消費與白銀外流引起清廷關切。1839 年，林則徐奉命赴廣東禁煙，並在虎門銷毀收繳的鴉片。1840 年，英國派遣遠征軍來華，戰事從沿海延伸至長江流域。清朝戰敗後，於 1842 年 8 月 29 日與英國簽訂《南京條約》，割讓香港島、開放廣州等五處通商口岸、支付賠款，並取消英商只能透過特許行商交易的限制。這些安排改變了清朝的對外通商制度。",
      "context": "清廷的禁煙政策與英國商人的鴉片貿易利益發生衝突。1839 年林則徐在廣東禁煙；1840 年英國遠征軍來華；1842 年清英簽訂《南京條約》。條約第二款限定英商居住經商的五處口岸，第五款取消只能透過特許行商交易的限制，第十款涉及通商口岸的進出口稅則。1842 年條約沒有直接把鴉片貿易合法化，也不能由條約推定各地實際執行情況。本題材料比較禁煙書信中的要求與戰後條約中的正式約定。",
      "start_year": 1839,
      "end_year": 1842,
      "personas": [
        {
          "name": "林則徐",
          "biography": "林則徐是清朝官員。1839 年，他以欽差大臣身分前往廣東查禁鴉片，要求外商交出鴉片，並主持虎門銷煙。他透過書信與告示表達禁煙立場，主張來華商人應遵守清朝法律，並要求英國君主約束販運鴉片的商人。",
          "expertise_areas": [
            "廣東禁煙",
            "虎門銷煙",
            "清朝官員職責",
            "對外貿易與交涉"
          ],
          "sources": [
            {
              "url": "https://ccnmtl.columbia.edu/services/dropoff/china_civ_temp/week11/pdfs/comiss.pdf"
            },
            {
              "url": "https://www.yearbook.gov.hk/2002/ehtml/e21-02.htm"
            }
          ],
          "prompt_profile": {}
        }
      ],
      "century": 19,
      "content_review": {
        "version": "reading-materials-20260917-v5",
        "checked_at": "2026-09-17",
        "status": "source_checked_pending_researcher_review",
        "sources": [
          "https://www.yearbook.gov.hk/2002/ehtml/e21-02.htm",
          "https://afe.easia.columbia.edu/ps/china/nanjing.pdf",
          "https://ccnmtl.columbia.edu/services/dropoff/china_civ_temp/week11/pdfs/comiss.pdf",
          "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第二冊/第二冊第五章"
        ],
        "curriculum_reference": {
          "publisher": "三民書局",
          "curriculum": "108 課綱普通型高中歷史",
          "scope": "公開自學教材相關頁面；頁碼依本次下載版本，不推定等於所有學年度的版本。",
          "volume": 2,
          "chapter": "第5章 傳統與現代的交會",
          "section": "第1節 東亞國家對西力衝擊的回應",
          "pages": [
            119,
            120
          ],
          "source_url": "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第二冊/第二冊第五章",
          "pdf_url": "https://drive.google.com/file/d/1Ss_YUEauXuV86XHAZZbYqWXFdNaqR7Rw/view"
        },
        "note": "課本作課程範圍與基本脈絡對照；具體文件、圖像與年代另與所列典藏來源互校。"
      }
    },
    {
      "canonical_name": "法國大革命",
      "description": "法國大革命通常指 1789 至 1799 年間法國政治與社會制度的劇烈變動。面對財政危機與代表權爭議，路易十六於 1789 年召開三級會議。第三等級代表與部分教士成立國民議會，並在網球場宣誓繼續集會、制定憲法。同年，《人權和公民權宣言》提出自由、法律平等與國民主權等原則。法國先建立君主立憲政體，1792 年廢除君主制度，進入共和時期；其間也發生對外戰爭、派系衝突與恐怖統治。1799 年，拿破崙透過霧月政變推翻督政府，建立執政府。本活動聚焦革命初期的宣誓紀錄與後來描繪這場宣誓的畫稿。",
      "context": "1789 年，財政危機與代表權爭議促成三級會議及國民議會的政治轉變。6 月 17 日第三等級代表與部分教士成立國民議會；6 月 20 日代表在網球場宣誓，承諾憲法未建立於穩固基礎前不解散。這次宣誓不是當天已公布憲法或廢除君主制度。大衛沒有在現場見證宣誓，他於 1791 年公開展示的預備畫稿，是事後蒐集資料並安排構圖的作品；它與未完成的大型油畫及 1883 年梅爾松的複製畫不同。",
      "start_year": 1789,
      "end_year": 1799,
      "personas": [
        {
          "name": "馬克西米連·羅伯斯比爾",
          "biography": "羅伯斯比爾原為律師，1789 年以第三等級代表身分參與三級會議，之後成為雅各賓派的重要人物與國民公會代表。他主張共和政體、公民權利與公共利益，並參與革命政府在戰爭及內部衝突下的政治決策。其革命防衛主張與政治暴力的關係，也成為後世持續討論的問題。",
          "sources": [
            {
              "url": "https://www2.assemblee-nationale.fr/sycomore/fiche?num_dept=11798"
            },
            {
              "url": "https://www2.assemblee-nationale.fr/decouvrir-l-assemblee/histoire/grands-discours-parlementaires/robespierre-10-mai-1793"
            }
          ],
          "prompt_profile": {}
        }
      ],
      "century": 18,
      "content_review": {
        "version": "reading-materials-20260917-v5",
        "checked_at": "2026-09-17",
        "status": "source_checked_pending_researcher_review",
        "sources": [
          "https://www.assemblee-nationale.fr/dyn/histoire-et-patrimoine/revolution-francaise/assemblee-nationale-constituante",
          "https://qpc360.conseil-constitutionnel.fr/bloc-constitutionnalite",
          "https://www.assemblee-nationale.fr/dyn/histoire-et-patrimoine/revolution-francaise/la-convention-nationale-et-la-fin-de-la-royaute",
          "https://www.assemblee-nationale.fr/dyn/histoire-et-patrimoine/revolution-francaise/le-coup-d-etat-des-18-et-19-brumaire-an-viii",
          "https://en.chateauversailles.fr/sites/default/files/presse/documents/cp_restauration_jeu_de_paume_en.pdf",
          "https://en.chateauversailles.fr/discover/history/key-dates/jeu-paume-oath-1789",
          "https://commons.wikimedia.org/wiki/File:Le_Serment_du_Jeu_de_paume.jpg",
          "https://sites.google.com/view/sanminhistorybook110/首頁/第二章"
        ],
        "curriculum_reference": {
          "publisher": "三民書局",
          "curriculum": "108 課綱普通型高中歷史",
          "scope": "公開自學教材相關頁面；頁碼依本次下載版本，不推定等於所有學年度的版本。",
          "volume": 3,
          "chapter": "第2章 歐洲自由與民主的發展",
          "section": "第2節 十八、十九世紀政治與經濟的新思維",
          "pages": [
            54,
            55
          ],
          "source_url": "https://sites.google.com/view/sanminhistorybook110/首頁/第二章",
          "pdf_url": "https://drive.google.com/file/d/1wMTa7g2J7SuHZXElY-cXduQdLQSGtVXO/view"
        },
        "note": "課本作課程範圍與基本脈絡對照；具體文件、圖像與年代另與所列典藏來源互校。"
      }
    }
  ],
  "tasks": [
    {
      "event_name": "黑船事件到明治維新",
      "title": "黑船事件到明治維新：新政體應由誰作主？",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "某展覽準備介紹黑船來航後，日本出現的政體構想。你負責比較坂本龍馬與西周的主張，根據下方兩則材料撰寫展覽說明。\n\nQ01｜若要替兩份構想寫一句共同的展覽說明，下列哪一項最符合材料？\n{{blank:q01}}\n\nQ02｜有人說：「兩份材料可以顯示當時有人構想設立議事機構，但不能僅憑這些構想，就認定日本人民當時已普遍取得選舉權。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果展覽要介紹「引進新的權力分工，同時維持德川家政治中心地位」的構想，應以誰的方案為主要材料？填入材料中的人名，並在理由中說明你的判斷依據。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "japan_ryoma_plan",
            "title": "坂本龍馬的《新政府綱領八策》",
            "caption": "1867 年（慶應三年舊曆十一月）的政體草案。以下為典藏文件與館方解說的中文內容摘要。",
            "text": "1853 年培里率艦來航後，幕府將美國總統國書及相關文件交給多位大名徵詢意見。此後，對外開放與由誰參與國家決策，成為幕末政治中的重要問題。\n\n1867 年，坂本龍馬與土佐藩的後藤象二郎商議政局，支持大政奉還。他留下的《新政府綱領八策》提出招攬人才擔任顧問、任用有才幹的諸侯、設置上下議政所，以及外交、法規和海陸軍等改革項目。\n\n草案末段提到由一名盟主把方案呈交朝廷，但人名以伏字代替。館方指出，這個人可能是山內容堂或德川慶喜等人，目前仍無定論。這份材料留下了龍馬對新政府的規劃，但沒有逐項交代議事成員如何產生。",
            "source_url": "https://www.ndl.go.jp/modern/cha1/description02.html",
            "attribution": "日本國立國會圖書館《史料にみる日本の近代》1-1、1-2及《新政府綱領八策》釋文；研究者中文改寫。"
          },
          {
            "id": "japan_nishi_plan",
            "title": "西周的《議題草案》與《別紙議題草案》",
            "caption": "館方繫年為 1867 年（慶應三年舊曆十一月）。以下為典藏文件與館方解說的中文內容摘要。",
            "text": "幕府開成所教授西周向德川慶喜的側近平山敬忠提交《議題草案》，討論大政奉還後的會議制度；《別紙議題草案》則進一步規劃以德川家為中心的政體。\n\n這套方案參考西方的權力分工：全國行政由將軍掌握，立法交給議政院，司法暫由各藩負責。議政院的上院由大名組成，下院則由各藩藩主選派一名藩士。天皇保留法律的形式批准等權能，但不負責日常行政；館方因此將其概括為象徵性地位。\n\n西周把這些安排寫成草案，作為當時政權重組的提案。展覽中的中文材料整理了他的構想，並未提供該制度實際運作的紀錄。",
            "source_url": "https://www.ndl.go.jp/modern/cha1/description03.html",
            "attribution": "日本國立國會圖書館《史料にみる日本の近代》1-3及《別紙議題草案》釋文；研究者中文改寫。展覽情境為本題組設定。"
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
                "label": "兩者都討論議事機構，但對政治權力如何安排各有構想。",
                "value": "A"
              },
              {
                "id": "b",
                "label": "兩者都主張保留將軍掌握行政，並讓天皇只有象徵性地位。",
                "value": "B"
              },
              {
                "id": "c",
                "label": "兩者只處理對外通商，不涉及日本內部的決策制度。",
                "value": "C"
              },
              {
                "id": "d",
                "label": "兩者記錄了同一套已完成實施的全國選舉制度。",
                "value": "D"
              }
            ],
            "correct_answer": "A",
            "source_text": "兩份草案都涉及議事機構；龍馬列出人才任用與多項改革，西周更具體分配將軍、議政院及各藩的權力。龍馬草案中的盟主人名是伏字，不能據此斷言其方案完全排除德川家。",
            "accepted_evidence_ids": [
              "japan_ryoma_plan",
              "japan_nishi_plan"
            ],
            "reasoning_criteria": "通過：指出兩者都提出議事機構，並以兩份材料的內容說明方案不完全相同，例如龍馬列舉人才任用與多項改革、西周具體劃分將軍、議政院及各藩的權力。也接受指出無法從伏字確定龍馬所指的盟主人選，而西周明確以德川家為中心。不要求專有術語或列出全部分工。不通過：只複述選項而未連結材料、斷言龍馬排除德川慶喜、把兩份方案說成完全相同，或把草案當成已實行的普選。"
          },
          {
            "id": "q02",
            "type": "true_false",
            "required": true,
            "correct_answer": true,
            "source_text": "材料介紹的是政體草案。龍馬草案未逐項規定議事成員產生方式；西周列明大名與各藩藩士等參與者，不是全體居民直接選出。",
            "accepted_evidence_ids": [
              "japan_ryoma_plan",
              "japan_nishi_plan"
            ],
            "reasoning_criteria": "通過：區分政體提案與已實施的制度，或指出參與者有限而不能等同普遍選舉權，並用草案性質、龍馬未交代議事成員產生方式、西周的成員安排等至少一項材料資訊支持。不要求主張當時所有人都沒有政治參與機會。不通過：只說資料不夠而無材料依據，或把議事機構直接等同普選。"
          },
          {
            "id": "q03",
            "type": "cloze",
            "required": true,
            "correct_answer": [
              "西周",
              "西周的方案",
              "西周的政體構想",
              "Nishi Amane"
            ],
            "source_text": "西周方案參考權力分工，同時把行政權交給將軍，以德川家為政治中心。",
            "accepted_evidence_ids": [
              "japan_nishi_plan"
            ],
            "reasoning_criteria": "通過：把新權力分工或議事機構，與將軍掌行政或德川家居政治中心這兩面連結起來。不必列完行政、立法與司法，也不要求任何專門術語。不通過：只因西周學過西洋知識就下結論、只重複人名，或誤稱其主張廢除德川政治權力。"
          }
        ],
        "all_correct_fallback": {
          "id": "japan_plans_equal_elections",
          "evidence_ids": [
            "japan_ryoma_plan",
            "japan_nishi_plan"
          ],
          "incorrect_claim": "只要政體草案提出設立議事機構，就足以證明當時所有日本人已經能投票決定國家政策。",
          "correct_interpretation": "提出議事機構不等於全民選舉已實施；需區分草案與實施，並核對誰有參與資格。西周草案所列議事成員是大名和各藩武士。",
          "source_text": "本文的兩份政體構想及其性質；尤其西周方案的參與者與權力分工。"
        },
        "authoring": {
          "method": "researcher_curated_with_ai_assistance",
          "version": "reading-materials-20260917-v5",
          "review_status": "awaiting_researcher_acceptance",
          "sources": [
            "https://www.ndl.go.jp/modern/e/cha1/description01.html",
            "https://www.ndl.go.jp/modern/cha1/description02.html",
            "https://www.ndl.go.jp/modern/img_t/M011/M011-001tx.html",
            "https://www.ndl.go.jp/modern/cha1/description03.html",
            "https://www.ndl.go.jp/modern/img_t/003/003-001tx.html"
          ],
          "note": "材料是依典藏史料釋文及館方解說編寫的中文閱讀材料，不是原件全文或人物逐字發言。以現存《新政府綱領八策》為依據，不將其與傳稱《船中八策》混為同一文件。龍馬草案盟主伏字所指人物未定；不以『龍馬排除德川、相對於西周保留德川』作為答案必要條件。西周草案採館方舊曆繫年，不推定寫作日與龍馬遇刺的先後，也不得由龍馬聲稱親自讀過或收到該草案。內容已作來源核對，仍待研究者檢視難度與正式使用適切性，不宣稱與其他事件等值。",
          "fact_check": {
            "checked_at": "2026-09-17",
            "method": "source_cross_check_with_public_textbook_reference",
            "status": "source_checked_pending_researcher_review",
            "note": "已交叉查核所列來源；不是史學專家簽核，也不代表題目難度或測量效度已驗證。"
          },
          "curriculum_reference": {
            "publisher": "三民書局",
            "curriculum": "108 課綱普通型高中歷史",
            "scope": "公開自學教材相關頁面；頁碼依本次下載版本，不推定等於所有學年度的版本。",
            "volume": 2,
            "chapter": "第5章 傳統與現代的交會",
            "section": "第1節 東亞國家對西力衝擊的回應",
            "pages": [
              124,
              125,
              126
            ],
            "source_url": "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第二冊/第二冊第五章",
            "pdf_url": "https://drive.google.com/file/d/1Ss_YUEauXuV86XHAZZbYqWXFdNaqR7Rw/view"
          }
        }
      }
    },
    {
      "event_name": "鴉片戰爭",
      "title": "鴉片戰爭：一封禁煙書信與一份戰後條約",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "一個歷史展覽要呈現第一次鴉片戰爭前後，清朝與英國之間的交涉。策展人準備並列展出林則徐的禁煙書信與《南京條約》的內容整理，請你協助撰寫解說。\n\nQ01｜若要替林則徐書信中的論證方式撰寫說明，下列哪一項最適當？\n{{blank:q01}}\n\nQ02｜有人根據《南京條約》關於交易對象的規定，宣稱：「條約簽訂後，英商已可到中國任何地方自由居住和經商。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果要查核「戰後清朝正式承諾如何改變英商的交易制度」，應優先閱讀本文中的哪一份文件？請填文件名稱，並說明它為何比另一份更適合回答這個問題。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "opium_lin_letter",
            "title": "1839 年林則徐致英國君主的禁煙書信（內容整理）",
            "caption": "1839 年林則徐在廣東禁煙時擬寫，要求英國君主約束鴉片商人。以下為書信內容整理。",
            "text": "1839 年，林則徐在廣東處理禁煙事務，擬寫了一封面向英國君主的書信。信中指責部分商人為追求利益，將鴉片運入中國。他把中國輸出的茶、絲等貨品描述為有益的商品，反問英商既能由這些貿易獲利，為何仍販售傷人的鴉片。\n\n接著，他請對方設想：假如有人把鴉片帶到英國，使當地人民購買、吸食，英國君主會如何看待？他藉此要求對方阻止鴉片販運，並主張來華經商者應遵守中國法律。以上是林則徐在信中的立場與說服方式；現存信件本身不能證明英國君主已閱讀或接受他的要求。",
            "source_url": "https://ccnmtl.columbia.edu/services/dropoff/china_civ_temp/week11/pdfs/comiss.pdf",
            "attribution": "依 Columbia University 收錄的林則徐禁煙書信英譯本第 2–4 頁中文改寫。譯本所據為 Ssu-yu Teng、John K. Fairbank 編《China's Response to the West》（1954）；非信件原件或逐字中譯。"
          },
          {
            "id": "opium_nanjing_treaty",
            "title": "1842 年《南京條約》的通商規定（條文整理）",
            "caption": "清英於 1842 年 8 月 29 日簽訂《南京條約》。下文整理第二、第五款與英商居住口岸及交易對象有關的內容。",
            "text": "清朝戰敗後，與英國於 1842 年簽訂《南京條約》。第二款列出廣州、廈門、福州、寧波與上海，允許英國商民及其家屬在這些城市居住、從事商業活動，並由英國派駐領事等官員。\n\n第五款提到，英商在廣州原先須透過清政府特許的行商交易。條約約定，往後在准許英商居住的口岸，取消只能與這些行商交易的限制，讓英商自行選擇交易對象。這兩款分別規範居住經商的地點與交易對象；它們是戰後的正式約定，並不是各地日常交易或執行情況的紀錄。",
            "source_url": "https://afe.easia.columbia.edu/ps/china/nanjing.pdf",
            "attribution": "依 Columbia University, Asia for Educators《南京條約》節錄第 1–2 頁第二、第五款中文改寫。此處只整理選定條款，並非條約全文。"
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
                "label": "以戰後條約的權利，要求英商擴大鴉片貿易。",
                "value": "A"
              },
              {
                "id": "b",
                "label": "以英國君主的回信，證明雙方已同意禁止鴉片。",
                "value": "B"
              },
              {
                "id": "c",
                "label": "把所有中外交易都視為有害，主張拒絕一切商品。",
                "value": "C"
              },
              {
                "id": "d",
                "label": "對比貿易的利益與鴉片的危害，要求對方設想本國遭受同樣傷害。",
                "value": "D"
              }
            ],
            "correct_answer": "D",
            "source_text": "林則徐對照茶絲貿易的利益與鴉片的危害，並假設鴉片被運入英國，藉此勸說英國君主約束商人。",
            "accepted_evidence_ids": [
              "opium_lin_letter"
            ],
            "reasoning_criteria": "通過：從信中指出有益貿易與鴉片傷害的對比，以及要求英國設想自己人民受害的意思，說明這些內容用來勸阻鴉片貿易。可用白話，不要求寫出換位思考或任何歷史思考術語。不通過：只評價林則徐愛國、只重複選項而不連結書信內容，或把勸說當成英方已同意。"
          },
          {
            "id": "q02",
            "type": "true_false",
            "required": true,
            "correct_answer": false,
            "source_text": "第二款列明五個城市；第五款的自由選擇交易對象限於准許英商居住的口岸，不能外推至中國任何地方。",
            "accepted_evidence_ids": [
              "opium_nanjing_treaty"
            ],
            "reasoning_criteria": "通過：區分可自行選交易對象與居住經商地點，指出條約只列五口或限定准許居住的口岸，故不足以推論全中國皆可。列出五個城市不是必要條件。不通過：只說條約不平等、英國很強勢，或把與任何人交易誤讀為在任何地方交易。"
          },
          {
            "id": "q03",
            "type": "cloze",
            "required": true,
            "correct_answer": [
              "南京條約",
              "《南京條約》",
              "南京條約的通商規定",
              "1842年南京條約",
              "1842年《南京條約》",
              "Treaty of Nanjing",
              "Treaty of Nanking"
            ],
            "source_text": "南京條約是戰後正式約定，包含英商居住城市及取消行商交易限制；林則徐書信表達戰前禁煙要求，不能替代戰後約定。",
            "accepted_evidence_ids": [
              "opium_lin_letter",
              "opium_nanjing_treaty"
            ],
            "reasoning_criteria": "通過：說明條約直接記載戰後正式承諾，例如五口或行商限制改變，並指出書信是戰前要求而非戰後協議。接受不逐字引用的等義說明。不通過：只因文件較新、官方文件必定完全正確，或認為條約足以證明每個地方的實際執行。"
          }
        ],
        "all_correct_fallback": {
          "id": "opium_request_equals_agreement",
          "evidence_ids": [
            "opium_lin_letter"
          ],
          "incorrect_claim": "林則徐的書信要求英國阻止鴉片輸入，所以這封信就能證明英國君主已接受禁煙要求。",
          "correct_interpretation": "書信可以顯示寫信者的要求與說服方式，但收信者是否閱讀、同意或採取行動，需要其他紀錄，不能由要求本身推定。",
          "source_text": "林則徐書信及其文件性質；寫信者的要求並非收信者的答覆。"
        },
        "authoring": {
          "method": "researcher_curated_with_ai_assistance",
          "version": "reading-materials-20260917-v5",
          "review_status": "awaiting_researcher_acceptance",
          "sources": [
            "https://ccnmtl.columbia.edu/services/dropoff/china_civ_temp/week11/pdfs/comiss.pdf",
            "https://afe.easia.columbia.edu/ps/china/nanjing.pdf"
          ],
          "note": "原創閱讀題組；內容依文件中文改寫，不是逐字翻譯。編製說明僅供研究者查看。只改寫核對過的文件段落，未複製來源教學問題；不將信件對英國的描述當作英國社會實況，也不宣稱南京條約使鴉片合法化。\n2026-09-17查核：題目答案維持D／false／南京條約。禁煙信英譯本導言有將南京條約誤述為鴉片合法化的敘述，未採用；是否送達或閱讀不可由信件本身推定。關稅第十款未直接訂出統一百分之五稅率，不把後續稅則或領事裁判權混寫為1842年第二、第五款內容。",
          "fact_check": {
            "checked_at": "2026-09-17",
            "method": "source_cross_check_with_public_textbook_reference",
            "status": "source_checked_pending_researcher_review",
            "note": "已交叉查核所列來源；不是史學專家簽核，也不代表題目難度或測量效度已驗證。"
          },
          "curriculum_reference": {
            "publisher": "三民書局",
            "curriculum": "108 課綱普通型高中歷史",
            "scope": "公開自學教材相關頁面；頁碼依本次下載版本，不推定等於所有學年度的版本。",
            "volume": 2,
            "chapter": "第5章 傳統與現代的交會",
            "section": "第1節 東亞國家對西力衝擊的回應",
            "pages": [
              119,
              120
            ],
            "source_url": "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第二冊/第二冊第五章",
            "pdf_url": "https://drive.google.com/file/d/1Ss_YUEauXuV86XHAZZbYqWXFdNaqR7Rw/view"
          }
        }
      }
    },
    {
      "event_name": "霧社事件",
      "title": "霧社事件：照片裡與照片外",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "校刊準備製作霧社事件專頁。編輯桌上放著一份軍事史料譯集的出版介紹，以及一張附有日文圖說的舊照片。有人想寫部隊的行動與物資安排，有人想談照片如何呈現事件，也有人想了解各部落居民在衝突中的生活。\n\n編輯必須先決定：現有材料能說明什麼？哪些研究還要繼續查找資料？請根據下方的出版介紹與歷史照片（含圖說），回答題目。\n\nQ01｜根據下方的材料介紹與照片，哪一項研究最需要補充其他人的紀錄或口述？\n{{blank:q01}}\n\nQ02｜有人說：「軍事紀錄的中文譯本在 2010 年出版，因此它不能包含日治時期軍方留下的紀錄。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果下一步要查找軍方物資供應的安排，應優先查閱介紹中提到的「軍事紀錄」，或先分析這張「攝影資料」？請填其中一項，並說明選擇的依據與限制。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "wushe_military_records",
            "title": "軍事紀錄介紹：2010 年出版的霧社事件史料譯集",
            "caption": "根據《霧社事件日文史料翻譯》的出版資料編寫。以下是收錄範圍的介紹，並非軍方日誌或給養紀錄原文。",
            "text": "1930 年 10 月 27 日，霧社地區馬赫坡社等六社的賽德克族人起事，日本軍警隨後進行鎮壓。軍方在事件期間留下部隊行動及物資供應等紀錄。\n\n《霧社事件日文史料翻譯》由國立臺灣歷史博物館於 2010 年出版。書中收錄《霧社事件陣中日誌》、《霧社事件關係陸軍大臣官房書類綴》及《昭和五年臺灣霧社事件給養史》等日文資料的中譯，也收錄春山明哲的解說。「昭和五年」相當於 1930 年；「給養」指軍隊所需糧食、物資等供應。\n\n編輯目前拿到的是這部譯集的出版介紹，尚未翻閱各份軍事文件全文。他先記下文件名稱，準備依研究問題進一步查閱。",
            "source_url": "https://gpi.culture.tw/books/1009903033",
            "attribution": "文化部 GPI 政府出版品資訊網《霧社事件日文史料翻譯》（GPN 1009903033；2010/09；國立臺灣歷史博物館）；背景另據臺史博〈霧社事件始末〉。正文為依出版介紹編寫的摘要，校刊編輯為虛構教學情境，未冒充軍方文件節錄。"
          },
          {
            "id": "wushe_photographic_records",
            "title": "霧社本部前整理行李的照片",
            "caption": "收錄於佐藤政藏編《第一第二霧社事件誌》（1931 年）。確切拍攝日期與攝影者尚未確認；1931 年是出版年份。",
            "image_url": "/images/materials/wushe-headquarters-1930.jpg",
            "text": "照片中可見穿制服的人、地上的行李與包裹，後方有建築物。這張照片收錄於佐藤政藏編輯的《第一第二霧社事件誌》，該書由實業時代社中部支社出版部於 1931 年出版。\n\n原書圖說（據臺大圖書館典藏書目）：\n「霧社本部前にて第三大隊の滿期除隊兵歸隊の為め荷物の整理中」\n圖說摘要：圖說提及第三大隊服役期滿的士兵，以及霧社本部前整理行李的情景。\n\n編輯打算在校刊上保留照片及圖說，再寫一段說明。目前這組攝影資料包含這張照片與原書圖說。",
            "source_url": "https://dl.lib.ntu.edu.tw/s/photo/item/103879",
            "attribution": "臺大圖書館臺灣舊照片資料庫，同名照片，出處《第一第二霧社事件誌》（1931）；本次以該書館藏清單及同書書目交叉核對。圖片檔沿用 Wikimedia Commons 公有領域版本，未改圖。日文為原圖說，中文為保守摘要而非逐字翻譯；不由『歸隊』自行推定具體退伍或返隊行政流程。"
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
                "label": "出版介紹列出的哪類軍事文件，可供下一步查找補給安排。",
                "value": "A"
              },
              {
                "id": "b",
                "label": "這張照片中可以看見哪些人物活動與物件。",
                "value": "B"
              },
              {
                "id": "c",
                "label": "不同部落居民如何理解衝突及生活變動。",
                "value": "C"
              },
              {
                "id": "d",
                "label": "這張照片的圖說如何介紹士兵與行李整理。",
                "value": "D"
              }
            ],
            "correct_answer": "C",
            "source_text": "目前提供的是軍事史料譯集的出版介紹，以及部隊整理行李的照片與圖說；兩者都沒有提供不同部落居民對自身經驗的完整敘述。要回答居民如何理解衝突及生活變動，需再補充相關紀錄或口述，並核對其背景與限制。",
            "accepted_evidence_ids": [
              "wushe_military_records",
              "wushe_photographic_records"
            ],
            "reasoning_criteria": "通過：指出現有介紹與照片偏向軍方活動，未提供不同部落居民對衝突與生活變動的敘述，因此需補充與居民經驗相關的材料。不必列出特定訪談人名，不把後來口述預設為必定正確。不通過：只說資料少而未連結研究問題，或因材料涉及軍方就認定全部內容都是假的。"
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
            "source_text": "出版介紹列出《昭和五年臺灣霧社事件給養史》等軍事文件，是下一步查找物資供應安排的較直接線索；目前提供的出版介紹與單張照片都不是完整補給紀錄。",
            "accepted_evidence_ids": [
              "wushe_military_records",
              "wushe_photographic_records"
            ],
            "reasoning_criteria": "通過：指出給養或後勤文件較直接對應物資供應問題，並說明至少一項限制，例如仍須查閱文件全文、軍方文件的記錄範圍受限、安排未必等於每次實際落實，或單張照片不能提供完整補給細節。不要求學習者已讀過未提供的文件全文。不通過：只說文字必定比照片可靠、軍方文件絕對真實，或未連結物資供應問題。"
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
          "version": "reading-materials-20260917-v5",
          "review_status": "awaiting_researcher_acceptance",
          "sources": [
            "https://gpi.culture.tw/books/1009903033",
            "https://collections.nmth.gov.tw/CollectionContent.aspx?a=132&rno=2017.025.0196.0039",
            "https://dl.lib.ntu.edu.tw/s/photo/item/103879",
            "https://dl.lib.ntu.edu.tw/s/photo/item?Search=&property%5B0%5D%5Bproperty%5D=33&property%5B0%5D%5Btext%5D=2014960&property%5B0%5D%5Btype%5D=eq",
            "https://commons.wikimedia.org/wiki/File:In_front_of_Musha_Headquarters,_sorting_out_luggage_for_the_3rd_Battalion%27s_full-term_discharge_corps_circa_1930.jpg"
          ],
          "image_provenance": {
            "path": "/images/materials/wushe-headquarters-1930.jpg",
            "sha256": "4e625113bc0b0db638121741f0f85937df4278c8d6951f227afa378186f235fb",
            "license": "Public domain (Commons: PD-Japan-oldphoto; PD-1996)",
            "checked_at": "2026-09-05"
          },
          "note": "本題組以可核對的文件名稱、出版資料及歷史照片編製；校刊編輯為虛構教學情境。軍事紀錄部分僅提供出版介紹，未提供或假稱引用軍方日誌與給養紀錄全文。圖說保留日文，中文採保守摘要，確切拍攝日期、攝影者及『滿期除隊兵歸隊』所涉行政流程尚未核實。題目答案維持 C、否、軍事紀錄；本輪調整材料範圍與題意對應，尚未做題目難度等值或測量效度驗證。角色仍設定於 1930 年 10 月，不得把 1931 年或後世資訊說成當時親知。",
          "fact_check": {
            "checked_at": "2026-09-17",
            "method": "source_cross_check_with_public_textbook_reference",
            "status": "source_checked_pending_researcher_review",
            "note": "已交叉查核所列來源；不是史學專家簽核，也不代表題目難度或測量效度已驗證。"
          },
          "curriculum_reference": {
            "publisher": "三民書局",
            "curriculum": "108 課綱普通型高中歷史",
            "scope": "公開自學教材相關頁面；頁碼依本次下載版本，不推定等於所有學年度的版本。",
            "volume": 1,
            "chapter": "第1章 臺灣最早的住民",
            "pages": [
              28,
              29
            ],
            "source_url": "https://sites.google.com/view/sanminhistorybook2/高一自學霸/歷史第一冊/第一冊序篇-第一章",
            "pdf_url": "https://drive.google.com/file/d/1aNdbDVYlD5y4xVcPeLlLGXBCYk7MsxAA/view"
          }
        }
      }
    },
    {
      "event_name": "法國大革命",
      "title": "法國大革命：一場宣誓，兩種紀錄",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "某展覽要介紹法國大革命初期的網球場宣誓。策展人取得宣誓內容的整理與一幅後來製作的畫稿，準備將它們並列展示。請閱讀材料，協助他判斷適合的解說。\n\nQ01｜依據宣誓紀錄，代表們為何在原會場關閉後，仍決定繼續集會？\n{{blank:q01}}\n\nQ02｜有人說：「大衛的畫稿描繪網球場宣誓，因此可以直接確認每位代表在 1789 年現場的實際動作與站位。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果要研究「革命初期的視覺作品，如何透過人物安排與構圖向公眾描繪這場宣誓」，應優先選擇本文中的「宣誓紀錄」或「大衛畫稿」？請填其中一項，並說明它為何適合這個問題。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "france_oath_record",
            "title": "1789 年 6 月 20 日的網球場宣誓（紀錄整理）",
            "caption": "1789 年 6 月 20 日，代表們轉往室內球場集會。以下為當日宣誓紀錄的中文內容整理。",
            "text": "1789 年，法國面臨財政危機，路易十六召開三級會議，代表分屬教士、貴族與第三等級。會議對代表權與表決方式產生爭議。6 月 17 日，第三等級代表與部分教士成立國民議會。\n\n6 月 20 日，代表們發現原先會場關閉，便轉到附近的室內球場集會。這座球場進行的是現代網球前身的運動，這次集會慣稱「網球場宣誓」。代表宣誓，在王國的憲法尚未建立於穩固基礎之前，不會解散；只要情勢需要，就繼續在能集會的地方開會。這段紀錄保留了他們繼續集會、建立憲法的承諾。",
            "source_url": "https://www.assemblee-nationale.fr/dyn/histoire-et-patrimoine/revolution-francaise/assemblee-nationale-constituante",
            "attribution": "依法國國民議會〈1789－制憲國民議會〉及凡爾賽宮網球場宣誓解說中文改寫。6 月 17 日的代表組成以國民議會逐日紀錄核對；此處不是原件影像或逐字引文。"
          },
          {
            "id": "france_david_drawing",
            "title": "大衛畫稿：1791 年描繪的網球場宣誓",
            "caption": "雅克路易大衛 1791 年的預備畫稿，描繪 1789 年 6 月 20 日的宣誓；現藏凡爾賽宮。它不是現場即時繪製的圖像。",
            "image_url": "/images/materials/tennis-court-oath-david-1791.jpg",
            "text": "畫家雅克路易大衛沒有在現場見證 1789 年 6 月 20 日的宣誓。後來，他蒐集相關資料並安排構圖，準備以大型繪畫呈現這件事。1791 年，他先在畫室、再於巴黎沙龍展出這幅預備畫稿，讓公眾觀看。\n\n畫面中央有人舉起右手，周圍許多人物也伸出手臂，上方可見旁觀人群與揚起的窗簾。這些是畫面呈現的安排。為了完成大型繪畫，大衛又邀請曾出席宣誓的議員到畫室，或寄送肖像供他參考；大型繪畫最終沒有完成。眼前這幅畫稿可以用來觀察畫家如何呈現宣誓，但不能單獨確認當天每個人的動作與站位。",
            "source_url": "https://en.chateauversailles.fr/sites/default/files/presse/documents/cp_restauration_jeu_de_paume_en.pdf",
            "attribution": "凡爾賽宮《The Royal Tennis Court restored》第 6 頁。圖像為大衛1791年預備畫稿（MV 840f），並非1883年梅爾松複製畫。沿用 Wikimedia Commons「Le Serment du Jeu de paume.jpg」公有領域圖檔；原攝影署名 Château de Versailles, Dist. RMN / Jean-Marc Manaï。"
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
                "label": "等待王室安排正式會場後，才開始討論是否制定憲法。",
                "value": "A"
              },
              {
                "id": "b",
                "label": "將建立憲法視為繼續集會的理由，不因場地改變而停止。",
                "value": "B"
              },
              {
                "id": "c",
                "label": "憲法已經完成，只差在另一個場地舉行公布儀式。",
                "value": "C"
              },
              {
                "id": "d",
                "label": "已決定立刻廢除君主制度，並以此作為結束會議的條件。",
                "value": "D"
              }
            ],
            "correct_answer": "B",
            "source_text": "代表宣誓憲法未建立於穩固基礎前不解散，並在需要時繼續於可用地點集會；場地變動沒有取代其憲法目標。",
            "accepted_evidence_ids": [
              "france_oath_record"
            ],
            "reasoning_criteria": "通過：把不解散的承諾或繼續集會，與憲法尚待建立的目標連結，說明換場地不等於放棄這個目標。接受簡短、白話的合理轉述。不通過：只重複選項、稱憲法已完成，或把這次宣誓直接說成當天已廢除君主制度。"
          },
          {
            "id": "q02",
            "type": "true_false",
            "required": true,
            "correct_answer": false,
            "source_text": "大衛未在宣誓現場，畫稿經事後蒐集資料與構圖安排；它不能單獨確認每個人的實際動作與站位。這並不等於畫作沒有任何史料價值。",
            "accepted_evidence_ids": [
              "france_david_drawing"
            ],
            "reasoning_criteria": "通過：指出畫家不在場、後來蒐集材料或安排構圖等至少一項資訊，並說明因此不能直接確認每個現場細節。只要因果連結清楚即可，不要求專業術語。不通過：只說畫是假的、所有後來資料都無用，或僅因相隔兩年便斷言所有細節必錯。"
          },
          {
            "id": "q03",
            "type": "cloze",
            "required": true,
            "correct_answer": [
              "大衛畫稿",
              "大衛的畫稿",
              "大衛的預備畫稿",
              "大衛預備畫稿",
              "網球場宣誓畫稿",
              "網球場宣誓預備畫稿",
              "1791年大衛畫稿",
              "大衛的網球場宣誓畫稿"
            ],
            "source_text": "1791 年公開展示的預備畫稿包含人物與構圖安排，適合研究革命初期的視覺作品如何描繪宣誓；宣誓紀錄主要保留代表的集體承諾。",
            "accepted_evidence_ids": [
              "france_oath_record",
              "france_david_drawing"
            ],
            "reasoning_criteria": "通過：將人物安排、構圖或向公眾展出的視覺作品，連結到研究宣誓如何被描繪。接受白話解釋，不要求評論藝術風格；可以比較宣誓紀錄，但不強制逐項比較。不通過：只說畫比較漂亮或年代較新，或把畫稿當成現場完整實錄。"
          }
        ],
        "all_correct_fallback": {
          "id": "france_later_drawing_useless",
          "evidence_ids": [
            "france_david_drawing"
          ],
          "incorrect_claim": "大衛不在宣誓現場，所以他的畫稿對研究法國大革命完全沒有價值。",
          "correct_interpretation": "畫稿不能單獨證明現場每個細節，仍可用來研究革命初期如何安排人物與構圖、向公眾呈現宣誓。材料是否適合，取決於研究問題。",
          "source_text": "大衛畫稿的後製性質及 1791 年公開展示背景。"
        },
        "authoring": {
          "method": "researcher_curated_with_ai_assistance",
          "version": "reading-materials-20260917-v5",
          "review_status": "awaiting_researcher_acceptance",
          "sources": [
            "https://www.assemblee-nationale.fr/dyn/histoire-et-patrimoine/revolution-francaise/assemblee-nationale-constituante",
            "https://en.chateauversailles.fr/discover/history/key-dates/jeu-paume-oath-1789",
            "https://en.chateauversailles.fr/sites/default/files/presse/documents/cp_restauration_jeu_de_paume_en.pdf",
            "https://commons.wikimedia.org/wiki/File:Le_Serment_du_Jeu_de_paume.jpg"
          ],
          "note": "原創閱讀題組；宣誓內容與畫作背景均為中文改寫，不是逐字引文。編製說明僅供研究者查看。沿用已確認的模擬題組形式；區分 1791 年預備畫稿、未完成的大型繪畫與 1883 年後來的複製作品。未複製學測題目。\n2026-09-17查核：答案維持B／false／大衛畫稿。Q03限縮為視覺作品的人物安排與構圖，避免『向公眾呈現』也可涵蓋公開宣誓紀錄的歧義。大衛不在場、1791畫室及沙龍展示與未完成大型繪畫，由凡爾賽宮官方修復資料第6頁支持。來源網站對6/17貴族加入時序有簡化差異，採國民議會記載的第三等級與部分教士。",
          "fact_check": {
            "checked_at": "2026-09-17",
            "method": "source_cross_check_with_public_textbook_reference",
            "status": "source_checked_pending_researcher_review",
            "note": "已交叉查核所列來源；不是史學專家簽核，也不代表題目難度或測量效度已驗證。"
          },
          "curriculum_reference": {
            "publisher": "三民書局",
            "curriculum": "108 課綱普通型高中歷史",
            "scope": "公開自學教材相關頁面；頁碼依本次下載版本，不推定等於所有學年度的版本。",
            "volume": 3,
            "chapter": "第2章 歐洲自由與民主的發展",
            "section": "第2節 十八、十九世紀政治與經濟的新思維",
            "pages": [
              54,
              55
            ],
            "source_url": "https://sites.google.com/view/sanminhistorybook110/首頁/第二章",
            "pdf_url": "https://drive.google.com/file/d/1wMTa7g2J7SuHZXElY-cXduQdLQSGtVXO/view"
          }
        }
      }
    }
  ],
  "previous_tasks": [
    {
      "event_name": "黑船事件到明治維新",
      "title": "黑船事件到明治維新：新政體應由誰作主？",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "某展覽要呈現黑船來航後，日本政治秩序如何被重新討論。策展人找到坂本龍馬與西周的兩份政體構想，準備替它們撰寫說明。\n\nQ01｜若要替兩份構想寫一句共同的展覽說明，下列哪一項最符合本文？\n{{blank:q01}}\n\nQ02｜有人說：「兩份材料可以顯示當時有人構想設立議事機構，但不能僅憑這些構想，就認定日本人民當時已普遍取得選舉權。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果展覽要介紹「引進新的權力分工，同時維持德川家政治中心地位」的構想，應以誰的方案為主要材料？填入本文中的人名，並在理由中說明你的判斷依據。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "japan_ryoma_plan",
            "title": "1867 年坂本龍馬的《新政府綱領八策》",
            "caption": "幕末政局變動之際，坂本龍馬向土佐藩高層提出的新政體草案。",
            "text": "1853 年，培里率領美國艦隊抵達浦賀，要求日本接受有關交往與通商的國書。幕府將國書及相關文件翻譯後，向多位大名徵詢意見。對外關係的壓力，也伴隨著由誰參與國家決策的討論。\n\n到了 1867 年，坂本龍馬與土佐藩的後藤象二郎討論政局，支持將政治權力歸還朝廷，並提出議事機構、官員任用、外交與軍事等方面的改革構想。他留下的《新政府綱領八策》，是向土佐藩高層提出的新政體草案。它所處理的不只是更換掌權者，也包括新政府應如何組織、由哪些人參與議事等問題。",
            "source_url": "https://www.ndl.go.jp/modern/e/cha1/description02.html",
            "attribution": "日本國立國會圖書館 Modern Japan in archives，1-1、1-2；以館方史料解說核對後自行改寫，未使用其現成習題。"
          },
          {
            "id": "japan_nishi_plan",
            "title": "1867 年西周的《議題草案》與《別紙議題草案》",
            "caption": "西周於 1867 年 12 月提出的政體構想，討論將軍、各藩與議事機構的權力安排。",
            "text": "幕府的西洋學研究者西周也提出另一套方案。他向德川慶喜的顧問提交《議題草案》，並在相關草案中規劃以德川家為中心的政治制度。這套構想參考西方的權力分工：行政由將軍掌握，司法暫由各藩負責，立法則交由大名及各藩武士組成的議事機構；天皇居於象徵性位置。\n\n兩份構想都出現在舊有政治秩序被重新商議的時期，也都涉及議事機構。不過，讀到設立議事機構的主張，與看見一套已經實施的制度，仍是兩種不同的事情。策展人手上目前只有上述草案與相關介紹，沒有當時的選民名冊或實際選舉紀錄。",
            "source_url": "https://www.ndl.go.jp/modern/e/cha1/description03.html",
            "attribution": "日本國立國會圖書館，1-3 NISHI Amane's Conception of a System of Government；末段策展情境為本題組設定，不是史料引文。"
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
                "label": "兩者都討論議事機構，但對政治權力如何安排各有構想。",
                "value": "A"
              },
              {
                "id": "b",
                "label": "兩者都主張保留將軍掌握行政，並讓天皇只有象徵性地位。",
                "value": "B"
              },
              {
                "id": "c",
                "label": "兩者只處理對外通商，不涉及日本內部的決策制度。",
                "value": "C"
              },
              {
                "id": "d",
                "label": "兩者記錄了同一套已完成實施的全國選舉制度。",
                "value": "D"
              }
            ],
            "correct_answer": "A",
            "source_text": "龍馬構想包括政治權力歸還朝廷及議事機構；西周構想以德川家為中心，將行政交予將軍並設議事機構。相似之處不等於整套權力安排一致。",
            "accepted_evidence_ids": [
              "japan_ryoma_plan",
              "japan_nishi_plan"
            ],
            "reasoning_criteria": "通過：指出兩者都涉及議事或決策組織，並說明至少一項權力安排差異，例如歸還朝廷與以德川家為中心。允許白話、同義轉述及有本文根據的其他比較。不通過：只複述所選選項而未連結材料、把兩份方案說成完全相同，或把改革主張當成已實行的普選。"
          },
          {
            "id": "q02",
            "type": "true_false",
            "required": true,
            "correct_answer": true,
            "source_text": "本文提供的是政體構想及草案，未提供普遍選舉權已落實的紀錄；西周方案的議事成員明列為大名及各藩武士。",
            "accepted_evidence_ids": [
              "japan_ryoma_plan",
              "japan_nishi_plan"
            ],
            "reasoning_criteria": "通過：說明提出議事機構不等於制度已實施或全民可參與，並以草案性質、缺少實施紀錄，或西周指定大名與武士為成員等至少一項本文資訊支持。不要求主張當時所有人都沒有政治參與機會。不通過：只說資料不夠而未指出缺少哪種連結，或把議事機構直接等同普選。"
          },
          {
            "id": "q03",
            "type": "cloze",
            "required": true,
            "correct_answer": [
              "西周",
              "西周的方案",
              "西周的政體構想",
              "Nishi Amane"
            ],
            "source_text": "西周方案參考權力分工，同時把行政權交給將軍，以德川家為政治中心。",
            "accepted_evidence_ids": [
              "japan_nishi_plan"
            ],
            "reasoning_criteria": "通過：把新權力分工或議事機構，與將軍掌行政或德川家居政治中心這兩面連結起來。不必列完行政、立法與司法，也不要求任何專門術語。不通過：只因西周學過西洋知識就下結論、只重複人名，或誤稱其主張廢除德川政治權力。"
          }
        ],
        "all_correct_fallback": {
          "id": "japan_plans_equal_elections",
          "evidence_ids": [
            "japan_ryoma_plan",
            "japan_nishi_plan"
          ],
          "incorrect_claim": "只要政體草案提出設立議事機構，就足以證明當時所有日本人已經能投票決定國家政策。",
          "correct_interpretation": "提出議事機構不等於全民選舉已實施；需區分草案與實施，並核對誰有參與資格。西周草案所列議事成員是大名和各藩武士。",
          "source_text": "本文的兩份政體構想及其性質；尤其西周方案的參與者與權力分工。"
        },
        "authoring": {
          "method": "researcher_curated_with_ai_assistance",
          "version": "reading-materials-20260905-v3",
          "review_status": "awaiting_researcher_acceptance",
          "sources": [
            "https://www.ndl.go.jp/modern/e/cha1/description01.html",
            "https://www.ndl.go.jp/modern/e/cha1/description02.html",
            "https://www.ndl.go.jp/modern/e/cha1/description03.html"
          ],
          "note": "原創閱讀題組；材料內容依史料介紹中文改寫，並非當事人的逐字發言。編製說明僅供研究者查看。不宣稱與其他事件難度等值。西周的後期草案只能作為提供的材料，不應被龍馬說成自己親眼見過或死後得知的事。"
        }
      }
    },
    {
      "event_name": "鴉片戰爭",
      "title": "鴉片戰爭：一封禁煙書信與一份戰後條約",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "一個歷史展覽要呈現鴉片戰爭前後，清朝與英國之間的交涉。策展人把林則徐的書信與《南京條約》放在一起，請你協助判斷適合的解說。書信中的主張不等於收信者已經同意。\n\nQ01｜若要替林則徐書信中的論證方式撰寫說明，下列哪一項最適當？\n{{blank:q01}}\n\nQ02｜有人根據《南京條約》關於交易對象的規定，宣稱：「條約簽訂後，英商已可到中國任何地方自由居住和經商。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果要查核「戰後清朝正式承諾如何改變英商的交易制度」，應優先閱讀本文中的哪一份文件？請填文件名稱，並說明它為何比另一份更適合回答這個問題。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "opium_lin_letter",
            "title": "1839 年林則徐致英國君主的禁煙書信",
            "caption": "林則徐在廣東推動禁煙時，透過書信要求英國君主約束販運鴉片的商人。",
            "text": "1839 年，林則徐在廣東處理禁煙事務，並寫了一封面向英國君主的書信。信中指責部分商人為追求利益，將鴉片運入中國，造成危害。他將中國輸出的茶、絲等貨品描述為有益的商品，反問英國商人既能從正常貿易獲利，為何還要販售傷人的鴉片。\n\n信中又提出一個換位的假設：假如有人把鴉片帶到英國，使當地人民購買、吸食，英國君主會如何看待？林則徐藉此要求對方約束商人、阻止鴉片輸入，並主張來華經商者應遵守中國法律。這是他試圖說服對方的論述；現存這封書信本身，並不能證明英國君主已閱讀或接受其中的要求。",
            "source_url": "https://ccnmtl.columbia.edu/services/dropoff/china_civ_temp/week11/pdfs/comiss.pdf",
            "attribution": "Columbia University 收錄林則徐 Letter of Advice to Queen Victoria，原文節譯第 2–4 頁；僅據信件內容改寫，不採用該檔導言中將南京條約誤述為鴉片合法化的敘述。"
          },
          {
            "id": "opium_nanjing_treaty",
            "title": "1842 年《南京條約》的通商規定",
            "caption": "鴉片戰爭後清英簽訂的條約；本文選取第二、第五款涉及居住口岸與交易對象的規定。",
            "text": "戰爭後，清朝與英國於 1842 年簽訂《南京條約》。第二款列出廣州、廈門、福州、寧波與上海，允許英國商民及其家屬在這些城市居住、從事商業活動，並安排英國領事駐在。\n\n第五款回顧英商在廣州原先須透過特許的行商交易，約定往後在准許英商居住的口岸，取消只能與這些行商交易的限制，讓英商自行選擇交易對象。策展人發現，這裡同時談到「在哪些地方」與「可以和誰交易」。他打算以這份條約說明戰後的正式約定，但尚未蒐集各地實際執行情況或商人的日常交易帳冊。",
            "source_url": "https://afe.easia.columbia.edu/ps/china/nanjing.pdf",
            "attribution": "Columbia University, Asia for Educators, Excerpts from the Treaty of Nanjing, August 1842，第 1–2 頁，第二及第五款；策展情境為原創。"
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
                "label": "以戰後條約的權利，要求英商擴大鴉片貿易。",
                "value": "A"
              },
              {
                "id": "b",
                "label": "以英國君主的回信，證明雙方已同意禁止鴉片。",
                "value": "B"
              },
              {
                "id": "c",
                "label": "把所有中外交易都視為有害，主張拒絕一切商品。",
                "value": "C"
              },
              {
                "id": "d",
                "label": "對比貿易的利益與鴉片的危害，要求對方設想本國遭受同樣傷害。",
                "value": "D"
              }
            ],
            "correct_answer": "D",
            "source_text": "林則徐對照茶絲貿易的利益與鴉片的危害，並假設鴉片被運入英國，藉此勸說英國君主約束商人。",
            "accepted_evidence_ids": [
              "opium_lin_letter"
            ],
            "reasoning_criteria": "通過：從信中指出有益貿易與鴉片傷害的對比，以及要求英國設想自己人民受害的意思，說明這些內容用來勸阻鴉片貿易。可用白話，不要求寫出換位思考或任何歷史思考術語。不通過：只評價林則徐愛國、只重複選項而不連結書信內容，或把勸說當成英方已同意。"
          },
          {
            "id": "q02",
            "type": "true_false",
            "required": true,
            "correct_answer": false,
            "source_text": "第二款列明五個城市；第五款的自由選擇交易對象限於准許英商居住的口岸，不能外推至中國任何地方。",
            "accepted_evidence_ids": [
              "opium_nanjing_treaty"
            ],
            "reasoning_criteria": "通過：區分可自行選交易對象與居住經商地點，指出條約只列五口或限定准許居住的口岸，故不足以推論全中國皆可。列出五個城市不是必要條件。不通過：只說條約不平等、英國很強勢，或把與任何人交易誤讀為在任何地方交易。"
          },
          {
            "id": "q03",
            "type": "cloze",
            "required": true,
            "correct_answer": [
              "南京條約",
              "《南京條約》",
              "南京條約的通商規定",
              "1842年南京條約",
              "1842年《南京條約》",
              "Treaty of Nanjing",
              "Treaty of Nanking"
            ],
            "source_text": "南京條約是戰後正式約定，包含英商居住城市及取消行商交易限制；林則徐書信表達戰前禁煙要求，不能替代戰後約定。",
            "accepted_evidence_ids": [
              "opium_lin_letter",
              "opium_nanjing_treaty"
            ],
            "reasoning_criteria": "通過：說明條約直接記載戰後正式承諾，例如五口或行商限制改變，並指出書信是戰前要求而非戰後協議。接受不逐字引用的等義說明。不通過：只因文件較新、官方文件必定完全正確，或認為條約足以證明每個地方的實際執行。"
          }
        ],
        "all_correct_fallback": {
          "id": "opium_request_equals_agreement",
          "evidence_ids": [
            "opium_lin_letter"
          ],
          "incorrect_claim": "林則徐的書信要求英國阻止鴉片輸入，所以這封信就能證明英國君主已接受禁煙要求。",
          "correct_interpretation": "書信可以顯示寫信者的要求與說服方式，但收信者是否閱讀、同意或採取行動，需要其他紀錄，不能由要求本身推定。",
          "source_text": "林則徐書信及其文件性質；寫信者的要求並非收信者的答覆。"
        },
        "authoring": {
          "method": "researcher_curated_with_ai_assistance",
          "version": "reading-materials-20260905-v3",
          "review_status": "awaiting_researcher_acceptance",
          "sources": [
            "https://ccnmtl.columbia.edu/services/dropoff/china_civ_temp/week11/pdfs/comiss.pdf",
            "https://afe.easia.columbia.edu/ps/china/nanjing.pdf"
          ],
          "note": "原創閱讀題組；內容依文件中文改寫，不是逐字翻譯。編製說明僅供研究者查看。只改寫核對過的文件段落，未複製來源教學問題；不將信件對英國的描述當作英國社會實況，也不宣稱南京條約使鴉片合法化。"
        }
      }
    },
    {
      "event_name": "霧社事件",
      "title": "霧社事件：照片裡與照片外",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "校刊準備製作霧社事件專頁。編輯桌上放著一本中文史料集，以及一張附有日文圖說的舊照片。有人想寫部隊的行動與物資安排，有人想談照片如何呈現事件，也有人想了解各部落居民在衝突中的生活。\n\n版面有限，編輯必須先決定：手上的材料適合寫哪些內容，哪些部分還得繼續找資料？請根據下方的軍事紀錄介紹與歷史照片（含圖說），回答下面三題。\n\nQ01｜只憑本文介紹的兩組資料，哪一項研究最需要補充其他人的紀錄或訪談？\n{{blank:q01}}\n\nQ02｜有人說：「軍事紀錄的中文譯本在 2010 年出版，因此它不能包含日治時期軍方留下的紀錄。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果要先查找軍方如何安排物資供應，而不只是它如何在影像中呈現行動，應優先閱讀「軍事紀錄」或「攝影資料」？請填其中一項，並說明選擇的依據與限制。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "wushe_military_records",
            "title": "軍事紀錄：2010 年出版的霧社事件史料譯集",
            "caption": "《霧社事件日文史料翻譯》由國立臺灣歷史博物館出版，收錄較早的軍方文件及事件解說。",
            "text": "1930 年 10 月 27 日，莫那魯道與霧社地區六個部落的賽德克族人發動抗日行動，日本軍警隨後進行鎮壓。除了戰鬥，部隊的調動與物資供應也留下了文字紀錄。\n\n《霧社事件日文史料翻譯》收錄的文件包括《霧社事件陣中日誌》、《霧社事件關係陸軍大臣官房書類綴》，以及《昭和五年臺灣霧社事件給養史》。其中「昭和五年」是 1930 年，「給養」指部隊所需的糧食、物資等供應。這些日文文件涉及日本軍方的軍事行動與後勤補給。\n\n這本中文出版品於 2010 年由國立臺灣歷史博物館出版，除了上述文件的譯文，也收錄學者春山明哲對事件的解說。編輯先從書名與收錄文件名稱建立索引，準備進一步查找部隊行動、物資供應等紀錄。",
            "source_url": "https://www.nmth.gov.tw/jp/News_Publish_Content.aspx?n=4414&s=139464",
            "attribution": "國立臺灣歷史博物館《霧社事件日文史料翻譯》出版介紹；事件背景另核對臺史博典藏〈霧社事件始末〉。本文不是軍方日誌的逐字節錄。"
          },
          {
            "id": "wushe_photographic_records",
            "title": "約 1930 年霧社本部前整理行李的照片",
            "caption": "這份攝影資料收錄於佐藤政藏編《第一第二霧社事件誌》（1931 年），呈現士兵與行李整理的場景；攝影者不詳。",
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
          "version": "reading-materials-20260916-v4",
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
    },
    {
      "event_name": "法國大革命",
      "title": "法國大革命：一場宣誓，兩種紀錄",
      "story_text": "",
      "revision_state": "teacher_modified",
      "error_elicitation_task_full_text": "某展覽要介紹法國大革命初期的網球場宣誓。策展人取得宣誓紀錄與一幅後來製作的畫稿，準備將它們放在一起展示。閱讀本文後，協助他判斷合適的解說。\n\nQ01｜依據宣誓紀錄，代表們為何在原會場關閉後，仍決定繼續集會？\n{{blank:q01}}\n\nQ02｜有人說：「大衛的畫稿描繪網球場宣誓，因此可以直接確認每位代表在 1789 年現場的實際動作與站位。」這個判斷是否成立？\n{{blank:q02}}\n\nQ03｜如果要研究「革命初期，人們如何向公眾呈現這場宣誓」，應優先選擇本文中的「宣誓紀錄」或「大衛畫稿」？請填其中一項，並說明它為何適合這個問題。\n{{blank:q03}}",
      "evaluation_payload": {
        "contract_version": "error_elicitation_v1",
        "materials": [
          {
            "id": "france_oath_record",
            "title": "1789 年 6 月 20 日的網球場宣誓紀錄",
            "caption": "代表們轉往室內網球場集會，宣誓在憲法建立於穩固基礎之前不解散。",
            "text": "1789 年，法國面臨財政危機，路易十六召開三級會議，代表分屬教士、貴族與第三等級。會議中，如何組成能代表國民的議事機構成為爭議。6 月 17 日，第三等級代表與部分教士成立國民議會。\n\n6 月 20 日，代表們發現原先的會場關閉，便到附近的室內網球場集會。他們宣誓，在王國的憲法尚未建立於穩固基礎之前，不會解散；只要情勢需要，就繼續在能集會的地方開會。這份紀錄留下的是代表們在當時所作的集體承諾，將繼續集會與制定憲法連結起來，而不是一份已經完成的憲法文本。",
            "source_url": "https://en.chateauversailles.fr/discover/history/key-dates/jeu-paume-oath-1789",
            "attribution": "凡爾賽宮 Jeu de Paume Oath, 1789；另據法國國民議會 Assemblée nationale constituante 核對 6 月 17 日成立背景。"
          },
          {
            "id": "france_david_drawing",
            "title": "大衛畫稿：1791 年描繪的網球場宣誓",
            "caption": "雅克路易大衛於 1791 年製作的預備畫稿，描繪 1789 年 6 月 20 日的宣誓；現藏凡爾賽宮。",
            "image_url": "/images/materials/tennis-court-oath-david-1791.jpg",
            "text": "畫家雅克路易大衛並未親自在場見證 1789 年 6 月 20 日的宣誓。他後來蒐集相關資料，安排畫面的構圖，準備以大型作品呈現這件事。1791 年，他的預備畫稿向公眾展示；為了完成較大的繪畫計畫，他也邀請議員到畫室，或寄送肖像供他參考。那幅大型繪畫最終沒有完成。\n\n策展人注意到，宣誓紀錄與畫稿雖指向同一場事件，留下的內容卻不同：一份是當時作出的承諾，另一份是稍後整理資料、安排人物與構圖，再呈現給觀看者的作品。他希望在不混淆兩者的前提下，讓觀眾理解這場宣誓，也理解它在革命初期如何被描繪。",
            "source_url": "https://en.chateauversailles.fr/sites/default/files/presse/documents/cp_restauration_jeu_de_paume_en.pdf",
            "attribution": "凡爾賽宮 The Royal Tennis Court restored，第 6 頁；圖像為 Jacques-Louis David 1791 年預備畫稿（MV 840f），非 1883 年複製畫。檔案取自 Wikimedia Commons「Le Serment du Jeu de paume.jpg」，標示 PD-Art／公有領域；攝影署名 Château de Versailles, Dist. RMN / Jean-Marc Manaï。圖片未裁切、生成或修補。"
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
                "label": "等待王室安排正式會場後，才開始討論是否制定憲法。",
                "value": "A"
              },
              {
                "id": "b",
                "label": "將建立憲法視為繼續集會的理由，不因場地改變而停止。",
                "value": "B"
              },
              {
                "id": "c",
                "label": "憲法已經完成，只差在另一個場地舉行公布儀式。",
                "value": "C"
              },
              {
                "id": "d",
                "label": "已決定立刻廢除君主制度，並以此作為結束會議的條件。",
                "value": "D"
              }
            ],
            "correct_answer": "B",
            "source_text": "代表宣誓憲法未建立於穩固基礎前不解散，並在需要時繼續於可用地點集會；場地變動沒有取代其憲法目標。",
            "accepted_evidence_ids": [
              "france_oath_record"
            ],
            "reasoning_criteria": "通過：把不解散的承諾或繼續集會，與憲法尚待建立的目標連結，說明換場地不等於放棄這個目標。接受簡短、白話的合理轉述。不通過：只重複選項、稱憲法已完成，或把這次宣誓直接說成當天已廢除君主制度。"
          },
          {
            "id": "q02",
            "type": "true_false",
            "required": true,
            "correct_answer": false,
            "source_text": "大衛未在宣誓現場，畫稿經事後蒐集資料與構圖安排；它不能單獨確認每個人的實際動作與站位。這並不等於畫作沒有任何史料價值。",
            "accepted_evidence_ids": [
              "france_david_drawing"
            ],
            "reasoning_criteria": "通過：指出畫家不在場、後來蒐集材料或安排構圖等至少一項資訊，並說明因此不能直接確認每個現場細節。只要因果連結清楚即可，不要求專業術語。不通過：只說畫是假的、所有後來資料都無用，或僅因相隔兩年便斷言所有細節必錯。"
          },
          {
            "id": "q03",
            "type": "cloze",
            "required": true,
            "correct_answer": [
              "大衛畫稿",
              "大衛的畫稿",
              "大衛的預備畫稿",
              "大衛預備畫稿",
              "網球場宣誓畫稿",
              "網球場宣誓預備畫稿",
              "1791年大衛畫稿",
              "大衛的網球場宣誓畫稿"
            ],
            "source_text": "1791 年公開展示的預備畫稿適合研究革命初期如何以人物安排與構圖向公眾呈現宣誓；宣誓紀錄更直接保留集體承諾。",
            "accepted_evidence_ids": [
              "france_oath_record",
              "france_david_drawing"
            ],
            "reasoning_criteria": "通過：把問題中的向公眾呈現，連結到畫稿在 1791 年展示、人物或構圖經安排等至少一項資訊，說明其適合研究事件如何被描繪。可以比較宣誓紀錄，但不強制逐項比較。不通過：只因畫比較漂亮、年代較新，或把畫稿當成現場攝影般的完整實錄。"
          }
        ],
        "all_correct_fallback": {
          "id": "france_later_drawing_useless",
          "evidence_ids": [
            "france_david_drawing"
          ],
          "incorrect_claim": "大衛不在宣誓現場，所以他的畫稿對研究法國大革命完全沒有價值。",
          "correct_interpretation": "畫稿不能單獨證明現場每個細節，仍可用來研究革命初期如何安排人物與構圖、向公眾呈現宣誓。材料是否適合，取決於研究問題。",
          "source_text": "大衛畫稿的後製性質及 1791 年公開展示背景。"
        },
        "authoring": {
          "method": "researcher_curated_with_ai_assistance",
          "version": "reading-materials-20260905-v3",
          "review_status": "awaiting_researcher_acceptance",
          "sources": [
            "https://www.assemblee-nationale.fr/dyn/histoire-et-patrimoine/revolution-francaise/assemblee-nationale-constituante",
            "https://en.chateauversailles.fr/discover/history/key-dates/jeu-paume-oath-1789",
            "https://en.chateauversailles.fr/sites/default/files/presse/documents/cp_restauration_jeu_de_paume_en.pdf",
            "https://commons.wikimedia.org/wiki/File:Le_Serment_du_Jeu_de_paume.jpg"
          ],
          "note": "原創閱讀題組；宣誓內容與畫作背景均為中文改寫，不是逐字引文。編製說明僅供研究者查看。沿用已確認的模擬題組形式；區分 1791 年預備畫稿、未完成的大型繪畫與 1883 年後來的複製作品。未複製學測題目。"
        }
      }
    }
  ]
}$json$::jsonb;
  v_event_patch JSONB;
  v_task_patch JSONB;
  v_previous_task JSONB;
  v_persona_patch JSONB;
  v_event events%ROWTYPE;
  v_latest event_tasks%ROWTYPE;
BEGIN
  FOR v_event_patch IN SELECT value FROM jsonb_array_elements(v_changes -> 'events')
  LOOP
    SELECT * INTO v_event FROM events
    WHERE canonical_name = v_event_patch ->> 'canonical_name' FOR UPDATE;
    -- Fresh databases replay this file after seed.sql inserts the base events.
    IF NOT FOUND OR v_event.archived_at IS NOT NULL THEN CONTINUE; END IF;
    IF EXISTS (
      SELECT 1 FROM event_tasks WHERE event_id = v_event.id
      AND evaluation_payload #>> '{authoring,version}' = v_changes ->> 'version'
    ) THEN CONTINUE; END IF;
    IF v_event.materials_locked_at IS NOT NULL THEN
      RAISE EXCEPTION 'Cannot revise locked event materials: %', v_event.canonical_name;
    END IF;
    IF EXISTS (
      SELECT 1 FROM experiment_sessions s
      WHERE s.event_id = v_event.id AND s.is_admin_test IS NOT TRUE
      AND s.status IN ('initialized', 'task_submitted', 'conversation_started')
    ) THEN
      RAISE EXCEPTION 'Finish active experiment sessions before revising: %', v_event.canonical_name;
    END IF;

    SELECT value INTO v_task_patch FROM jsonb_array_elements(v_changes -> 'tasks')
    WHERE value ->> 'event_name' = v_event.canonical_name;
    SELECT value INTO v_previous_task FROM jsonb_array_elements(v_changes -> 'previous_tasks')
    WHERE value ->> 'event_name' = v_event.canonical_name;
    SELECT * INTO v_latest FROM event_tasks WHERE event_id = v_event.id
    ORDER BY created_at DESC, id DESC LIMIT 1;
    -- Do not silently replace a newer/manual task that was not part of this review.
    IF FOUND AND (v_latest.title IS DISTINCT FROM v_previous_task ->> 'title'
      OR v_latest.story_text IS DISTINCT FROM v_previous_task ->> 'story_text'
      OR v_latest.error_elicitation_task_full_text IS DISTINCT FROM v_previous_task ->> 'error_elicitation_task_full_text'
      OR v_latest.evaluation_payload IS DISTINCT FROM v_previous_task -> 'evaluation_payload') THEN
      RAISE EXCEPTION 'Current task differs from reviewed content for %. Compare manually before applying.', v_event.canonical_name;
    END IF;

    UPDATE events SET
      description = v_event_patch ->> 'description',
      context = v_event_patch ->> 'context',
      start_year = (v_event_patch ->> 'start_year')::INT,
      end_year = (v_event_patch ->> 'end_year')::INT,
      century = (v_event_patch ->> 'century')::INT,
      source_summary = COALESCE(source_summary, '{}'::jsonb) || jsonb_build_object('content_review', v_event_patch -> 'content_review'),
      updated_at = now()
    WHERE id = v_event.id;

    FOR v_persona_patch IN SELECT value FROM jsonb_array_elements(v_event_patch -> 'personas')
    LOOP
      UPDATE personas SET
        biography = v_persona_patch ->> 'biography',
        expertise_areas = CASE WHEN v_persona_patch ? 'expertise_areas'
          THEN ARRAY(SELECT jsonb_array_elements_text(v_persona_patch -> 'expertise_areas')) ELSE expertise_areas END,
        sources = (SELECT COALESCE(jsonb_agg(DISTINCT item), '[]'::jsonb)
          FROM jsonb_array_elements(COALESCE(sources, '[]'::jsonb) || (v_persona_patch -> 'sources')) AS s(item)),
        prompt_profile = COALESCE(prompt_profile, '{}'::jsonb) || (v_persona_patch -> 'prompt_profile'),
        updated_at = now()
      WHERE event_id = v_event.id AND name = v_persona_patch ->> 'name' AND archived_at IS NULL;
    END LOOP;

    INSERT INTO event_tasks (event_id, title, story_text, error_elicitation_task_full_text, evaluation_payload, revision_state, created_at)
    VALUES (v_event.id, v_task_patch ->> 'title', v_task_patch ->> 'story_text',
      v_task_patch ->> 'error_elicitation_task_full_text', v_task_patch -> 'evaluation_payload',
      v_task_patch ->> 'revision_state',
      GREATEST(clock_timestamp(), COALESCE(v_latest.created_at + INTERVAL '1 microsecond', '-infinity'::timestamptz)));
  END LOOP;
END;
$do$;
