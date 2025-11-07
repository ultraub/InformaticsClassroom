# Deferred Cleanup: Submit-Answers Code

**Date**: November 7, 2025
**Status**: PRESERVED - To be reviewed later
**Branch**: cleanup/deprecated-ui-code

---

## Overview

During the UI cleanup process, all submit-answers related code has been **PRESERVED** per user request. This document tracks what was kept and what still needs review for potential removal.

---

## Preserved Files

### Templates (Archived)

**Location**: `informatics_classroom/templates_archive/classroom/`

```
✅ PRESERVED:
├── submit_answers.html    (10,152 bytes) - Submit answers page template
└── answerform.html        (1,064 bytes) - Answer form component template
```

**Reason**: User requested to defer submit-answers cleanup until later review.

---

### Routes

**File**: `informatics_classroom/classroom/routes.py`

#### HTML-Serving Routes (PRESERVED)

```python
# Line 238-243
@classroom_bp.route("/submit-answers", methods=["GET"])
def submit_answers_page():
    """Render the submit answers page."""
    if not session.get("user"):
        return redirect(url_for("auth_bp.login"))
    return render_template("submit_answers.html", title="Submit Answers")
```

**Status**: ⚠️ **PRESERVED** - Serves archived template `submit_answers.html`
**React Replacement**: Likely exists in `/src/pages/QuizSubmission.tsx` or similar
**Action Required**: Verify React replacement works, then remove this route

#### API Routes (KEEP - Active)

```python
# Line 898-931
@classroom_bp.route("/submit-answer", methods=['POST'])
def submit_answer():
    """Handle individual answer submission"""
    # ~30 lines of submission logic
```

```python
# Line 933-956
@classroom_bp.route("/api/submit-answers", methods=["POST"])
def submit_answers():
    """Submit answers for a quiz."""
    # ~20 lines of batch submission logic
```

**Status**: ✅ **KEEP** - Active API endpoints used by React UI
**Do NOT Remove**: These are functional API routes

---

## What Was Removed (Nov 7, 2025)

For context, here's what was safely removed in this cleanup:

### Removed Templates
- All auth module templates (login.html, display.html, auth_error.html, index.html)
- All mlmodelgame templates (models.html)
- All networkbuilder templates (networkgame.html)
- Most classroom templates EXCEPT submit_answers.html and answerform.html:
  - ❌ assignment.html
  - ❌ base.html
  - ❌ create_quiz.html
  - ❌ exercise_form.html
  - ❌ exercise_review.html
  - ❌ fhir.html
  - ❌ home.html
  - ❌ layout.html
  - ❌ manage_users.html
  - ❌ modify_quiz.html
  - ❌ quiz.html
  - ❌ studentcenter.html
  - ❌ token_generation.html

### Removed Route Files
- ❌ `informatics_classroom/classroom/routes_old.py` (1,227 lines)
- ❌ `informatics_classroom/classroom/routes_updated_01172025.py` (1,080 lines)

### Removed Static Assets
- ❌ `informatics_classroom/classroom/static/style.css` (323 bytes)
- ❌ `informatics_classroom/classroom/static/` directory (now empty)

---

## Future Cleanup Plan

### Phase 1: Investigation (Next Session)

**Action Items**:
1. ✅ Test React UI quiz submission functionality
2. ✅ Verify `/api/submit-answers` (POST) is being used
3. ✅ Check if `/submit-answer` (POST) is still needed
4. ✅ Confirm `/submit-answers` (GET) is unused (React handles UI)

**Tools**:
```bash
# Check Flask logs for route usage
grep "GET /submit-answers" flask_server.log
grep "POST /submit-answer" flask_server.log
grep "POST /api/submit-answers" flask_server.log

# Search React code for API calls
cd informatics-classroom-ui
grep -r "submit-answer" src/
grep -r "/api/submit-answers" src/
```

### Phase 2: Removal (After Testing)

**If React handles all UI**:

1. **Remove HTML-serving route** (routes.py:238-243):
   ```python
   # DELETE:
   @classroom_bp.route("/submit-answers", methods=["GET"])
   def submit_answers_page():
       ...
   ```

2. **Archive templates** (already in templates_archive, can delete):
   ```bash
   rm informatics_classroom/templates_archive/classroom/submit_answers.html
   rm informatics_classroom/templates_archive/classroom/answerform.html
   ```

3. **KEEP API routes** - These are active:
   - ✅ `/submit-answer` (POST) - Line 898
   - ✅ `/api/submit-answers` (POST) - Line 933

---

## Testing Checklist

Before removing submit-answers code:

### React UI Testing
- [ ] Navigate to quiz submission page in React UI
- [ ] Submit answers to a quiz
- [ ] Verify submission completes successfully
- [ ] Check browser Network tab for API calls
- [ ] Confirm no calls to `/submit-answers` (GET) - old HTML route
- [ ] Confirm calls to `/api/submit-answers` (POST) - new API route

### Backend Testing
```bash
# Start Flask with logging
python app.py

# Monitor logs while testing React UI
tail -f flask_server.log | grep submit
```

### Expected Behavior
- ✅ React UI makes POST requests to `/api/submit-answers`
- ❌ No GET requests to `/submit-answers` (HTML route)
- ✅ API returns JSON responses
- ✅ Quiz submissions save to database

---

## Decision Matrix

| Route | Type | Status | Action |
|-------|------|--------|--------|
| `/submit-answers` (GET) | HTML | ⚠️ Deprecated | Remove after testing |
| `/submit-answer` (POST) | API | ✅ Active | **KEEP** |
| `/api/submit-answers` (POST) | API | ✅ Active | **KEEP** |
| `submit_answers.html` | Template | 🗄️ Archived | Delete after route removal |
| `answerform.html` | Template | 🗄️ Archived | Delete after route removal |

---

## Rollback Plan

If submit-answers functionality breaks:

### Emergency Restore
```bash
# Restore from pre-cleanup tag
git checkout pre-ui-cleanup -- informatics_classroom/templates_archive/classroom/submit_answers.html
git checkout pre-ui-cleanup -- informatics_classroom/templates_archive/classroom/answerform.html

# Ensure the GET route in routes.py:238 is still present (it is, we preserved it)
```

### Permanent Rollback (Worst Case)
```bash
# Merge in the preserved templates
cp informatics_classroom/templates_archive/classroom/submit_answers.html informatics_classroom/templates/
cp informatics_classroom/templates_archive/classroom/answerform.html informatics_classroom/templates/

# Restart Flask
flask run
```

---

## Notes

### Why Submit-Answers Was Preserved

User specifically requested:
> "do not remove anything on submit-answers yet. Make note of it and we will come back to it"

**Reasoning**: Likely needs additional testing or may have special requirements not yet migrated to React.

### Related Issues

- **Quiz Submission Flow**: Verify complete end-to-end quiz taking → submission → grading flow
- **Answer History**: Check if answerform.html has unique functionality not in React
- **Batch Submissions**: Confirm `/api/submit-answers` handles bulk answer submission correctly

---

## Completion Criteria

Submit-answers cleanup complete when:
- ✅ React UI handles all quiz submission
- ✅ No GET requests to `/submit-answers` in production logs
- ✅ API routes tested and working
- ✅ Templates deleted from templates_archive
- ✅ HTML-serving route removed from routes.py
- ✅ Zero regressions in quiz functionality

---

## Contact

**Created**: November 7, 2025
**Last Updated**: November 7, 2025
**Next Review**: After React UI quiz submission testing
**Owner**: Development Team
