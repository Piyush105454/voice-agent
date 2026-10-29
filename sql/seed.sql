-- Guru Line seed. Deterministic IDs so the demo, tests and docs can reference them.
-- Timestamps are relative to now() so the demo always looks "fresh" after a reset.
-- Rahul is seeded in his BEFORE state (mastery 0.30, confidence 3, misconception 0.80).
-- The scripted "Replay Rahul session" produces the AFTER state (0.62, 6, 0.35).

-- ======================= curriculum =======================
insert into topics(id,name,grade_min,grade_max) values
 ('num_negatives','Negative numbers',6,8),
 ('alg_expressions','Variables and expressions',6,8),
 ('alg_linear_eq','Linear equations',7,9),
 ('alg_distribution','Distributive property',7,9),
 ('alg_multistep','Multi-step equations',8,10);

insert into topic_prereqs values
 ('num_negatives','alg_expressions'),('alg_expressions','alg_linear_eq'),
 ('num_negatives','alg_linear_eq'),('alg_linear_eq','alg_multistep'),('alg_distribution','alg_multistep');

insert into misconception_types(id,topic_id,name,description,example) values
 ('adds_instead_of_inverse','alg_linear_eq','Adds instead of using inverse',
  'Applies the same operation to the other side instead of the inverse (adds when it should subtract, multiplies when it should divide).','x+5=12 -> 17'),
 ('sign_not_flipped','alg_linear_eq','Sign not flipped when moving a term',
  'Moves a term across the equals sign but keeps its sign.','x-3=7 -> 4'),
 ('coefficient_ignored','alg_linear_eq','Ignores coefficient',
  'Treats 3x as x: forgets to divide by the number in front of the variable.','3x=12 -> 12'),
 ('neg_number_confusion','num_negatives','Negative number rules',
  'Mixes up rules for adding, subtracting or multiplying negative numbers.','-2-3 -> -1'),
 ('distributes_partially','alg_distribution','Partial distribution',
  'Multiplies only the first term inside the bracket.','2(x+3) -> 2x+3'),
 ('equals_as_answer','alg_expressions','Treats = as "answer comes"',
  'Reads "=" as "write the answer next" instead of "both sides are equal".','3+4=7+2');

