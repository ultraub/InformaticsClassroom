# UI Cleanup Analysis - Deprecated Code Removal Plan

**Analysis Date**: November 7, 2025
**Migration Context**: Postgres migration + React SPA (informatics-classroom-ui) now active
**Status**: Migration complete, React UI fully operational

---

## Executive Summary

After migrating to PostgreSQL and the new React-based `informatics-classroom-ui`, significant old Flask template-based UI code can be safely removed. This analysis identifies **~21 HTML templates, 2 route files (~2,300 lines), and deprecated static assets** that are no longer used.

**Key Findings**:
- ✅ **Templates already archived**: 21 HTML files moved to `templates_archive/` on Nov 4, 2025
- ⚠️ **Active deprecated routes**: Still serving old HTML templates that should be removed
- ✅ **Static assets archived**: Old CSS/JS already moved to `static_archive/`
- 🔴 **Route cleanup needed**: Old route files and HTML-serving endpoints need removal

---

## 1. Template Files Analysis

### Already Archived (Safe - Ready for Deletion)

**Location**: `informatics_classroom/templates_archive/`
**Archive Date**: November 4, 2025
**Total Files**: 21 HTML templates
**Disk Space**: ~50KB

#### Auth Module Templates (4 files)
```
templates_archive/auth/
├── auth_error.html        ← Replaced by React error handling
├── display.html           ← Replaced by React dashboard
├── index.html             ← Replaced by React landing page
└── login.html             ← Replaced by React MSAL login flow
```

**React Replacements**:
- `auth_error.html` → React: `/src/components/auth/ErrorBoundary.tsx`
- `login.html` → React: `/src/components/auth/LoginForm.tsx`
- `display.html` → React: `/src/pages/Dashboard.tsx`

#### Classroom Module Templates (16 files)
```
templates_archive/classroom/
├── answerform.html         ← React: QuizTaking component
├── assignment.html         ← React: Assignments page
├── base.html              ← React: Layout component
├── create_quiz.html       ← React: QuizCreator page
├── exercise_form.html     ← React: ExerciseForm component
├── exercise_review.html   ← React: ExerciseReview page
├── fhir.html              ← React: FHIRViewer component
├── home.html              ← React: Dashboard page
├── layout.html            ← React: Layout component
├── manage_users.html      ← React: Users page (COMPLETED)
├── modify_quiz.html       ← React: QuizEditor page
├── quiz.html              ← React: QuizTaking page
├── studentcenter.html     ← React: StudentDashboard
├── submit_answers.html    ← React: QuizSubmission
└── token_generation.html  ← React: TokenGenerator page
```

**All Replaced**: Every archived template has a functional React equivalent in `informatics-classroom-ui/src/`

#### ML Model Game Template (1 file)
```
templates_archive/mlmodelgame/
└── models.html            ← ML game interface (consider future React migration)
```

#### Network Builder Template (1 file)
```
templates_archive/networkbuilder/
└── networkgame.html       ← OHDSI network game (consider future React migration)
```

### Still Active (Need Removal)

**Location**: `informatics_classroom/templates/`
**Files**: 3 minimal templates
**Purpose**: Legacy fallback/transition support

```
informatics_classroom/templates/
├── home.html          ← Backend status page (keep for now - useful debug tool)
├── login.html         ← MSAL login redirect (still in use by auth/routes.py:43)
└── auth_error.html    ← Auth error fallback (still in use by auth/routes.py:66)
```

**Recommendation**:
- ✅ **KEEP**: `home.html` - Useful backend status dashboard for debugging
- ⚠️ **CONDITIONAL**: `login.html` & `auth_error.html` - Check if still needed for MSAL flow

---

## 2. Route Files Analysis

### Deprecated Route Files (Safe for Deletion)

#### routes_old.py
- **Location**: `informatics_classroom/classroom/routes_old.py`
- **Lines**: 1,227
- **Created**: Original Flask UI implementation
- **Status**: 🔴 **SAFE TO DELETE**

