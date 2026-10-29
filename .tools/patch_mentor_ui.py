from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:70])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


edit("web/components/SimpleView.tsx", [
    ('''  { id: "coach", icon: Sparkles, hint: "Tell Guru what you want to improve — any subject, exam, skill or goal. It remembers your journey." },
  { id: "maths", icon: Calculator, hint: "Maths drills: Guru finds why an answer is wrong and fixes it with hints." },
  { id: "english", icon: Languages, hint: "Speak freely; Guru gently fixes one mistake at a time." },''',
     '''  { id: "coach", icon: Sparkles, hint: "Talk about anything: studies, career, work, confidence, habits. Guru understands the problem, finds the cause, gives one next step and follows up every call." },
  { id: "english", icon: Languages, hint: "Speaking practice: Guru gently fixes one mistake at a time." },
  { id: "maths", icon: Calculator, hint: "Maths drills: Guru finds why an answer is wrong and fixes it with hints." },'''),
])
edit("web/components/GoalsPanel.tsx", [
    ('''coach: "Open coaching", maths: "Maths", english: "English speaking"''',
     '''coach: "Mentor: any problem", maths: "Maths practice", english: "English speaking"'''),
    ('''  coach: "Score 90 in my board exams",''', '''  coach: "Get my first job in tech",'''),
])

edit("web/app/start/page.tsx", [
    ('''  const [grade, setGrade] = useState("");''',
     '''  const [about, setAbout] = useState("");
  const [grade, setGrade] = useState("");'''),
    ('''        body: { first_name: name.trim(), grade: grade ? Number(grade) : null, language: language || null,''',
     '''        body: { first_name: name.trim(), about: about || null,
                grade: about === "School student" && grade ? Number(grade) : null, language: language || null,'''),
    ('''            <label htmlFor="grade" className="mb-1.5 block text-sm font-medium">Class <span className="text-muted">(optional)</span></label>
            <select id="grade" value={grade} onChange={(e) => setGrade(e.target.value)} className={field}>
              <option value="">Not in school / skip</option>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => <option key={g} value={g}>Class {g}</option>)}
            </select>''',
     '''            <label htmlFor="about" className="mb-1.5 block text-sm font-medium">About you <span className="text-muted">(optional)</span></label>
            <select id="about" value={about} onChange={(e) => setAbout(e.target.value)} className={field}>
              {ABOUT.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
            </select>
            {about === "School student" && (
              <select aria-label="Class" value={grade} onChange={(e) => setGrade(e.target.value)} className={`${field} mt-2`}>
                <option value="">Class (optional)</option>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => <option key={g} value={g}>Class {g}</option>)}
              </select>
            )}'''),
    ('''const LANGS = [''',
     '''// Guru mentors anyone: not only school classes
const ABOUT = [
  { value: "", label: "Prefer not to say" },
  { value: "School student", label: "School student" },
  { value: "College student", label: "College student" },
  { value: "Working professional", label: "Working professional" },
  { value: "Looking for a job", label: "Looking for a job" },
  { value: "Preparing for an exam", label: "Preparing for an exam" },
  { value: "Business owner", label: "Business / self-employed" },
  { value: "Homemaker", label: "Homemaker" },
];

const LANGS = ['''),
    ('''Tell Guru a little about you. Then just talk — about any subject, exam, skill or goal. Guru remembers every call and helps you improve day by day.''',
     '''Tell Guru a little about you. Then just talk about anything: studies, career, work, confidence or habits. Guru understands your problem, gives you one next step, and follows up every call.'''),
])
print("ok")