insert into questions(id,topic_id,text,answer,difficulty,wrong_answer_map) values
 -- Negative numbers
 ('q_001','num_negatives','-2 - 3 kitna hoga?','-5',0.3,'{"-1":"neg_number_confusion","1":"neg_number_confusion","5":"neg_number_confusion"}'),
 ('q_002','num_negatives','-4 + 7 kitna hoga?','3',0.3,'{"-11":"neg_number_confusion","-3":"neg_number_confusion","11":"neg_number_confusion"}'),
 ('q_003','num_negatives','5 - 8 kitna hoga?','-3',0.3,'{"3":"neg_number_confusion","13":"neg_number_confusion"}'),
 ('q_004','num_negatives','-6 + 2 kitna hoga?','-4',0.35,'{"-8":"neg_number_confusion","4":"neg_number_confusion","8":"neg_number_confusion"}'),
 ('q_005','num_negatives','-3 guna 4 kitna hoga?','-12',0.4,'{"12":"neg_number_confusion"}'),
 ('q_006','num_negatives','-2 guna -5 kitna hoga?','10',0.5,'{"-10":"neg_number_confusion","-7":"neg_number_confusion"}'),
 ('q_007','num_negatives','0 - 9 kitna hoga?','-9',0.2,'{"9":"neg_number_confusion"}'),
 ('q_008','num_negatives','-1 - (-4) kitna hoga?','3',0.6,'{"-5":"neg_number_confusion","5":"neg_number_confusion","-3":"neg_number_confusion"}'),
 -- Variables and expressions
 ('q_009','alg_expressions','3 + 4 = ___ + 2. Khaali jagah mein kya aayega?','5',0.3,'{"7":"equals_as_answer","9":"equals_as_answer"}'),
 ('q_010','alg_expressions','8 = ___ + 3. Khaali jagah mein kya aayega?','5',0.35,'{"11":"equals_as_answer","8":"equals_as_answer"}'),
 ('q_011','alg_expressions','5 + 2 = ___ - 1. Khaali jagah mein kya aayega?','8',0.4,'{"7":"equals_as_answer","6":"equals_as_answer"}'),
 ('q_012','alg_expressions','10 - 4 = ___ + 1. Khaali jagah mein kya aayega?','5',0.4,'{"6":"equals_as_answer","7":"equals_as_answer"}'),
 ('q_013','alg_expressions','Agar x = 3 hai, toh 2x + 1 kitna hoga?','7',0.3,'{"4":"coefficient_ignored"}'),
 ('q_014','alg_expressions','Agar x = 4 hai, toh 3x - 2 kitna hoga?','10',0.4,'{"2":"coefficient_ignored"}'),
 ('q_015','alg_expressions','6 + 3 = 4 + ___. Khaali jagah mein kya aayega?','5',0.35,'{"9":"equals_as_answer","13":"equals_as_answer"}'),
 ('q_016','alg_expressions','___ + 6 = 2 + 9. Khaali jagah mein kya aayega?','5',0.45,'{"11":"equals_as_answer","17":"equals_as_answer"}'),
 -- Linear equations
 ('q_017','alg_linear_eq','x + 5 = 12, x kya hoga?','7',0.3,'{"17":"adds_instead_of_inverse"}'),
 ('q_018','alg_linear_eq','x - 3 = 7, x kya hoga?','10',0.4,'{"4":"sign_not_flipped"}'),
 ('q_019','alg_linear_eq','3x = 12, x kya hoga?','4',0.4,'{"12":"coefficient_ignored","9":"sign_not_flipped"}'),
 ('q_020','alg_linear_eq','x + 8 = 15, x kya hoga?','7',0.3,'{"23":"adds_instead_of_inverse"}'),
 ('q_021','alg_linear_eq','x - 6 = 2, x kya hoga?','8',0.4,'{"-4":"sign_not_flipped","4":"sign_not_flipped"}'),
 ('q_022','alg_linear_eq','5x = 20, x kya hoga?','4',0.4,'{"20":"coefficient_ignored","15":"coefficient_ignored","100":"adds_instead_of_inverse"}'),
 ('q_023','alg_linear_eq','x + 9 = 4, x kya hoga?','-5',0.55,'{"13":"adds_instead_of_inverse","5":"neg_number_confusion"}'),
 ('q_024','alg_linear_eq','4x = 28, x kya hoga?','7',0.45,'{"28":"coefficient_ignored","24":"coefficient_ignored","112":"adds_instead_of_inverse"}'),
 ('q_025','alg_linear_eq','x - 7 = 3, x kya hoga?','10',0.4,'{"-4":"sign_not_flipped","4":"sign_not_flipped"}'),
 ('q_026','alg_linear_eq','x + 12 = 20, x kya hoga?','8',0.35,'{"32":"adds_instead_of_inverse"}'),
 ('q_027','alg_linear_eq','2x = 18, x kya hoga?','9',0.35,'{"18":"coefficient_ignored","16":"coefficient_ignored","36":"adds_instead_of_inverse"}'),
 ('q_028','alg_linear_eq','x - 4 = -1, x kya hoga?','3',0.6,'{"-5":"sign_not_flipped","5":"sign_not_flipped"}'),
 ('q_029','alg_linear_eq','x + 3 = 10, x kya hoga?','7',0.25,'{"13":"adds_instead_of_inverse"}'),
 ('q_030','alg_linear_eq','6x = 42, x kya hoga?','7',0.45,'{"42":"coefficient_ignored","36":"coefficient_ignored"}'),
 -- Distributive property
 ('q_031','alg_distribution','Agar x = 1 hai, toh 2(x + 3) kitna hoga?','8',0.4,'{"5":"distributes_partially"}'),
 ('q_032','alg_distribution','Agar x = 2 hai, toh 3(x + 2) kitna hoga?','12',0.4,'{"8":"distributes_partially"}'),
 ('q_033','alg_distribution','Agar x = 3 hai, toh 4(x - 1) kitna hoga?','8',0.5,'{"11":"distributes_partially"}'),
 ('q_034','alg_distribution','Agar x = 1 hai, toh 5(2 + x) kitna hoga?','15',0.45,'{"11":"distributes_partially"}'),
 ('q_035','alg_distribution','2(x + 4) = 14, x kya hoga?','3',0.6,'{"5":"distributes_partially"}'),
 -- Multi-step equations
 ('q_036','alg_multistep','2x + 3 = 11, x kya hoga?','4',0.55,'{"7":"adds_instead_of_inverse","8":"coefficient_ignored"}'),
 ('q_037','alg_multistep','3x - 4 = 11, x kya hoga?','5',0.6,'{"15":"coefficient_ignored"}'),
 ('q_038','alg_multistep','2(x + 1) = 10, x kya hoga?','4',0.65,'{"4.5":"distributes_partially","9":"coefficient_ignored"}'),
 ('q_039','alg_multistep','4x + 2 = 18, x kya hoga?','4',0.6,'{"5":"adds_instead_of_inverse","16":"coefficient_ignored"}'),
 ('q_040','alg_multistep','2(x - 3) = 8, x kya hoga?','7',0.7,'{"5.5":"distributes_partially","11":"coefficient_ignored"}');

