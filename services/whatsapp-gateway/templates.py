IDLE_PROMPT = (
    "👋 Welcome to *QuickJobs!*\n\n"
    "Here's what you can do:\n\n"
    "📝 *hi* or *hello* — Register as a job seeker\n"
    "🔔 *START* — Re-subscribe to job alerts\n"
    "🔕 *STOP* — Unsubscribe from job alerts\n"
    "🗑️ *DELETE MY DATA* — Erase all your data (PDPA)\n\n"
    "_Send *hi* to get started!_"
)

WELCOME = (
    "👋 Welcome to *QuickJobs!*\n"
    "I'll help you find your next job opportunity.\n\n"
    "I'll ask you a few quick questions to build your profile.\n\n"
    "Available commands during registration:\n"
    "🔄 *RESTART* — Start registration over from the beginning\n"
    "🔕 *STOP* — Unsubscribe from alerts\n"
    "🗑️ *DELETE MY DATA* — Erase all your data\n\n"
    "Let's begin! What is your full name?"
)


def ask_skills(name: str) -> str:
    return (
        f"Nice to meet you, *{name}!* 🎉\n\n"
        "What are your main skills?\n"
        "_(e.g. Python, React, SQL — separate with commas)_"
    )


ASK_EXPERIENCE = (
    "What is your experience level?\n\n"
    "1️⃣ Junior\n"
    "2️⃣ Mid\n"
    "3️⃣ Senior\n"
    "4️⃣ Lead\n\n"
    "Reply with the number."
)

ASK_LOCATION = "What city or region are you based in? 📍"

ASK_SALARY = (
    "What is your expected monthly salary range? 💰\n\n"
    "Please enter as: *min-max* in LKR\n"
    "_(e.g. 80000-150000)_"
)

ASK_CV = (
    "Almost done! 📄\n\n"
    "Please send your CV as a *PDF* or *Word (.docx)* file.\n"
    "We'll use it to match you with the best jobs."
)


def onboarding_complete(name: str) -> str:
    return (
        f"🎉 You're all set, *{name}!*\n\n"
        "We'll notify you on WhatsApp when a matching job appears.\n\n"
        "*Your profile commands:*\n"
        "1️⃣ Update Skills\n"
        "2️⃣ Update Location\n"
        "3️⃣ Update Salary\n"
        "4️⃣ Upload New CV\n"
        "5️⃣ Stop Alerts\n"
        "6️⃣ My Applications\n"
        "7️⃣ Rejected Jobs\n\n"
        "*Other commands:*\n"
        "🔄 *RESTART* — Re-register from the beginning\n"
        "🔕 *STOP* — Unsubscribe from alerts\n"
        "🗑️ *DELETE MY DATA* — Erase all your data\n\n"
        "_Reply with a number to update your profile._"
    )


ACTIVE_MENU = (
    "📋 *QuickJobs Menu*\n\n"
    "*Update your profile:*\n"
    "1️⃣ Update Skills\n"
    "2️⃣ Update Location\n"
    "3️⃣ Update Salary\n"
    "4️⃣ Upload New CV\n"
    "5️⃣ Stop Alerts\n"
    "6️⃣ My Applications\n"
    "7️⃣ Rejected Jobs\n\n"
    "*Other commands:*\n"
    "🔄 *RESTART* — Re-register from the beginning\n"
    "🔕 *STOP* — Unsubscribe from alerts\n"
    "🗑️ *DELETE MY DATA* — Erase all your data\n\n"
    "_What would you like to update?_"
)

ASK_NEW_SKILLS   = "Please enter your updated skills _(comma separated)_:"
ASK_NEW_LOCATION = "Please enter your new city or region 📍:"
ASK_NEW_SALARY   = "Please enter your new salary range _(e.g. 80000-150000)_ 💰:"
ASK_NEW_CV       = "Please send your new CV as a *PDF* or *Word (.docx)* file 📄:"


def confirm_update(field: str, value: str) -> str:
    return (
        f"You want to update *{field}* to:\n_{value}_\n\n"
        "Reply *YES* to confirm or *NO* to cancel."
    )