**Contains**:
- 15+ HTML-serving GET routes (`/generate-token`, `/create-quiz`, `/modify-quiz`, etc.)
- Old API endpoints that have been migrated to `api_routes.py`
- Legacy session-based authentication logic

#### routes_updated_01172025.py
- **Location**: `informatics_classroom/classroom/routes_updated_01172025.py`
- **Lines**: 1,080
- **Created**: January 17, 2025 (intermediate migration version)
- **Status**: 🔴 **SAFE TO DELETE**

**Contains**:
- Same HTML-serving routes as routes_old.py
- Partial API migration (superseded by api_routes.py)
- Transition code no longer needed

### Active Routes File (Needs Cleanup)

#### routes.py (Current)
- **Location**: `informatics_classroom/classroom/routes.py`
- **Lines**: 1,360
- **Status**: ⚠️ **NEEDS CLEANUP**

**HTML-Serving Routes to Remove** (11 routes):

```python
# Line 183
@classroom_bp.route("/generate-token", methods=["GET"])
→ Serves: token_generation.html (archived)
→ React Replacement: /src/pages/TokenGenerator.tsx

# Line 220
@classroom_bp.route("/create-quiz", methods=["GET"])
→ Serves: create_quiz.html (archived)
→ React Replacement: /src/pages/QuizCreator.tsx

# Line 227
@classroom_bp.route("/modify-quiz", methods=["GET"])
→ Serves: modify_quiz.html (archived)
→ React Replacement: /src/pages/QuizEditor.tsx

# Line 238
@classroom_bp.route("/submit-answers", methods=["GET"])
→ Serves: submit_answers.html (archived)
→ React Replacement: /src/pages/QuizSubmission.tsx

# Line 245
@classroom_bp.route("/manage-users", methods=["GET"])
→ Serves: manage_users.html (archived)
→ React Replacement: /src/pages/Users.tsx ✅ FULLY FUNCTIONAL

# Line 258
@classroom_bp.route("/exercise-review", methods=["GET"])
→ Serves: exercise_review.html (archived)
→ React Replacement: /src/pages/ExerciseReview.tsx

# Line 742
@classroom_bp.route('/home')
→ Serves: home.html (backend status - KEEP for debugging)

# Line 749
@classroom_bp.route("/quiz", methods=['GET','POST'])
→ Serves: quiz.html (archived)
→ React Replacement: /src/pages/QuizTaking.tsx

# Line 958
@classroom_bp.route("/assignment", methods=["GET"])
→ Serves: assignment.html (archived)
→ React Replacement: /src/pages/Assignments.tsx

# Line 1302
@classroom_bp.route("/fhir", methods=["GET"])
→ Serves: fhir.html (archived)
→ React Replacement: /src/components/FHIRViewer.tsx
```

**Lines to Remove**: ~200 lines of HTML-serving route code
**Impact**: No functional impact - all replaced by React + API routes

---

## 3. Static Assets Analysis

### Already Archived

**Location**: `informatics_classroom/static_archive/`
**Status**: ✅ Previously archived (exact contents need verification)

### Still Active

**Location**: `informatics_classroom/classroom/static/`
**File**: `style.css` (323 bytes)

**Contents**:
```css
.table { border-spacing: 2; margin: 1rem; background-color: #f5f5f5; }
.table__row:nth-child(even) { background-color:#e5e5e5; }
.table__header { text-align:left; background-color:#d5d5d5; }
.table__cell { padding:8px }
.correct__cell { background-color: rgb(127, 255, 142); padding:8px }
```

**Analysis**:
- Used by archived templates only (exercise_review.html tables)
- NOT used by React UI (has own Tailwind CSS)
- 🔴 **SAFE TO DELETE** or move to archive

---

## 4. Auth Routes Analysis

**File**: `informatics_classroom/auth/routes.py`

### HTML-Serving Routes Still Active

```python
# Line 43
@auth_bp.route("/login")
→ Serves: login.html (MSAL auth flow - still needed?)
→ Check: Does React handle MSAL entirely, or does it redirect here?

# Line 59
@auth_bp.route(Config.REDIRECT_PATH)
→ Serves: auth_error.html on auth failures
→ May still be needed for MSAL callback errors

# Line 667
@auth_bp.route("/graphcall")
→ Serves: display.html (graph data display)
→ 🔴 DEPRECATED - React uses /api/auth/session instead
```