-- ======================= people =======================
insert into teachers(id,name,email) values
 ('aaaaaaaa-0000-4000-8000-000000000001','Ms. Sharma','sharma@school.example');
insert into classes(id,teacher_id,name,grade) values
 ('bbbbbbbb-0000-4000-8000-000000000001','aaaaaaaa-0000-4000-8000-000000000001','Class 8A',8);

-- Phone numbers are fictional placeholders. scripts/reset_demo.py can set Rahul's to DEMO_STUDENT_PHONE.
insert into students(id,class_id,first_name,phone_e164,language,grade,is_minor) values
 ('11111111-1111-4111-8111-111111111111','bbbbbbbb-0000-4000-8000-000000000001','Rahul','+919800000021','hi-en',8,true),
 ('22222222-2222-4222-8222-222222222222','bbbbbbbb-0000-4000-8000-000000000001','Priya','+919800000032','hi',8,true),
 ('33333333-3333-4333-8333-333333333333','bbbbbbbb-0000-4000-8000-000000000001','Aman','+919800000043','en',8,true),
 ('44444444-4444-4444-8444-444444444444','bbbbbbbb-0000-4000-8000-000000000001','Sneha','+919800000054','hi-en',7,true),
 ('55555555-5555-4555-8555-555555555555','bbbbbbbb-0000-4000-8000-000000000001','Kabir','+919800000065','hi-en',8,true),
 -- No consent on file: used to demonstrate that calls are refused.
 ('66666666-6666-4666-8666-666666666666','bbbbbbbb-0000-4000-8000-000000000001','Meera','+919800000076','hi',8,true);

insert into guardians(student_id,name,phone_e164,preferred_language) values
 ('11111111-1111-4111-8111-111111111111','Sunita (mother)','+919800001021','hi'),
 ('22222222-2222-4222-8222-222222222222','Rakesh (father)','+919800001032','hi'),
 ('33333333-3333-4333-8333-333333333333','Anita (mother)','+919800001043','en'),
 ('44444444-4444-4444-8444-444444444444','Vikram (father)','+919800001054','hi'),
 ('55555555-5555-4555-8555-555555555555','Pooja (mother)','+919800001065','hi'),
 ('66666666-6666-4666-8666-666666666666','Mahesh (father)','+919800001076','hi');

-- Guardian consent for the 5 demo students, all three purposes. Meera: none.
insert into consents(student_id,given_by,purpose,granted,granted_at)
select s.id, 'guardian', p.purpose, true, now() - interval '14 days'
from students s cross join (values ('voice_tutoring'),('recording'),('teacher_sharing')) p(purpose)
where s.first_name <> 'Meera';

insert into data_sources(student_id,kind,consent_id,purpose)
select c.student_id, k.kind, c.id, k.purpose
from consents c
join (values ('call_transcript','Find misconceptions and remember them for the next call'),
             ('grading_result','Track mastery per topic'),
             ('parent_goal','Plan practice around the family''s goal')) k(kind,purpose) on true
where c.purpose = 'voice_tutoring';

