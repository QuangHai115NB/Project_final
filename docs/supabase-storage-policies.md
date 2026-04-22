SUPABASE STORAGE POLICY SCRIPT FOR CV REVIEWER

File này dùng để copy vào Supabase SQL Editor.

Quan trọng:
- App hiện tại KHONG dung Supabase Auth o frontend/backend de truy cap storage.
- App dung JWT rieng cua Flask + SUPABASE_SERVICE_KEY o backend.
- Vi vay:
  1. Bucket CV va JD nen de PRIVATE.
  2. Khong can mo policy public cho CV/JD.
  3. Bucket avatar nen PUBLIC vi frontend dang dung public URL de hien anh avatar.

Bucket names trong code:
- cv-uploads
- jd-uploads
- user-avatars

Storage path format trong code:
- user_<app_user_id>/...
- Vi du: user_12/cv_uploads_20260422153000_ab12cd34.pdf

Luu y rat quan trong:
- auth.uid() cua Supabase KHONG map voi user_id integer trong app Flask cua ban.
- Vi vay khong nen viet policy kieu "folder name = auth.uid()" cho app nay.
- Neu ban muon policy theo tung user, ban can doi sang Supabase Auth hoac dong bo user mapping ro rang.

==================================================
SQL DE XOA POLICY QUA RONG NEU DA TAO TRUOC DO
==================================================

drop policy if exists "Public read cv uploads" on storage.objects;
drop policy if exists "Public read jd uploads" on storage.objects;
drop policy if exists "Authenticated read cv uploads" on storage.objects;
drop policy if exists "Authenticated read jd uploads" on storage.objects;
drop policy if exists "Authenticated upload cv uploads" on storage.objects;
drop policy if exists "Authenticated upload jd uploads" on storage.objects;
drop policy if exists "Authenticated delete cv uploads" on storage.objects;
drop policy if exists "Authenticated delete jd uploads" on storage.objects;

==================================================
SQL DE TAO / CAP NHAT BUCKET
==================================================

insert into storage.buckets (id, name, public)
values
  ('cv-uploads', 'cv-uploads', false),
  ('jd-uploads', 'jd-uploads', false),
  ('user-avatars', 'user-avatars', true)
on conflict (id) do update
set public = excluded.public;

==================================================
KHUYEN NGHI CHO APP HIEN TAI
==================================================

Khong tao policy read public cho:
- cv-uploads
- jd-uploads

Ly do:
- CV/JD dang duoc upload/download thong qua backend Flask.
- Backend dung service role key nen van truy cap duoc storage.
- De private se dung voi du lieu nhay cam.

==================================================
OPTIONAL: POLICY CHO AVATAR NEU BAN MUON CHO PHEP DOC CONG KHAI QUA STORAGE.OBJECTS
==================================================

Ghi chu:
- Neu bucket user-avatars da la public thi thuong khong can policy nay.
- Doan nay chi de du phong trong truong hop ban muon ro rang hoa quyen select.

drop policy if exists "Public read user avatars" on storage.objects;

create policy "Public read user avatars"
on storage.objects
for select
to public
using (bucket_id = 'user-avatars');

==================================================
KHONG NEN THEM CAC POLICY SAU CHO CV/JD
==================================================

Khong nen them:
- for select to public using (bucket_id = 'cv-uploads')
- for select to public using (bucket_id = 'jd-uploads')
- for select to authenticated using (bucket_id = 'cv-uploads')
- for select to authenticated using (bucket_id = 'jd-uploads')

Vi:
- "authenticated" cua Supabase khong phai user dang login trong app Flask cua ban.
- Neu mo sai policy, ban co the vo tinh expose CV/JD.

==================================================
CHECKLIST SAU KHI CHAY SQL
==================================================

1. Vao Storage > Buckets.
2. Xac nhan:
   - cv-uploads = private
   - jd-uploads = private
   - user-avatars = public
3. Test lai app:
   - Upload CV
   - Upload JD
   - Bam xem CV/JD
   - Upload avatar

==================================================
NEU BAN MUON DUNG CHINH SACH CHI TIET HON TRONG TUONG LAI
==================================================

Ban nen doi theo mot trong 2 huong:

Huong 1:
- Tiep tuc dung Flask auth hien tai
- Chi cho backend dung service role de doc/ghi storage
- Giu CV/JD private

Huong 2:
- Chuyen sang Supabase Auth
- Luu object path theo auth.uid()
- Luc do moi viet RLS/policy theo folder cua tung user

