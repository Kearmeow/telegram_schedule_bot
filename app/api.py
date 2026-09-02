from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import db
from .config import ADMIN_IDS

app = FastAPI(title="Telegram Schedule Mini App")


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GroupSelect(BaseModel):
    telegram_id: int
    group_id: int


class LessonCreate(BaseModel):
    group_id: int
    weekday: int = Field(ge=1, le=7)
    start_time: str
    end_time: str
    subject: str = Field(min_length=1, max_length=200)
    teacher: str = ""
    room: str = ""
    notes: str = ""


class LessonUpdate(BaseModel):
    weekday: int = Field(ge=1, le=7)
    start_time: str
    end_time: str
    subject: str = Field(min_length=1, max_length=200)
    teacher: str = ""
    room: str = ""
    notes: str = ""


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS


def require_admin(telegram_id: int):
    if not is_admin(telegram_id):
        raise HTTPException(status_code=403, detail="Admin access required")


@app.get("/")
async def index():
    return FileResponse("web/index.html")


@app.get("/app.js")
async def javascript():
    return FileResponse("web/app.js", media_type="application/javascript")


@app.get("/style.css")
async def css():
    return FileResponse("web/style.css", media_type="text/css")


@app.get("/api/groups")
async def groups():
    return db.list_groups()


@app.get("/api/groups/{group_id}/schedule")
async def schedule(group_id: int, weekday: int | None = None):
    if not db.get_group(group_id):
        raise HTTPException(404, "Group not found")
    if weekday is not None and not 1 <= weekday <= 7:
        raise HTTPException(400, "Invalid weekday")
    return db.get_lessons(group_id, weekday)


@app.post("/api/users/group")
async def select_group(data: GroupSelect):
    if not db.get_group(data.group_id):
        raise HTTPException(404, "Group not found")
    db.set_user_group(data.telegram_id, data.group_id)
    return {"ok": True}


@app.get("/api/users/{telegram_id}/group")
async def user_group(telegram_id: int):
    group_id = db.get_user_group(telegram_id)
    return {"group_id": group_id}


@app.get("/api/admin/check/{telegram_id}")
async def admin_check(telegram_id: int):
    return {"admin": is_admin(telegram_id)}


@app.post("/api/admin/groups")
async def add_group(data: GroupCreate, telegram_id: int):
    require_admin(telegram_id)
    try:
        group_id = db.create_group(data.name)
    except Exception as e:
        raise HTTPException(400, "Не удалось создать группу: возможно, она уже существует")
    return {"id": group_id, "name": data.name.strip()}


@app.delete("/api/admin/groups/{group_id}")
async def remove_group(group_id: int, telegram_id: int):
    require_admin(telegram_id)
    db.delete_group(group_id)
    return {"ok": True}


@app.post("/api/admin/lessons")
async def add_lesson(data: LessonCreate, telegram_id: int):
    require_admin(telegram_id)
    if not db.get_group(data.group_id):
        raise HTTPException(404, "Group not found")
    lesson_id = db.create_lesson(
        data.group_id, data.weekday, data.start_time, data.end_time,
        data.subject, data.teacher, data.room, data.notes
    )
    return {"id": lesson_id}


@app.put("/api/admin/lessons/{lesson_id}")
async def edit_lesson(lesson_id: int, data: LessonUpdate, telegram_id: int):
    require_admin(telegram_id)
    db.update_lesson(
        lesson_id, data.weekday, data.start_time, data.end_time,
        data.subject, data.teacher, data.room, data.notes
    )
    return {"ok": True}


@app.delete("/api/admin/lessons/{lesson_id}")
async def remove_lesson(lesson_id: int, telegram_id: int):
    require_admin(telegram_id)
    db.delete_lesson(lesson_id)
    return {"ok": True}