-- ======================= learning state (current) =======================
insert into mastery(student_id,topic_id,p_known,stability_days,attempts,updated_at) values
 -- Rahul: weak negatives -> drives the "Why this question?" ribbon
 ('11111111-1111-4111-8111-111111111111','num_negatives',0.28,3,6,now() - interval '1 day'),
 ('11111111-1111-4111-8111-111111111111','alg_expressions',0.55,4,4,now() - interval '3 days'),
 ('11111111-1111-4111-8111-111111111111','alg_linear_eq',0.30,3,8,now() - interval '1 day'),
 ('11111111-1111-4111-8111-111111111111','alg_distribution',0.45,3,2,now() - interval '6 days'),
 ('11111111-1111-4111-8111-111111111111','alg_multistep',0.20,2,1,now() - interval '6 days'),
 -- Priya
 ('22222222-2222-4222-8222-222222222222','num_negatives',0.35,3,5,now() - interval '2 days'),
 ('22222222-2222-4222-8222-222222222222','alg_expressions',0.60,4,3,now() - interval '2 days'),
 ('22222222-2222-4222-8222-222222222222','alg_linear_eq',0.52,4,4,now() - interval '2 days'),
 -- Aman
 ('33333333-3333-4333-8333-333333333333','alg_linear_eq',0.66,5,6,now() - interval '1 day'),
 ('33333333-3333-4333-8333-333333333333','alg_distribution',0.34,3,4,now() - interval '1 day'),
 ('33333333-3333-4333-8333-333333333333','num_negatives',0.72,6,3,now() - interval '4 days'),
 -- Sneha
 ('44444444-4444-4444-8444-444444444444','alg_expressions',0.38,3,5,now() - interval '2 days'),
 ('44444444-4444-4444-8444-444444444444','alg_linear_eq',0.41,3,3,now() - interval '2 days'),
 -- Kabir
 ('55555555-5555-4555-8555-555555555555','alg_linear_eq',0.58,4,5,now() - interval '3 days'),
 ('55555555-5555-4555-8555-555555555555','alg_multistep',0.44,3,3,now() - interval '3 days');

insert into student_misconceptions(student_id,misconception_id,strength,first_seen,last_seen,evidence_n) values
 ('11111111-1111-4111-8111-111111111111','adds_instead_of_inverse',0.80,now() - interval '3 days',now() - interval '1 day',4),
 ('11111111-1111-4111-8111-111111111111','neg_number_confusion',0.45,now() - interval '3 days',now() - interval '3 days',2),
 ('11111111-1111-4111-8111-111111111111','sign_not_flipped',0.30,now() - interval '1 day',now() - interval '1 day',1),
 ('22222222-2222-4222-8222-222222222222','neg_number_confusion',0.60,now() - interval '2 days',now() - interval '2 days',3),
 ('22222222-2222-4222-8222-222222222222','sign_not_flipped',0.42,now() - interval '2 days',now() - interval '2 days',2),
 ('33333333-3333-4333-8333-333333333333','distributes_partially',0.70,now() - interval '4 days',now() - interval '1 day',3),
 ('33333333-3333-4333-8333-333333333333','sign_not_flipped',0.45,now() - interval '4 days',now() - interval '4 days',2),
 ('44444444-4444-4444-8444-444444444444','equals_as_answer',0.65,now() - interval '2 days',now() - interval '2 days',3),
 ('44444444-4444-4444-8444-444444444444','coefficient_ignored',0.40,now() - interval '2 days',now() - interval '2 days',1),
 ('55555555-5555-4555-8555-555555555555','coefficient_ignored',0.55,now() - interval '3 days',now() - interval '3 days',2),
 ('55555555-5555-4555-8555-555555555555','adds_instead_of_inverse',0.32,now() - interval '3 days',now() - interval '3 days',1);

