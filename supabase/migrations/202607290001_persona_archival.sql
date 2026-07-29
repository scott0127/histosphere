-- Persona 的「刪除」採可恢復封存，保留既有對話與研究資料關聯。
alter table public.personas
  add column if not exists archived_at timestamptz;

comment on column public.personas.archived_at is
  '封存時間；null 表示未封存。封存不會刪除既有研究資料。';

-- 只替尚未設定肖像的既有人物補值，保留 Admin 已自訂的圖片。
update public.personas
set avatar_url = case name
  when '馬克西米連·羅伯斯比爾' then '/images/personas/maximilien-robespierre.jpg'
  when '莫那·魯道' then '/images/personas/mona-rudao.jpg'
  when '林則徐' then '/images/personas/lin-zexu.jpg'
  when '坂本龍馬' then '/images/personas/sakamoto-ryoma.jpg'
  else avatar_url
end
where name in ('馬克西米連·羅伯斯比爾', '莫那·魯道', '林則徐', '坂本龍馬')
  and coalesce(avatar_url, '') = '';

-- 實驗執行時人物必須唯一；停用或封存人物不受此限制。
create unique index if not exists personas_one_active_per_event_idx
  on public.personas (event_id)
  where active = true and archived_at is null;
