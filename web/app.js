const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const telegramId = tg?.initDataUnsafe?.user?.id || 0;
const dayNames = ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];
const shortDays = ["", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

let groups = [];
let selectedGroup = null;
let selectedDay = getInitialDay();
let isAdmin = false;
let editingLesson = null;

const $ = (id) => document.getElementById(id);

function getInitialDay() {
  const d = new Date().getDay();
  return d === 0 ? 7 : d;
}

async function api(url, options = {}) {
  const headers = options.body instanceof FormData ? {} : {"Content-Type": "application/json"};
  const response = await fetch(url, {...options, headers: {...headers, ...(options.headers || {})}});
  if (!response.ok) {
    let detail = "Ошибка запроса";
    try { detail = (await response.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response;
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}

function renderDays() {
  const container = $("days");
  container.innerHTML = "";
  for (let i = 1; i <= 7; i++) {
    const button = document.createElement("button");
    button.className = "day" + (i === selectedDay ? " active" : "");
    button.textContent = shortDays[i];
    button.onclick = async () => {
      selectedDay = i;
      renderDays();
      await loadSchedule();
    };
    container.appendChild(button);
  }
}

function fillGroupSelect(selectId, value = null) {
  const select = $(selectId);
  if (!select) return;
  select.innerHTML = "";
  for (const group of groups) select.add(new Option(group.name, group.id));
  if (value && groups.some(g => g.id === Number(value))) select.value = value;
}

async function loadGroups() {
  groups = await api("/api/groups");
  const select = $("groupSelect");
  select.innerHTML = "";

  if (!groups.length) {
    select.innerHTML = '<option value="">Группы пока не добавлены</option>';
    $("schedule").innerHTML = '<div class="card empty">Администратор ещё не добавил группы.</div>';
    $("groupList").innerHTML = '<div class="empty">Групп пока нет.</div>';
    $("adminGroup").innerHTML = "";
    $("lessonFilterGroup").innerHTML = "";
    selectedGroup = null;
    return;
  }

  for (const group of groups) select.add(new Option(group.name, group.id));
  let saved = null;
  if (telegramId) {
    try { saved = (await api(`/api/users/${telegramId}/group`)).group_id; } catch {}
  }
  selectedGroup = groups.some(g => g.id === saved) ? saved : groups[0].id;
  select.value = selectedGroup;
  fillGroupSelect("adminGroup", selectedGroup);
  fillGroupSelect("lessonFilterGroup", selectedGroup);
  renderGroupList();
  await loadSchedule();
  await loadAdminLessons();
}

function renderGroupList() {
  const box = $("groupList");
  box.innerHTML = "";
  for (const group of groups) {
    const row = document.createElement("div");
    row.className = "group-row";
    row.innerHTML = `<div><strong>${escapeHtml(group.name)}</strong><span class="hint">ID: ${group.id}</span></div><button class="danger small" data-delete-group="${group.id}">Удалить</button>`;
    row.querySelector("button").onclick = async () => {
      if (!confirm(`Удалить группу «${group.name}» и всё её расписание?`)) return;
      try {
        await api(`/api/admin/groups/${group.id}?telegram_id=${telegramId}`, {method: "DELETE"});
        await loadGroups();
        toast("Группа удалена");
      } catch (e) { toast(e.message); }
    };
    box.appendChild(row);
  }
}

async function loadSchedule() {
  renderDays();
  if (!selectedGroup) return;
  const lessons = await api(`/api/groups/${selectedGroup}/schedule?weekday=${selectedDay}`);
  const schedule = $("schedule");
  if (!lessons.length) {
    schedule.innerHTML = `<div class="card empty">В ${dayNames[selectedDay].toLowerCase()} занятий нет 🎉</div>`;
    return;
  }
  schedule.innerHTML = "";
  for (const lesson of lessons) {
    const card = document.createElement("div");
    card.className = "lesson";
    const meta = [];
    if (lesson.teacher) meta.push("👨‍🏫 " + escapeHtml(lesson.teacher));
    if (lesson.room) meta.push("🚪 " + escapeHtml(lesson.room));
    if (lesson.notes) meta.push("📝 " + escapeHtml(lesson.notes));
    card.innerHTML = `<div class="time">${escapeHtml(lesson.start_time)}<br><span>${escapeHtml(lesson.end_time)}</span></div><div><div class="subject">${escapeHtml(lesson.subject)}</div><div class="meta">${meta.join("<br>")}</div></div>`;
    schedule.appendChild(card);
  }
}

function clearLessonForm() {
  editingLesson = null;
  $("editingLessonId").value = "";
  $("subject").value = "";
  $("teacher").value = "";
  $("room").value = "";
  $("notes").value = "";
  $("startTime").value = "09:00";
  $("endTime").value = "10:30";
  $("saveLesson").textContent = "Сохранить занятие";
  $("cancelEdit").classList.add("hidden");
}

function startEditLesson(lesson) {
  editingLesson = lesson;
  $("editingLessonId").value = lesson.id;
  $("adminGroup").value = lesson.group_id;
  $("lessonDay").value = lesson.weekday;
  $("startTime").value = lesson.start_time;
  $("endTime").value = lesson.end_time;
  $("subject").value = lesson.subject;
  $("teacher").value = lesson.teacher || "";
  $("room").value = lesson.room || "";
  $("notes").value = lesson.notes || "";
  $("saveLesson").textContent = "Сохранить изменения";
  $("cancelEdit").classList.remove("hidden");
  $("lessonsTab").scrollIntoView({behavior: "smooth", block: "start"});
}

async function loadAdminLessons() {
  if (!isAdmin || !selectedGroup) return;
  const filterGroup = Number($("lessonFilterGroup").value || selectedGroup);
  const lessons = await api(`/api/groups/${filterGroup}/schedule`);
  const box = $("adminLessons");
  if (!lessons.length) { box.innerHTML = '<div class="empty">Занятий нет.</div>'; return; }
  box.innerHTML = "";
  for (const lesson of lessons) {
    const div = document.createElement("div");
    div.className = "admin-lesson";
    div.innerHTML = `<div class="lesson-main"><div class="lesson-time">${escapeHtml(dayNames[lesson.weekday])} · ${escapeHtml(lesson.start_time)}–${escapeHtml(lesson.end_time)}</div><strong>${escapeHtml(lesson.subject)}</strong><div class="meta">${lesson.teacher ? "👨‍🏫 " + escapeHtml(lesson.teacher) : ""}${lesson.room ? " · 🚪 " + escapeHtml(lesson.room) : ""}${lesson.notes ? " · 📝 " + escapeHtml(lesson.notes) : ""}</div></div><div class="lesson-actions"><button class="secondary small" data-edit>Изменить</button><button class="danger small" data-delete>Удалить</button></div>`;
    div.querySelector("[data-edit]").onclick = () => startEditLesson(lesson);
    div.querySelector("[data-delete]").onclick = async () => {
      if (!confirm("Удалить это занятие?")) return;
      try {
        await api(`/api/admin/lessons/${lesson.id}?telegram_id=${telegramId}`, {method: "DELETE"});
        await loadSchedule(); await loadAdminLessons(); toast("Занятие удалено");
      } catch (e) { toast(e.message); }
    };
    box.appendChild(div);
  }
}

$("groupSelect").addEventListener("change", async (e) => {
  selectedGroup = Number(e.target.value);
  $("adminGroup").value = selectedGroup;
  $("lessonFilterGroup").value = selectedGroup;
  if (telegramId) {
    try { await api("/api/users/group", {method: "POST", body: JSON.stringify({telegram_id: telegramId, group_id: selectedGroup})}); } catch (e) { toast(e.message); }
  }
  await loadSchedule();
  await loadAdminLessons();
});

$("adminGroup").addEventListener("change", async (e) => {
  selectedGroup = Number(e.target.value);
  $("groupSelect").value = selectedGroup;
  $("lessonFilterGroup").value = selectedGroup;
  await loadSchedule(); await loadAdminLessons();
});

$("lessonFilterGroup").addEventListener("change", async (e) => {
  selectedGroup = Number(e.target.value);
  $("groupSelect").value = selectedGroup;
  $("adminGroup").value = selectedGroup;
  await loadSchedule(); await loadAdminLessons();
});

$("adminButton").onclick = () => {
  $("adminPanel").classList.remove("hidden");
  window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"});
};
$("closeAdmin").onclick = () => $("adminPanel").classList.add("hidden");
$("cancelEdit").onclick = clearLessonForm;

$("addGroup").onclick = async () => {
  const name = $("newGroupName").value.trim();
  if (!name) return toast("Введите название группы");
  try {
    await api(`/api/admin/groups?telegram_id=${telegramId}`, {method: "POST", body: JSON.stringify({name})});
    $("newGroupName").value = "";
    await loadGroups();
    toast("Группа добавлена");
  } catch (e) { toast(e.message); }
};

$("saveLesson").onclick = async () => {
  const data = {
    group_id: Number($("adminGroup").value), weekday: Number($("lessonDay").value),
    start_time: $("startTime").value, end_time: $("endTime").value,
    subject: $("subject").value.trim(), teacher: $("teacher").value.trim(),
    room: $("room").value.trim(), notes: $("notes").value.trim()
  };
  if (!data.subject) return toast("Введите предмет");
  if (!data.start_time || !data.end_time) return toast("Укажите время");
  try {
    if (editingLesson) {
      await api(`/api/admin/lessons/${editingLesson.id}?telegram_id=${telegramId}`, {method: "PUT", body: JSON.stringify(data)});
      toast("Изменения сохранены");
    } else {
      await api(`/api/admin/lessons?telegram_id=${telegramId}`, {method: "POST", body: JSON.stringify(data)});
      toast("Занятие добавлено");
    }
    clearLessonForm(); await loadGroups();
  } catch (e) { toast(e.message); }
};

for (const tab of document.querySelectorAll(".tab")) {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(x => x.classList.add("hidden"));
    tab.classList.add("active");
    $(tab.dataset.tab).classList.remove("hidden");
  };
}

$("dropZone").onclick = () => $("excelFile").click();
$("excelFile").onchange = () => {
  const file = $("excelFile").files[0];
  $("fileName").textContent = file ? file.name : "Выбери файл .xlsx";
  $("importExcel").disabled = !file;
};


$("saveTextSchedule").onclick = async () => {
  const group = $("textGroup").value.trim();
  const text = $("scheduleText").value.trim();
  const mode = document.querySelector('input[name="textImportMode"]:checked').value;

  if (!group) return toast("Введите название группы");
  if (!text) return toast("Вставьте расписание");

  const button = $("saveTextSchedule");
  button.disabled = true;
  button.textContent = "Сохраняем…";

  try {
    const result = await api(`/api/admin/import/text?telegram_id=${telegramId}`, {
      method: "POST",
      body: JSON.stringify({group, text, mode})
    });

    toast(`Готово: ${result.lessons} занятий, группа «${group}»`);
    await loadGroups();

    const target = groups.find(g => g.name === group);
    if (target) {
      selectedGroup = target.id;
      $("groupSelect").value = target.id;
      $("adminGroup").value = target.id;
      $("lessonFilterGroup").value = target.id;
      await loadSchedule();
      await loadAdminLessons();
    }
  } catch (e) {
    toast(e.message);
  } finally {
    button.disabled = false;
    button.textContent = "💾 Сохранить расписание";
  }
};

$("downloadTemplate").onclick = async () => {
  try {
    const response = await fetch(`/api/admin/import/template?telegram_id=${telegramId}`);
    if (!response.ok) throw new Error("Не удалось скачать шаблон");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "schedule_template.xlsx"; a.click();
    URL.revokeObjectURL(url);
  } catch (e) { toast(e.message); }
};

$("importExcel").onclick = async () => {
  const file = $("excelFile").files[0];
  if (!file) return toast("Выберите Excel-файл");
  const mode = document.querySelector('input[name="importMode"]:checked').value;
  const form = new FormData(); form.append("file", file);
  $("importExcel").disabled = true; $("importExcel").textContent = "Импортируем…";
  try {
    const result = await api(`/api/admin/import?telegram_id=${telegramId}&mode=${mode}`, {method: "POST", body: form});
    toast(`Готово: ${result.lessons} занятий, ${result.groups} групп`);
    $("excelFile").value = ""; $("fileName").textContent = "Выбери файл .xlsx";
    await loadGroups();
  } catch (e) { toast(e.message); }
  finally { $("importExcel").disabled = false; $("importExcel").textContent = "⬆️ Импортировать"; }
};

function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

async function init() {
  renderDays();
  if (telegramId) {
    try { isAdmin = (await api(`/api/admin/check/${telegramId}`)).admin; } catch {}
    if (isAdmin) $("adminButton").classList.remove("hidden");
  }
  await loadGroups();
}

init().catch(e => { console.error(e); toast(e.message); });
