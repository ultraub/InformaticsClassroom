# Template Archive Manifest

**Archive Date**: November 4, 2025
**Reason**: Migration to React SPA
**Total Files Archived**: 21 HTML templates

## Archived Templates

### Auth Module (4 files)
- `auth_error.html` - Authentication error page
- `display.html` - Post-authentication display
- `index.html` - Landing page
- `login.html` - MSAL login page

### Classroom Module (16 files)
- `answerform.html` - Answer submission form
- `assignment.html` - Assignment viewing
- `base.html` - Base template
- `create_quiz.html` - Quiz creation form
- `exercise_form.html` - Exercise forms
- `exercise_review.html` - Exercise review
- `fhir.html` - FHIR data viewer
- `home.html` - Welcome page
- `layout.html` - Layout template
- `manage_users.html` - User management (migrated to React)
- `modify_quiz.html` - Quiz modification
- `quiz.html` - Quiz taking interface
- `studentcenter.html` - Student dashboard
- `submit_answers.html` - Answer submission results
- `token_generation.html` - Token generation UI

### ML Model Game Module (1 file)
- `models.html` - ML model game

### Network Builder Module (1 file)
- `networkgame.html` - OHDSI network game

## Rollback Instructions

If you need to restore the old Flask templates:

```bash
# Restore all templates
cp -r informatics_classroom/templates_archive/auth/*.html informatics_classroom/auth/templates/
cp -r informatics_classroom/templates_archive/classroom/*.html informatics_classroom/classroom/templates/
cp -r informatics_classroom/templates_archive/mlmodelgame/*.html informatics_classroom/mlmodelgame/templates/
cp -r informatics_classroom/templates_archive/networkbuilder/*.html informatics_classroom/networkbuilder/templates/

# Disable React UI
export USE_REACT_UI=false

# Restart Flask
flask run
```

## Migration Status

- ✅ Templates archived safely
- ✅ Archive manifest created
- ⏳ JWT authentication integration
- ⏳ React SPA routing configuration
- ⏳ Feature flag implementation
- ⏳ Role-based rollout

## Deletion Schedule

**Planned Deletion**: Week 7 (after successful hard cutover)
**Condition**: All features verified working in React + No critical issues for 1 week

---

**DO NOT DELETE THIS ARCHIVE** until migration is complete and stable for at least 1 week.
