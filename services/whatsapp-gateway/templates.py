WELCOME = (
    "👋 Welcome to *QuickJobs*!\n"
    "I'll help you find your next job opportunity.\n\n"
    "What is your full name?"
)

def ask_skills(name: str) -> str:
    return (
        f"Nice to meet you, *{name}*! 🎉\n\n"
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
        f"🎉 You're all set, *{name}*!\n\n"
        "We'll notify you on WhatsApp when a matching job appears.\n\n"
        "To manage your profile, reply with:\n"
        "1️⃣ Update Skills\n"
        "2️⃣ Update Location\n"
        "3️⃣ Update Salary\n"
        "4️⃣ Upload New CV\n"
        "5️⃣ Stop Alerts\n\n"
        "_Send *STOP* anytime to unsubscribe._"
    )

ACTIVE_MENU = (
    "📋 *QuickJobs Menu*\n\n"
    "1️⃣ Update Skills\n"
    "2️⃣ Update Location\n"
    "3️⃣ Update Salary\n"
    "4️⃣ Upload New CV\n"
    "5️⃣ Stop Alerts\n\n"
    "_What would you like to update?_"
)

ASK_NEW_SKILLS    = "Please enter your updated skills _(comma separated)_:"
ASK_NEW_LOCATION  = "Please enter your new city or region 📍:"
ASK_NEW_SALARY    = "Please enter your new salary range _(e.g. 80000-150000)_ 💰:"
ASK_NEW_CV        = "Please send your new CV as a *PDF* or *Word (.docx)* file 📄:"

def confirm_update(field: str, value: str) -> str:
    return (
        f"You want to update *{field}* to:\n_{value}_\n\n"
        "Reply *YES* to confirm or *NO* to cancel."
    )

def update_saved(field: str) -> str:
    return f"✅ Your *{field}* has been updated successfully!"

UPDATE_CANCELLED  = "❌ Update cancelled. Your profile is unchanged."

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

CV_RECEIVED = "✅ CV received! We're processing it now..."

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
    "_If you'd like to register again in the future, just send *HI* to get started._"
)

DATA_DELETE_CANCELLED = (
    "✅ Deletion cancelled. Your data is safe."
)
