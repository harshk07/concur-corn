from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from app.schema.deploySaveConsent2 import check_cp
from app.schema.build_consent_txn import build_consent_transaction
from app.schema.push_to_blockchain import push_signed_transactions_to_blockchain
from app.routes.cp_management_route import cpManagementRoute
from app.routes.interact_save_consent import contractInteractRoute
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title="Concur Blockchain",
    docs_url="/api"
)

scheduler = BackgroundScheduler()
scheduler.add_job(check_cp, "interval", seconds=20)
scheduler.add_job(build_consent_transaction, "interval", seconds=20)
scheduler.add_job(push_signed_transactions_to_blockchain, "interval", seconds=20)  
scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

app.include_router(cpManagementRoute)
app.include_router(contractInteractRoute)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"]
)

# Adding comment for git push

