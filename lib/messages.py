"""
lib/messages.py — All Burmese Unicode strings for the DonatingBot.

Static strings are defined here.
Dynamic strings (welcome, thank_you, etc.) are loaded from the
Google Sheets "Settings" tab at runtime via sheets.get_settings().
"""

# ─── Static UI Labels ─────────────────────────────────────────────────────────

NOT_MEMBER = (
    "⛔ ဤ bot ကို အသုံးပြုခွင့် မရှိပါ။\n\n"
    "သတ်မှတ်ထားသော channel ၏ member များသာ\n"
    "ဤ bot ကို အသုံးပြုနိုင်သည်။"
)


ASK_STUDENT_ID = (
    "🎓 ကျောင်းသား ID ကို ရိုက်ထည့်ပါ\n\n"
    "📝 ဥပမာ - g9A-001 သို့မဟုတ် G9A001\n"
    "(စာလုံးကြီး၊ ကြားပြက်ခြားနှင့် dash များ ရိုက်ချရနိုင်သည်)"
)

INVALID_STUDENT_ID = (
    "❌ Student ID မမှန်ကန်ပါ။\n"
    "ဥပမာ - G9A001 ဟု ရိုက်ထည့်ပါ။"
)

CHOOSE_CLASS = "📚 တန်းကို ရွေးချယ်ပါ"

CHOOSE_METHOD = "💳 ငွေလွှဲနည်းလမ်းကို ရွေးချယ်ပါ"

WAVE_LABEL  = "💜 WavePay"
NUG_LABEL   = "🟡 NUGPay"

NO_ACCOUNT = (
    "⚠️ ဤတန်းအတွက် {} အကောင့် မပေးထားသေးပါ။\n"
    "ဆရာ/ဆရာမနှင့် ဆက်သွယ်ပါ။"
)

SHOW_ACCOUNT_WAVE = (
    "✅ WavePay အကောင့် -\n\n"
    "👤 အမည် - {account_name}\n"
    "📱 ဖုန်းနံပါတ် - {account_number}\n\n"
    "အထက်ပါ အကောင့်သို့ ငွေလွှဲပြီးနောက် ဆက်လုပ်ပါ။"
)

SHOW_ACCOUNT_NUG = (
    "✅ NUGPay အကောင့် -\n\n"
    "👤 အမည် - {account_name}\n"
    "🔑 NUG ID - {account_number}\n\n"
    "အထက်ပါ အကောင့်သို့ ငွေလွှဲပြီးနောက် ဆက်လုပ်ပါ။"
)

ASK_AMOUNT = (
    "💰 လှူဒါန်းမည့် ပမာဏကို ကျပ် (Ks) ဖြင့် ရိုက်ထည့်ပါ\n\n"
    "ဥပမာ - 5000"
)

INVALID_AMOUNT = (
    "❌ ပမာဏ မမှန်ကန်ပါ။\n"
    "ဂဏန်း သာ ရိုက်ထည့်ပါ။ ဥပမာ - 5000"
)

ASK_SCREENSHOT = (
    "📸 Transaction Screenshot ပေးပို့ပါ\n\n"
    "⚠️ Screenshot တစ်ပုံသာ ပေးပို့ပါ"
)

PROCESSING = "⏳ Screenshot စစ်ဆေးနေသည်... ခေတ္တစောင့်ပါ"

EXTRACTION_FAILED = (
    "❌ Screenshot မှ ဒေတာ ဖတ်မရပါ။\n"
    "ရှင်းလင်းသောပုံကို ပြန်ပေးပို့ပါ။"
)

NOT_SUCCESS = (
    "❌ Transaction မအောင်မြင်ပါ (Status: {status})\n"
    "အောင်မြင်သော Transaction ၏ Screenshot ကိုသာ ပေးပို့ပါ။"
)

# Amount note shown in confirmation (not a rejection — teacher verifies manually)
AMOUNT_NOTE = (
    "📌 မှတ်ချက် - ကျောင်းသား ၂ ဦးနှင့်အထက် SS တစ်ပုံ မျှဝေနိုင်သည်\n"
    "ဆရာ/ဆရာမ မှ စစ်ဆေးပါမည်"
)