-- ======================= session history =======================
insert into sessions(id,student_id,channel,bolna_call_id,started_at,ended_at,status,transcript) values
 ('c1000000-0000-4000-8000-000000000002','11111111-1111-4111-8111-111111111111','phone','seed-call-r1',
  now() - interval '3 days', now() - interval '3 days' + interval '6 minutes','ended',
  E'Guru: Namaste Rahul! -2 - 3 kitna hoga?\nRahul: minus 1\nGuru: Chalo check karte hain. Number line par -2 se 3 kadam kis taraf jaoge?\nRahul: left... minus 5\nGuru: Bahut accha, tumne number line use ki! x + 5 = 12, x kya hoga?\nRahul: 17\nGuru: Equal ke dusri taraf jaate hi +5 ka kya hota hai?\nRahul: minus ho jata hai... 7\nGuru: Shabaash, tumne inverse use kiya.'),
 ('c1000000-0000-4000-8000-000000000001','11111111-1111-4111-8111-111111111111','phone','seed-call-r2',
  now() - interval '1 day', now() - interval '1 day' + interval '7 minutes','ended',
  E'Guru: Namaste Rahul! 1 se 10 mein, linear equations mein kitna confident ho?\nRahul: 3\nGuru: x + 8 = 15, x kya hoga?\nRahul: 23\nGuru: Chalo check karte hain. +8 ko dusri taraf le jaane ke liye kya karna padega?\nRahul: plus karna?\nGuru: Ek step saath karte hain: dono taraf se 8 ghatao. Ab kya bacha?\nRahul: 7\nGuru: Bahut accha, tumne step likha. x - 3 = 7, x kya hoga?\nRahul: 4\nGuru: Chalo check karte hain. -3 ko dusri taraf le jaao toh uska sign kya banega?\nRahul: plus 3... toh 10\nGuru: Shabaash! Ab kitna confident ho, 1 se 10 mein?\nRahul: 4'),
 ('c2000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','phone','seed-call-p1',
  now() - interval '2 days', now() - interval '2 days' + interval '6 minutes','ended',
  E'Guru: Namaste Priya! -4 + 7 kitna hoga?\nPriya: minus 11\nGuru: Chalo check karte hain. -4 se 7 kadam aage jaoge toh kahan pahunchoge?\nPriya: 3\nGuru: Bahut accha! x - 6 = 2, x kya hoga?\nPriya: minus 4\nGuru: -6 ko dusri taraf le jaao toh sign kya hoga?\nPriya: plus... 8'),
 ('c3000000-0000-4000-8000-000000000001','33333333-3333-4333-8333-333333333333','phone','seed-call-a1',
  now() - interval '1 day', now() - interval '1 day' + interval '5 minutes','ended',
  E'Guru: Hi Aman! If x = 2, what is 3(x + 2)?\nAman: 8\nGuru: Let''s check. The 3 multiplies everything inside the bracket. What is 3 times 2, and 3 times x?\nAman: 6 and 6... so 12\nGuru: Great, you multiplied both terms.'),
 ('c4000000-0000-4000-8000-000000000001','44444444-4444-4444-8444-444444444444','phone','seed-call-s1',
  now() - interval '2 days', now() - interval '2 days' + interval '5 minutes','ended',
  E'Guru: Namaste Sneha! 3 + 4 = ___ + 2, khaali jagah mein kya aayega?\nSneha: 7\nGuru: Chalo check karte hain. Equal ka matlab dono taraf barabar. Left side kitna hai?\nSneha: 7... toh 5 + 2. 5!\nGuru: Bahut accha!'),
 ('c5000000-0000-4000-8000-000000000001','55555555-5555-4555-8555-555555555555','phone','seed-call-k1',
  now() - interval '3 days', now() - interval '3 days' + interval '6 minutes','ended',
  E'Guru: Namaste Kabir! 5x = 20, x kya hoga?\nKabir: 20\nGuru: Chalo check karte hain. 5x ka matlab 5 guna x. x akela kaise hoga?\nKabir: 5 se divide... 4\nGuru: Shabaash!');

insert into attempts(session_id,question_id,student_answer,correct,misconception_id,hint_level,created_at) values
 ('c1000000-0000-4000-8000-000000000002','q_001','minus 1',false,'neg_number_confusion',1,now() - interval '3 days' + interval '1 minute'),
 ('c1000000-0000-4000-8000-000000000002','q_001','minus 5',true,null,1,now() - interval '3 days' + interval '2 minutes'),
 ('c1000000-0000-4000-8000-000000000002','q_017','17',false,'adds_instead_of_inverse',1,now() - interval '3 days' + interval '3 minutes'),
 ('c1000000-0000-4000-8000-000000000002','q_017','7',true,null,1,now() - interval '3 days' + interval '4 minutes'),
 ('c1000000-0000-4000-8000-000000000001','q_020','23',false,'adds_instead_of_inverse',1,now() - interval '1 day' + interval '1 minute'),
 ('c1000000-0000-4000-8000-000000000001','q_020','plus karna?',false,'adds_instead_of_inverse',2,now() - interval '1 day' + interval '2 minutes'),
 ('c1000000-0000-4000-8000-000000000001','q_020','7',true,null,2,now() - interval '1 day' + interval '3 minutes'),
 ('c1000000-0000-4000-8000-000000000001','q_018','4',false,'sign_not_flipped',1,now() - interval '1 day' + interval '4 minutes'),
 ('c1000000-0000-4000-8000-000000000001','q_018','plus 3 toh 10',true,null,1,now() - interval '1 day' + interval '5 minutes'),
 ('c2000000-0000-4000-8000-000000000001','q_002','minus 11',false,'neg_number_confusion',1,now() - interval '2 days' + interval '1 minute'),
 ('c2000000-0000-4000-8000-000000000001','q_002','3',true,null,1,now() - interval '2 days' + interval '2 minutes'),
 ('c2000000-0000-4000-8000-000000000001','q_021','minus 4',false,'sign_not_flipped',1,now() - interval '2 days' + interval '3 minutes'),
 ('c2000000-0000-4000-8000-000000000001','q_021','8',true,null,1,now() - interval '2 days' + interval '4 minutes'),
 ('c3000000-0000-4000-8000-000000000001','q_032','8',false,'distributes_partially',1,now() - interval '1 day' + interval '1 minute'),
 ('c3000000-0000-4000-8000-000000000001','q_032','12',true,null,1,now() - interval '1 day' + interval '2 minutes'),
 ('c4000000-0000-4000-8000-000000000001','q_009','7',false,'equals_as_answer',1,now() - interval '2 days' + interval '1 minute'),
 ('c4000000-0000-4000-8000-000000000001','q_009','5',true,null,1,now() - interval '2 days' + interval '2 minutes'),
 ('c5000000-0000-4000-8000-000000000001','q_022','20',false,'coefficient_ignored',1,now() - interval '3 days' + interval '1 minute'),
 ('c5000000-0000-4000-8000-000000000001','q_022','4',true,null,1,now() - interval '3 days' + interval '2 minutes');