**Recommendation**:
- ⚠️ Investigate MSAL flow to confirm if `/login` and callback error handling can be fully React-based
- 🔴 Remove `/graphcall` route (line 667) - deprecated by React

---

## 5. Module-Specific Routes

### ML Model Game
**File**: `informatics_classroom/mlmodelgame/routes.py`

```python
# Still serving: mlmodelgame/templates/models.html
@mlmodel_bp.route('/models')
```

**Status**: 🟡 **KEEP for now** - No React replacement yet, game still functional

### Network Builder
**File**: `informatics_classroom/networkbuilder/routes.py`

```python
# Still serving: networkbuilder/templates/networkgame.html
@network_bp.route('/networkgame')
```

**Status**: 🟡 **KEEP for now** - No React replacement yet, game still functional

---

## 6. Safety Analysis

### Risk Assessment

#### 🟢 LOW RISK (Safe Immediate Deletion)

1. **Archived templates** (`templates_archive/`) - Already moved, 100% replaced
2. **Old route files** (`routes_old.py`, `routes_updated_01172025.py`) - Not imported anywhere
3. **classroom/static/style.css** - Only referenced by archived templates

**Estimated Impact**: None - all functionality replaced by React UI

#### 🟡 MEDIUM RISK (Requires Testing)

1. **HTML-serving routes in routes.py** - Need to verify no legacy direct URL access
2. **Auth templates** (`login.html`, `auth_error.html`) - Verify MSAL flow fully React-based

**Testing Required**:
- Test MSAL authentication flow end-to-end
- Verify no external links pointing to old routes
- Check if any mobile apps/scripts hit old endpoints

#### 🔴 HIGH RISK (Do Not Remove)

1. **API routes** (all `/api/*` endpoints) - Actively used by React UI
2. **mlmodelgame/networkbuilder** - Still functional standalone features
3. **home.html** - Useful backend status dashboard

---

## 7. Removal Plan

### Phase 1: Archive Cleanup (Immediate - Low Risk)

**Delete Archived Templates Directory**:
```bash
rm -rf informatics_classroom/templates_archive/
```

**Estimated Savings**: ~50KB, removes 21 unused HTML files
**Risk**: None - already archived and replaced
**Rollback**: Restore from git history if needed

---

### Phase 2: Old Route Files (Immediate - Low Risk)

**Delete Deprecated Route Files**:
```bash
rm informatics_classroom/classroom/routes_old.py
rm informatics_classroom/classroom/routes_updated_01172025.py
```

**Estimated Savings**: ~2,300 lines of code
**Risk**: None - not imported by `__init__.py`
**Rollback**: Restore from git history if needed

---

### Phase 3: Static Assets (Immediate - Low Risk)

**Delete Unused CSS**:
```bash
rm informatics_classroom/classroom/static/style.css
rmdir informatics_classroom/classroom/static/  # if empty
```

**Estimated Savings**: 323 bytes
**Risk**: None - only used by archived templates
**Rollback**: Restore from git history if needed

---

### Phase 4: HTML-Serving Routes (After Testing - Medium Risk)

**File**: `informatics_classroom/classroom/routes.py`

**Routes to Remove** (with line numbers):

```python
# DELETE THESE ROUTES:
# Line 183-217: /generate-token (GET) → render_template("token_generation.html")
# Line 220-225: /create-quiz (GET) → render_template("create_quiz.html")
# Line 227-236: /modify-quiz (GET) → render_template("modify_quiz.html")
# Line 238-243: /submit-answers (GET) → render_template("submit_answers.html")
# Line 245-256: /manage-users (GET) → render_template("manage_users.html")
# Line 258-264: /exercise-review (GET) → render_template("exercise_review.html")
# Line 749-751: /quiz (GET/POST) → render_template("quiz.html")
# Line 958-975: /assignment (GET) → render_template("assignment.html")
# Line 1302-1307: /fhir (GET) → render_template("fhir.html")

# KEEP THIS ROUTE (useful debug tool):
# Line 742-747: /home → render_template("home.html")
```

