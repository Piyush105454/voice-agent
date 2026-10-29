from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:70])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


# First call for EVERY new person: warm greeting + which language to start in (Hindi, English or a mix)
edit("api/coach.py", [
    ('''    if not db.language_known(sid):
        return (f"Hi {n}! Main Guru hoon, aapka AI coach. " + ("Aapse milkar bahut khushi hui. " if first_call else "")
                + "Aap Hindi, English, ya dono mix mein baat karna pasand karoge?")''',
     '''    if first_call or not db.language_known(sid):
        return (f"Namaste {n}! Main Guru hoon, aapka AI mentor. Aapse milkar bahut khushi hui. "
                "Hum kis language mein baat shuru karein: Hindi, English, ya dono ka mix?")'''),
])
edit("api/prompts/voice_system_prompt.md", [
    ('''- If LANGUAGE above says unknown, the opening line asked it: when they answer, call set_language(session_id,
  language) once.''',
     '''- On a first call (or if LANGUAGE above says unknown) the opening line asked which language to start in: when
  they answer, call set_language(session_id, language) once.'''),
])

# Sign-up: for anyone (school, college, working, job seeking...), class only for school students
edit("web/app/start/page.tsx", [
    ('''  const [grade, setGrade] = useState("");''',
     '''  const [grade, setGrade] = useState("");
  const [about, setAbout] = useState("");'''),
    ('''body: { first_name: name.trim(), grade: grade ? Number(grade) : null, language: language || null,''',
     '''body: { first_name: name.trim(), grade: about === "School student" && grade ? Number(grade) : null,
                about: about || null, language: language || null,'''),
    ('''            <label htmlFor="grade" className="mb-1.5 block text-sm font-medium">Class <span className="text-muted">(optional)</span></label>
            <select id="grade" value={grade} onChange={(e) => setGrade(e.target.value)} className={field}>
              <option value="">Not in school / skip</option>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => <option key={g} value={g}>Class {g}</option>)}
            </select>''',
     '''            <label htmlFor="about" className="mb-1.5 block text-sm font-medium">You are <span className="text-muted">(optional)</span></label>
            <select id="about" value={about} onChange={(e) => setAbout(e.target.value)} className={field}>
              <option value="">Skip</option>
              {["School student", "College student", "Working professional", "Job seeker", "Business owner", "Other"]
                .map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            {about === "School student" && (
              <select aria-label="Class" value={grade} onChange={(e) => setGrade(e.target.value)} className={`${field} mt-2`}>
                <option value="">Class (optional)</option>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((g) => <option key={g} value={g}>Class {g}</option>)}
              </select>
            )}'''),
    ('''Tell Guru a little about you. Then just talk — about any subject, exam, skill or goal.''',
     '''Student, college, working or job hunting: tell Guru a little about you. Then just talk about any problem or goal: studies, career, work, skills, confidence.'''),
])
print("ok")