insert into confidence_logs(session_id,topic_id,phase,value,created_at) values
 ('c1000000-0000-4000-8000-000000000002','alg_linear_eq','before',2,now() - interval '3 days'),
 ('c1000000-0000-4000-8000-000000000002','alg_linear_eq','after',3,now() - interval '3 days' + interval '6 minutes'),
 ('c1000000-0000-4000-8000-000000000001','alg_linear_eq','before',3,now() - interval '1 day'),
 ('c1000000-0000-4000-8000-000000000001','alg_linear_eq','after',4,now() - interval '1 day' + interval '7 minutes'),
 ('c2000000-0000-4000-8000-000000000001','num_negatives','before',4,now() - interval '2 days'),
 ('c2000000-0000-4000-8000-000000000001','num_negatives','after',5,now() - interval '2 days' + interval '6 minutes'),
 ('c3000000-0000-4000-8000-000000000001','alg_distribution','before',7,now() - interval '1 day'),
 ('c3000000-0000-4000-8000-000000000001','alg_distribution','after',6,now() - interval '1 day' + interval '5 minutes'),
 ('c4000000-0000-4000-8000-000000000001','alg_expressions','before',5,now() - interval '2 days'),
 ('c4000000-0000-4000-8000-000000000001','alg_expressions','after',6,now() - interval '2 days' + interval '5 minutes'),
 ('c5000000-0000-4000-8000-000000000001','alg_linear_eq','before',6,now() - interval '3 days'),
 ('c5000000-0000-4000-8000-000000000001','alg_linear_eq','after',7,now() - interval '3 days' + interval '6 minutes');

insert into summaries(session_id,audience,language,body,created_at) values
 ('c1000000-0000-4000-8000-000000000001','teacher','en',
  E'Improved: solved x - 3 = 7 after one nudge about the sign.\nStill weak: adds instead of using the inverse (x + 8 = 15 -> 23).\nClass action: a 5-minute "balance scale" warm-up on undoing + and -.',now() - interval '1 day' + interval '8 minutes'),
 ('c1000000-0000-4000-8000-000000000001','parent','hi',
  E'आज राहुल ने समीकरण हल करने का अभ्यास किया।\nउसने एक सवाल में चिह्न बदलना खुद सही किया।\nघर पर उससे पूछिए कि "+8 को दूसरी तरफ़ ले जाएँ तो क्या होता है?"',now() - interval '1 day' + interval '8 minutes'),
 ('c2000000-0000-4000-8000-000000000001','teacher','en',
  E'Improved: used a number line to get -4 + 7 = 3.\nStill weak: negative number rules (answered -11 first).\nClass action: number-line jumps with signed steps.',now() - interval '2 days' + interval '7 minutes'),
 ('c2000000-0000-4000-8000-000000000001','parent','hi',
  E'आज प्रिया ने ऋणात्मक संख्याओं का अभ्यास किया।\nउसने संख्या रेखा से सही उत्तर निकाला।\nघर पर सीढ़ियों पर ऊपर-नीचे गिनती का खेल खेलिए।',now() - interval '2 days' + interval '7 minutes'),
 ('c3000000-0000-4000-8000-000000000001','teacher','en',
  E'Improved: expanded 3(x + 2) correctly after a prompt.\nStill weak: partial distribution (multiplies only the first term).\nClass action: "arrow from the outside number to every term" drill.',now() - interval '1 day' + interval '6 minutes'),
 ('c3000000-0000-4000-8000-000000000001','parent','en',
  E'Aman practised brackets in algebra today.\nHe fixed his own answer once he multiplied both terms.\nAt home, ask him to explain why 3(x + 2) is not 3x + 2.',now() - interval '1 day' + interval '6 minutes'),
 ('c4000000-0000-4000-8000-000000000001','teacher','en',
  E'Improved: balanced 3 + 4 = ___ + 2 once she read "=" as "same as".\nStill weak: treats "=" as "the answer comes next".\nClass action: true/false equations like 7 = 5 + 2.',now() - interval '2 days' + interval '6 minutes'),
 ('c4000000-0000-4000-8000-000000000001','parent','hi',
  E'आज स्नेहा ने बराबर के चिह्न का मतलब समझा।\nउसने एक सवाल खुद सही किया।\nघर पर पूछिए: "क्या 7 = 5 + 2 सही है?"',now() - interval '2 days' + interval '6 minutes'),
 ('c5000000-0000-4000-8000-000000000001','teacher','en',
  E'Improved: divided by the coefficient in 5x = 20 after a hint.\nStill weak: sometimes ignores the coefficient.\nClass action: read "5x" aloud as "5 times x" before solving.',now() - interval '3 days' + interval '7 minutes'),
 ('c5000000-0000-4000-8000-000000000001','parent','hi',
  E'आज कबीर ने समीकरण हल किए।\nउसने 5x = 20 में सही तरीका ढूँढा।\nघर पर उसे अपने स्टेप्स बोलकर समझाने को कहिए।',now() - interval '3 days' + interval '7 minutes');

