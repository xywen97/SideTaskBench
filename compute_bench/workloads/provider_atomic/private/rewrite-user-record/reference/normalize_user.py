def normalize_user(row):
    return {"id": row["user_id"], "display_name": row["full_name"].strip(), "active": bool(row["active"])}
