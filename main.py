from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

app = FastAPI(title="আমার দেশ, আমার তথ্য")

DIVISIONS = {
    "বরিশাল": ["বরগুনা", "বরিশাল", "ভোলা", "ঝালকাঠি", "পটুয়াখালী", "পিরোজপুর"],
    "চট্টগ্রাম": ["বান্দরবান", "ব্রাহ্মণবাড়িয়া", "চাঁদপুর", "চট্টগ্রাম", "কক্সবাজার", "কুমিল্লা", "ফেনী", "খাগড়াছড়ি", "লক্ষ্মীপুর", "নোয়াখালী", "রাঙ্গামাটি"],
    "ঢাকা": ["ঢাকা", "ফরিদপুর", "গাজীপুর", "গোপালগঞ্জ", "কিশোরগঞ্জ", "মাদারীপুর", "মানিকগঞ্জ", "মুন্সিগঞ্জ", "নারায়ণগঞ্জ", "নরসিংদী", "রাজবাড়ী", "শরীয়তপুর", "টাঙ্গাইল"],
    "খুলনা": ["বাগেরহাট", "চুয়াডাঙ্গা", "যশোর", "ঝিনাইদহ", "খুলনা", "কুষ্টিয়া", "মাগুরা", "মেহেরপুর", "নড়াইল", "সাতক্ষীরা"],
    "ময়মনসিংহ": ["জামালপুর", "ময়মনসিংহ", "নেত্রকোনা", "শেরপুর"],
    "রাজশাহী": ["বগুড়া", "জয়পুরহাট", "নওগাঁ", "নাটোর", "চাঁপাইনবাবগঞ্জ", "পাবনা", "রাজশাহী", "সিরাজগঞ্জ"],
    "রংপুর": ["দিনাজপুর", "গাইবান্ধা", "কুড়িগ্রাম", "লালমনিরহাট", "নীলফামারী", "পঞ্চগড়", "রংপুর", "ঠাকুরগাঁও"],
    "সিলেট": ["হবিগঞ্জ", "মৌলভীবাজার", "সুনামগঞ্জ", "সিলেট"]
}

class DataRecord(BaseModel):
    module: str
    item: str
    region_type: str = "জেলা"
    region_name: Optional[str] = None
    market_name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    price_type: Optional[str] = None
    status: str = "পাওয়া যাচ্ছে না"
    published_at: Optional[str] = None
    collected_at: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    note: Optional[str] = None

DB = []  # Verified Records
APPROVAL_QUEUE = []  # যাচাই প্রয়োজন
ADMIN_LOGS = []

@app.get("/", response_class=HTMLResponse)
def home():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return HTMLResponse("<h1>আমার দেশ, আমার তথ্য</h1>")

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.get("/districts")
def get_districts():
    total = sum(len(v) for v in DIVISIONS.values())
    return {"total_divisions": 8, "total_districts": total, "data": DIVISIONS}

@app.get("/records")
def get_records():
    return DB

@app.post("/records")
def add_record(record: DataRecord):
    # নিয়ম: উৎস ছাড়া Verified নয়
    if record.status in ["লাইভ", "সর্বশেষ প্রাপ্ত"] and not record.source_name:
        record.status = "যাচাই প্রয়োজন"
        APPROVAL_QUEUE.append({"id": len(APPROVAL_QUEUE)+1, "record": record.dict(), "reason": "উৎস নেই", "created_at": datetime.now().isoformat()})
        return {"message": "উৎস নেই, Approval Queue-তে গেছে"}
    DB.append(record.dict())
    return {"message": "Verified হিসেবে যোগ হয়েছে"}

# --- Public Submission ---
@app.post("/public-submit")
def public_submit(record: DataRecord):
    item = {"id": len(APPROVAL_QUEUE)+1, "record": record.dict(), "reason": "Public Submission - যাচাই প্রয়োজন", "created_at": datetime.now().isoformat(), "status": "pending"}
    APPROVAL_QUEUE.append(item)
    return {"message": "Approval Queue-তে গেছে", "id": item["id"]}

# --- Admin Approval Queue ---
@app.get("/admin")
def admin_panel():
    html = "<h1>Admin Approval Queue</h1>"
    html += f"<p>Pending: {len([x for x in APPROVAL_QUEUE if x.get('status')!='approved'])} | Verified: {len(DB)}</p>"
    for q in APPROVAL_QUEUE:
        html += f"<div style='border:1px solid #ddd;padding:10px;margin:10px;'><b>ID {q['id']}</b> - {q['record']['item']} - {q['record'].get('value')} {q['record'].get('unit')} - {q['record'].get('region_name')} - {q['record'].get('market_name')} - Reason: {q['reason']} - Status: {q.get('status','pending')} <br><a href='/admin/approve/{q['id']}'>Approve</a> | <a href='/admin/reject/{q['id']}'>Reject</a></div>"
    html += "<br><a href='/'>Home</a>"
    return HTMLResponse(html)

@app.get("/admin/approve/{qid}")
def approve(qid: int):
    for q in APPROVAL_QUEUE:
        if q["id"] == qid and q.get("status") != "approved":
            q["status"] = "approved"
            q["record"]["status"] = "সর্বশেষ প্রাপ্ত"
            DB.append(q["record"])
            ADMIN_LOGS.append({"action": "approve", "id": qid, "time": datetime.now().isoformat()})
            return HTMLResponse(f"Approved ID {qid} <br><a href='/admin'>Back</a>")
    return HTMLResponse("পাওয়া যায়নি")

@app.get("/admin/reject/{qid}")
def reject(qid: int):
    for q in APPROVAL_QUEUE:
        if q["id"] == qid:
            q["status"] = "rejected"
            ADMIN_LOGS.append({"action": "reject", "id": qid, "time": datetime.now().isoformat()})
            return HTMLResponse(f"Rejected ID {qid} <br><a href='/admin'>Back</a>")
    return HTMLResponse("পাওয়া যায়নি")

@app.get("/admin/logs")
def logs():
    return ADMIN_LOGS