insert into memory_facts(student_id,kind,content,confidence,source_session,created_at) values
 ('11111111-1111-4111-8111-111111111111','misconception','{"id":"adds_instead_of_inverse","evidence":"x + 5 = 12 -> 17"}',0.85,'c1000000-0000-4000-8000-000000000002',now() - interval '3 days'),
 ('11111111-1111-4111-8111-111111111111','misconception','{"id":"neg_number_confusion","evidence":"-2 - 3 -> minus 1"}',0.7,'c1000000-0000-4000-8000-000000000002',now() - interval '3 days'),
 ('11111111-1111-4111-8111-111111111111','strategy','{"id":"step_by_step","evidence":"solved after doing one step together"}',0.75,'c1000000-0000-4000-8000-000000000001',now() - interval '1 day'),
 ('11111111-1111-4111-8111-111111111111','misconception','{"id":"adds_instead_of_inverse","evidence":"x + 8 = 15 -> 23"}',0.9,'c1000000-0000-4000-8000-000000000001',now() - interval '1 day'),
 ('11111111-1111-4111-8111-111111111111','goal','{"text":"Feel ready for the unit test on equations"}',0.8,'c1000000-0000-4000-8000-000000000001',now() - interval '1 day'),
 ('22222222-2222-4222-8222-222222222222','misconception','{"id":"neg_number_confusion","evidence":"-4 + 7 -> minus 11"}',0.8,'c2000000-0000-4000-8000-000000000001',now() - interval '2 days'),
 ('22222222-2222-4222-8222-222222222222','strategy','{"id":"visual","evidence":"used a number line"}',0.7,'c2000000-0000-4000-8000-000000000001',now() - interval '2 days'),
 ('33333333-3333-4333-8333-333333333333','misconception','{"id":"distributes_partially","evidence":"3(x + 2) with x=2 -> 8"}',0.85,'c3000000-0000-4000-8000-000000000001',now() - interval '1 day'),
 ('44444444-4444-4444-8444-444444444444','misconception','{"id":"equals_as_answer","evidence":"3 + 4 = ___ + 2 -> 7"}',0.85,'c4000000-0000-4000-8000-000000000001',now() - interval '2 days'),
 ('55555555-5555-4555-8555-555555555555','misconception','{"id":"coefficient_ignored","evidence":"5x = 20 -> 20"}',0.85,'c5000000-0000-4000-8000-000000000001',now() - interval '3 days'),
 ('55555555-5555-4555-8555-555555555555','strategy','{"id":"worked_example","evidence":"followed the 5-times-x hint"}',0.6,'c5000000-0000-4000-8000-000000000001',now() - interval '3 days');