**Estimated Savings**: ~200 lines
**Risk**: Medium - verify no direct URL usage
**Testing Plan**:
1. Search codebase for hardcoded URLs to these routes
2. Test all React pages to confirm they use API routes
3. Deploy to staging first, monitor for 404 errors

---

### Phase 5: Auth Route Cleanup (After MSAL Investigation - Medium Risk)

**File**: `informatics_classroom/auth/routes.py`

**Investigate First**:
```python
# Line 43: @auth_bp.route("/login")
# Line 59: @auth_bp.route(Config.REDIRECT_PATH)
```

**Conditional Deletion**:
```python
# Line 667-676: @auth_bp.route("/graphcall")
# → Safe to delete if React handles graph data via /api/auth/session
```

**Testing Plan**:
1. Test full MSAL login flow with React UI only
2. Verify auth error handling in React
3. Confirm `/graphcall` is unused (check logs)

---

### Phase 6: Template Files (After Route Removal - Low Risk)

**Delete Remaining Archived-Template References**:
```bash
# After removing all HTML-serving routes:
rm informatics_classroom/templates/home.html  # Keep if /home route kept
# Keep login.html and auth_error.html until MSAL investigation complete
```

---

## 8. Pre-Deletion Checklist

### Before Removing Anything

- [ ] **Backup current state**: Create git tag `pre-ui-cleanup`
- [ ] **Review git history**: Ensure templates_archive has proper lineage
- [ ] **Search codebase**: `grep -r "render_template" informatics_classroom/`
- [ ] **Check external refs**: Search docs for old route URLs
- [ ] **Test React UI**: Full end-to-end testing of all pages
- [ ] **Review logs**: Check for 404s on old routes (indicates usage)

### Testing Strategy

1. **Local Testing**:
   ```bash
   # Start React UI
   cd informatics-classroom-ui && npm run dev

   # Start Flask backend
   cd .. && python app.py

   # Test all major flows:
   # - Login/Auth
   # - Quiz creation/taking
   # - User management
   # - Token generation
   # - Exercise review
   ```

2. **Staging Deployment**:
   - Deploy to staging environment
   - Monitor for 1 week
   - Check error logs for template-related 404s
   - Verify no external integrations broken

3. **Production Rollout**:
   - Gradual removal (Phase 1 → Phase 6)
   - 1 week between phases
   - Rollback plan: git revert + redeploy

---

## 9. Estimated Impact

### Disk Space Savings
- **Templates**: ~50KB
- **Route files**: ~70KB
- **Static assets**: ~1KB (style.css only)
- **Total**: ~121KB (minimal but clean)

### Code Maintenance Benefits
- **Reduced confusion**: No duplicate route files
- **Clearer codebase**: Only active code remains
- **Faster onboarding**: New developers see only React UI
- **Reduced test surface**: Fewer routes to maintain

### Performance Impact
- **Negligible**: Flask still loads same modules
- **Slightly faster startup**: Fewer route registrations
- **Better caching**: Fewer static files to check

---

## 10. Rollback Plan

If issues arise after deletion:

### Emergency Rollback (Full Restore)
```bash
# Restore from git tag
git checkout pre-ui-cleanup

# Or restore specific files
git checkout pre-ui-cleanup -- informatics_classroom/templates_archive/
git checkout pre-ui-cleanup -- informatics_classroom/classroom/routes_old.py
```

### Partial Rollback (Specific Templates)
```bash
# If specific template needed
git show pre-ui-cleanup:informatics_classroom/templates_archive/classroom/manage_users.html > temp.html
# Copy to templates/ and restore route
```

### React UI Fallback (Worst Case)
```bash
# Disable React UI in .env
export USE_REACT_UI=false

# Restore all old templates
git checkout pre-ui-cleanup -- informatics_classroom/templates_archive/
cp -r informatics_classroom/templates_archive/classroom/* informatics_classroom/classroom/templates/
cp -r informatics_classroom/templates_archive/auth/* informatics_classroom/auth/templates/

# Restart Flask
flask run
```