DUPLICATE_TX = (
    "❌ ဤ Transaction ID သည် ယခင်က တင်ထားပြီး ဖြစ်သည်။\n"
    "ထပ်မံ တင်၍မရပါ။"
)

WRONG_ACCOUNT = (
    "❌ ငွေလွှဲ ရမည့် အကောင့် မမှန်ကန်ပါ\n\n"
    "ငွေလွှဲ ရမည့် အကောင့် - {expected}\n"
    "Screenshot တွင် - {found}\n\n"
    "မှန်ကန်သော အကောင့်သို့ ငွေလွှဲပြီး ပြန်ပေးပို့ပါ။"
)

RATE_LIMITED = (
    "⏱️ မကြာမီ တင်ထားပြီး ဖြစ်သည်။\n"
    "{seconds} စက္ကန့် ကြာပြီးနောက် ထပ်မံ တင်နိုင်သည်။"
)

CANCEL_MSG = "❌ ပယ်ဖျက်လိုက်သည်။ /start နှိပ်ပြီး ပြန်စတင်နိုင်သည်။"

# ─── Admin Strings ─────────────────────────────────────────────────────────────

ADMIN_MENU = (
    "👨‍💼 Admin မီနူး\n\n"
    "/stats — နေ့စဉ်/လစဉ် ဝင်ငွေ စစ်ဆေးမည်\n"
    "/accounts — ငွေလွှဲ အကောင့်များ ကြည့်မည်\n"
    "/broadcast — သတင်းစကားများ ပို့မည်\n"
)

NOT_ADMIN = "⛔ Admin သာ ဤ command ကို အသုံးပြုနိုင်သည်။"

BROADCAST_PROMPT = (
    "📢 Broadcast လုပ်မည့် သတင်းစကား ရိုက်ထည့်ပါ\n"
    "(/cancel နှိပ်ပြီး ပယ်ဖျက်နိုင်သည်)"
)

BROADCAST_SENT = "✅ သတင်းစကားကို {count} ဦးထံ ပေးပို့ပြီးပါပြီ။"

STATS_HEADER = "📊 လှူဒါန်းမှု စာရင်း"

NO_STATS = "📭 ဒေတာ မရှိသေးပါ။"

# ─── Default fallbacks (if Settings sheet is missing) ─────────────────────────

DEFAULT_WELCOME = (
    "🏫 ကျောင်းထောက်ပံ့ရေး Bot သို့ ကြိုဆိုပါသည်။\n\n"
    "ဤ Bot မှတဆင့် ကျောင်းသားများ၏ ပညာသင်ကြားရေးအတွက် \n"
    "လှူဒါန်းငွေများ ပေးပို့နိုင်ပါသည်။\n\n"
    "ဆက်လုပ်ရန် အောက်ပါ ခလုတ်ကို နှိပ်ပါ 👇"
)

DEFAULT_THANK_YOU = (
    "🎉 ကျေးဇူးတင်ပါသည်!\n\n"
    "သင်၏ လှူဒါန်းမှုသည် ကျောင်းသားများအတွက် \n"
    "အလွန် အဖိုးတန်ပါသည်။\n\n"
    "📋 လှူဒါန်းမှု အချက်အလက်\n"
    "─────────────────────\n"
    "🎓 Student ID  : {student_id}\n"
    "📚 တန်း       : {class_name}\n"
    "💳 နည်းလမ်း   : {method}\n"
    "💰 ပမာဏ       : {amount} Ks\n"
    "🏦 အကောင့်    : {account_name}\n"
    "🔢 TX ID      : {transaction_id}\n"
    "📅 ရက်စွဲ     : {date_time}\n"
    "─────────────────────\n"
    "✅ မှတ်တမ်းတင်ပြီးပါပြီ"
)

START_BUTTON = "🚀 ဆက်လုပ်ရန်"
CANCEL_BUTTON = "❌ ပယ်ဖျက်မည်"