-- History for "over time" charts (Rahul's earlier arc + one point for others)
insert into learning_snapshots(student_id,session_id,kind,key,value,created_at) values
 ('11111111-1111-4111-8111-111111111111','c1000000-0000-4000-8000-000000000002','mastery','alg_linear_eq',0.22,now() - interval '3 days' + interval '6 minutes'),
 ('11111111-1111-4111-8111-111111111111','c1000000-0000-4000-8000-000000000002','mastery','num_negatives',0.28,now() - interval '3 days' + interval '6 minutes'),
 ('11111111-1111-4111-8111-111111111111','c1000000-0000-4000-8000-000000000002','misconception','adds_instead_of_inverse',0.55,now() - interval '3 days' + interval '6 minutes'),
 ('11111111-1111-4111-8111-111111111111','c1000000-0000-4000-8000-000000000002','misconception','neg_number_confusion',0.45,now() - interval '3 days' + interval '6 minutes'),
 ('11111111-1111-4111-8111-111111111111','c1000000-0000-4000-8000-000000000001','mastery','alg_linear_eq',0.30,now() - interval '1 day' + interval '7 minutes'),
 ('11111111-1111-4111-8111-111111111111','c1000000-0000-4000-8000-000000000001','misconception','adds_instead_of_inverse',0.80,now() - interval '1 day' + interval '7 minutes'),
 ('11111111-1111-4111-8111-111111111111','c1000000-0000-4000-8000-000000000001','misconception','sign_not_flipped',0.30,now() - interval '1 day' + interval '7 minutes'),
 ('22222222-2222-4222-8222-222222222222','c2000000-0000-4000-8000-000000000001','mastery','num_negatives',0.35,now() - interval '2 days' + interval '6 minutes'),
 ('22222222-2222-4222-8222-222222222222','c2000000-0000-4000-8000-000000000001','misconception','neg_number_confusion',0.60,now() - interval '2 days' + interval '6 minutes'),
 ('33333333-3333-4333-8333-333333333333','c3000000-0000-4000-8000-000000000001','mastery','alg_distribution',0.34,now() - interval '1 day' + interval '5 minutes'),
 ('33333333-3333-4333-8333-333333333333','c3000000-0000-4000-8000-000000000001','misconception','distributes_partially',0.70,now() - interval '1 day' + interval '5 minutes'),
 ('44444444-4444-4444-8444-444444444444','c4000000-0000-4000-8000-000000000001','mastery','alg_expressions',0.38,now() - interval '2 days' + interval '5 minutes'),
 ('44444444-4444-4444-8444-444444444444','c4000000-0000-4000-8000-000000000001','misconception','equals_as_answer',0.65,now() - interval '2 days' + interval '5 minutes'),
 ('55555555-5555-4555-8555-555555555555','c5000000-0000-4000-8000-000000000001','mastery','alg_linear_eq',0.58,now() - interval '3 days' + interval '6 minutes'),
 ('55555555-5555-4555-8555-555555555555','c5000000-0000-4000-8000-000000000001','misconception','coefficient_ignored',0.55,now() - interval '3 days' + interval '6 minutes');

-- A next-day plan for Rahul from yesterday's session
insert into plans(id,student_id,created_at,valid_from,valid_to) values
 ('d1000000-0000-4000-8000-000000000001','11111111-1111-4111-8111-111111111111',now() - interval '1 day',current_date,current_date + 2);
insert into plan_items(plan_id,day,topic_id,type,n_questions) values
 ('d1000000-0000-4000-8000-000000000001',1,'num_negatives','guided',3),
 ('d1000000-0000-4000-8000-000000000001',1,'alg_linear_eq','review',3),
 ('d1000000-0000-4000-8000-000000000001',2,'alg_linear_eq','independent',3),
 ('d1000000-0000-4000-8000-000000000001',3,'alg_multistep','guided',3);

insert into audit_log(actor,action,entity,entity_id,created_at) values
 ('teacher:Ms. Sharma','view','student','11111111-1111-4111-8111-111111111111',now() - interval '20 hours'),
 ('guardian:Sunita','view','parent_update','11111111-1111-4111-8111-111111111111',now() - interval '18 hours'),
 ('system','summary_created','session','c1000000-0000-4000-8000-000000000001',now() - interval '1 day' + interval '8 minutes');

-- Seeded sessions predate the ADDITIVE sessions.topic_id column: set it from what was practised.
update sessions s set topic_id = x.topic_id
from (select distinct on (a.session_id) a.session_id, q.topic_id
      from attempts a join questions q on q.id = a.question_id
      group by a.session_id, q.topic_id order by a.session_id, count(*) desc) x
where x.session_id = s.id and s.topic_id is null;