---

## 11. Final Recommendations

### Immediate Actions (This Week)

✅ **Phase 1**: Delete `templates_archive/` directory
✅ **Phase 2**: Delete `routes_old.py` and `routes_updated_01172025.py`
✅ **Phase 3**: Delete `classroom/static/style.css`

**Command Sequence**:
```bash
# Create safety tag
git tag -a pre-ui-cleanup -m "Before UI cleanup - Nov 2025"
git push origin pre-ui-cleanup

# Phase 1: Remove archived templates
rm -rf informatics_classroom/templates_archive/

# Phase 2: Remove old route files
rm informatics_classroom/classroom/routes_old.py
rm informatics_classroom/classroom/routes_updated_01172025.py

# Phase 3: Remove unused static CSS
rm informatics_classroom/classroom/static/style.css
rmdir informatics_classroom/classroom/static/ 2>/dev/null || true

# Commit cleanup
git add -A
git commit -m "chore: remove deprecated UI templates and routes after React migration

- Deleted 21 archived HTML templates (templates_archive/)
- Removed old route files: routes_old.py, routes_updated_01172025.py
- Cleaned up unused static CSS (classroom/static/style.css)
- All functionality now handled by React UI (informatics-classroom-ui)

Rollback tag: pre-ui-cleanup"
git push origin main
```

### Near-Term Actions (Next 2 Weeks)

⚠️ **Phase 4**: Remove HTML-serving routes from `routes.py` (after testing)
⚠️ **Phase 5**: Investigate and clean up auth routes (after MSAL review)
⚠️ **Phase 6**: Final template cleanup

### Future Considerations

🟡 **ML Model Game**: Migrate to React component (optional)
🟡 **Network Builder**: Migrate to React component (optional)
✅ **home.html**: Keep as backend status dashboard (useful tool)

---

## 12. Success Criteria

### Cleanup Complete When:
- ✅ No template files in `templates_archive/`
- ✅ No old route files (`routes_old.py`, `routes_updated_01172025.py`)
- ✅ No unused static CSS files
- ✅ Only API routes remain in `routes.py` (+ optional `/home` debug route)
- ✅ All React UI functionality tested and working
- ✅ No 404 errors in production logs for old routes

### Quality Gates:
- **Zero regressions**: All existing functionality works
- **Clean git history**: Proper commit messages and tags
- **Documentation updated**: This analysis archived for reference
- **Team awareness**: Dev team informed of changes

---

## Appendix A: Route Inventory

### API Routes (Keep - Active)
All routes in `informatics_classroom/classroom/api_routes.py`:
- `/api/student/courses`, `/api/student/progress`, `/api/student/dashboard`
- `/api/quiz/details`, `/api/quiz/submit-answer`
- `/api/instructor/classes`, `/api/classes`, `/api/classes/<class_id>`
- `/api/quizzes/create`, `/api/quizzes/<quiz_id>/edit`, `/api/quizzes/<quiz_id>/update`
- `/api/quizzes/<quiz_id>`, `/api/classes/<class_id>/grades`
- `/api/instructor/quizzes`, `/api/instructor/class-modules`
- `/api/tokens/generate`, `/api/assignments/analyze`
- `/api/student/exercise-review`, `/api/classes/<class_id>/members`

### HTML Routes (Remove - Deprecated)
From `informatics_classroom/classroom/routes.py`:
- `/generate-token` (line 183)
- `/create-quiz` (line 220)
- `/modify-quiz` (line 227)
- `/submit-answers` (line 238)
- `/manage-users` (line 245)
- `/exercise-review` (line 258)
- `/quiz` (line 749)
- `/assignment` (line 958)
- `/fhir` (line 1302)

### Debug Routes (Keep - Useful)
- `/home` (line 742) - Backend status dashboard

---

**Analysis Complete**: November 7, 2025
**Next Review**: After Phase 3 completion
**Contact**: Development Team