def update_saved(field: str) -> str:
    return f"✅ Your *{field}* has been updated successfully!"


UPDATE_CANCELLED = "❌ Update cancelled. Your profile is unchanged."

OPT_OUT_CONFIRM = (
    "🔕 You've been unsubscribed from job alerts.\n\n"
    "Send *START* anytime to re-subscribe."
)

OPT_IN_CONFIRM = (
    "🔔 You're back! You'll now receive job alert notifications again.\n\n"
    "_Send *STOP* anytime to unsubscribe._"
)

INVALID_EXPERIENCE = (
    "Please reply with a number between 1 and 4:\n\n"
    "1️⃣ Junior\n"
    "2️⃣ Mid\n"
    "3️⃣ Senior\n"
    "4️⃣ Lead"
)

INVALID_SALARY = (
    "Please enter your salary range in the format *min-max*\n"
    "_(e.g. 80000-150000)_"
)

CV_UPLOAD_FAILED = (
    "❌ We couldn't process your CV.\n\n"
    "Please try again with a readable *PDF* or *Word (.docx)* file.\n"
    "Make sure the file contains selectable text (not a scanned image)."
)

ASK_DELETE_CONFIRM = (
    "⚠️ *Delete My Data*\n\n"
    "This will permanently erase all your information from QuickJobs:\n"
    "• Your profile and skills\n"
    "• All uploaded CVs\n"
    "• Your job alert history\n\n"
    "Reply *CONFIRM DELETE* to proceed, or anything else to cancel."
)

DATA_DELETED_CONFIRM = (
    "✅ *Your data has been permanently deleted.*\n\n"
    "All your personal information and uploaded CVs have been removed from QuickJobs.\n\n"
    "You will no longer receive job alerts.\n\n"
    "_If you'd like to register again in the future, just send *hi* to get started._"
)

DATA_DELETE_CANCELLED = "✅ Deletion cancelled. Your data is safe."

# ── Job-offer APPLY / SKIP ─────────────────────────────────────────

def offer_resolved(decision: str, result: dict) -> str:
    title   = result.get("job_title", "the job")
    company = result.get("company_name", "")
    if decision == "APPLY":
        return f"✅ You've applied for *{title}* at *{company}*! The employer can now see your profile."
    return (
        f"👍 No problem — you've skipped *{title}* at *{company}*.\n\n"
        "You can find it again anytime under *Rejected Jobs* and reapply."
    )


def next_offer_waiting(job_title: str, company_name: str) -> str:
    return (
        f"📬 You also have another match waiting: *{job_title}* at *{company_name}*.\n\n"
        "Reply *APPLY* or *SKIP* to respond."
    )


# ── My Applications / Rejected Jobs ────────────────────────────────

def _format_job_line(index: int, job: dict) -> str:
    parts = [f"*{job['title']}*", f"🏢 {job['company_name']}"]
    if job.get("location"):
        parts.append(f"📍 {job['location']}")
    if job.get("salary"):
        parts.append(f"💰 {job['salary']}")
    return f"{index}. " + " — ".join(parts)


def applications_list(apps: list) -> str:
    if not apps:
        return "📋 *My Applications*\n\nYou haven't applied to any jobs yet."
    lines = ["📋 *My Applications*\n"] + [_format_job_line(i, j) for i, j in enumerate(apps, 1)]
    return "\n".join(lines)


def rejected_jobs_list(rejected: list) -> str:
    lines = ["🗂️ *Rejected Jobs*\n"] + [_format_job_line(i, j) for i, j in enumerate(rejected, 1)]
    lines.append("\n_Reply with a number to reapply for that job._")
    return "\n".join(lines)


NO_REJECTED_JOBS = "🗂️ *Rejected Jobs*\n\nYou haven't skipped any job matches."

INVALID_LIST_CHOICE = "Please reply with a valid number from the list above."


def reapplied_confirm(job_title: str, company_name: str) -> str:
    return f"✅ You've reapplied for *{job_title}* at *{company_name}*! The employer can now see your profile."


REAPPLY_FAILED = "❌ Something went wrong while reapplying. Please try again shortly."
