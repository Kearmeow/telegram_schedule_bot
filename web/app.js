const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const telegramId = tg?.initDataUnsafe?.user?.id || 0;

const dayNames = [
  "", "Понедельник", "Вторник", "Среда", "Четверг",
  "Пятница", "Суббота", "Воскресенье"
];

const shortDays = ["", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

let groups = [];
let selectedGroup = null;
let selectedDay = getInitialDay();
let isAdmin = false;

const $ = (id) => document.getElementById(id);

function getInitialDay() {
  const jsDay = new Date().getDay();
  return jsDay === 0 ? 7 : jsDay;
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {"Content-Type": "application/json"},
    ...options
  });

  if (!response.ok) {
    let detail = "Ошибка запроса";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return response.json();
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2200);
}

async function loadGroups() {
  groups = await api("/api/groups");

  const select = $("groupSelect");
  const adminSelect = $("adminGroup");

  select.innerHTML = "";
  adminSelect.innerHTML = "";

  if (!groups.length) {
    select.innerHTML = '<option value="">Группы пока не добавлены</option>';
    $("schedule").innerHTML =
      '<div class="card empty">Администратор ещё не добавил группы.</div>';
    return;
  }

  for (const group of groups) {
    const option = new Option(group.name, group.id);
    select.add(option);

    const adminOption = new Option(group.name, group.id);
    adminSelect.add(adminOption);
  }

  let saved = null;
  if (telegramId) {
    try {
      saved = (await api(`/api/users/${telegramId}/group`)).group_id;
    } catch {}
  }

  const exists = groups.some(g => g.id === saved);
  selectedGroup = exists ? saved : groups[0].id;
  select.value = selectedGroup;
  adminSelect.value = selectedGroup;

  await loadSchedule();
  await loadAdminLessons();
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

async function loadSchedule() {
  renderDays();

  if (!selectedGroup) return;

  const lessons = await api(
    `/api/groups/${selectedGroup}/schedule?weekday=${selectedDay}`
  );

  const schedule = $("schedule");

  if (!lessons.length) {
    schedule.innerHTML =
      `<div class="card empty">В ${dayNames[selectedDay].toLowerCase()} занятий нет 🎉</div>`;
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

    card.innerHTML = `
      <div class="time">
        ${escapeHtml(lesson.start_time)}<br>
        <span style="color:var(--hint);font-weight:400">${escapeHtml(lesson.end_time)}</span>
      </div>
      <div>
        <div class="subject">${escapeHtml(lesson.subject)}</div>
        <div class="meta">${meta.join("<br>")}</div>
      </div>
    `;

    schedule.appendChild(card);
  }
}

$("groupSelect").addEventListener("change", async (event) => {
  selectedGroup = Number(event.target.value);
  $("adminGroup").value = selectedGroup;

  if (telegramId) {
    try {
      await api("/api/users/group", {
        method: "POST",
        body: JSON.stringify({
          telegram_id: telegramId,
          group_id: selectedGroup
        })
      });
    } catch (e) {
      toast(e.message);
    }
  }

  await loadSchedule();
  await loadAdminLessons();
});

$("adminGroup").addEventListener("change", async (event) => {
  selectedGroup = Number(event.target.value);
  $("groupSelect").value = selectedGroup;
  await loadSchedule();
  await loadAdminLessons();
});

$("adminButton").onclick = () => {
  $("adminPanel").classList.remove("hidden");
  window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"});
};

$("closeAdmin").onclick = () => {
  $("adminPanel").classList.add("hidden");
};

$("addGroup").onclick = async () => {
  const name = $("newGroupName").value.trim();
  if (!name) return toast("Введите название группы");

  try {
    await api(`/api/admin/groups?telegram_id=${telegramId}`, {
      method: "POST",
      body: JSON.stringify({name})
    });

    $("newGroupName").value = "";
    await loadGroups();
    toast("Группа добавлена");
  } catch (e) {
    toast(e.message);
  }
};

$("addLesson").onclick = async () => {
  const data = {
    group_id: Number($("adminGroup").value),
    weekday: Number($("lessonDay").value),
    start_time: $("startTime").value,
    end_time: $("endTime").value,
    subject: $("subject").value.trim(),
    teacher: $("teacher").value.trim(),
    room: $("room").value.trim(),
    notes: $("notes").value.trim()
  };

  if (!data.subject) return toast("Введите предмет");

  try {
    await api(`/api/admin/lessons?telegram_id=${telegramId}`, {
      method: "POST",
      body: JSON.stringify(data)
    });

    $("subject").value = "";
    $("teacher").value = "";
    $("room").value = "";
    $("notes").value = "";

    await loadSchedule();
    await loadAdminLessons();
    toast("Занятие добавлено");
  } catch (e) {
    toast(e.message);
  }
};

async function loadAdminLessons() {
  if (!isAdmin || !selectedGroup) return;

  const lessons = await api(`/api/groups/${selectedGroup}/schedule`);
  const box = $("adminLessons");

  if (!lessons.length) {
    box.innerHTML = '<div class="empty">Занятий нет.</div>';
    return;
  }

  box.innerHTML = "";

  for (const lesson of lessons) {
    const div = document.createElement("div");
    div.className = "admin-lesson";
    div.innerHTML = `
      <strong>${escapeHtml(dayNames[lesson.weekday])}</strong> ·
      ${escapeHtml(lesson.start_time)}–${escapeHtml(lesson.end_time)}
      <br>
      ${escapeHtml(lesson.subject)}
      ${lesson.room ? " · 🚪 " + escapeHtml(lesson.room) : ""}
      <div class="lesson-actions">
        <button class="secondary" data-edit="${lesson.id}">Изменить</button>
        <button class="danger" data-delete="${lesson.id}">Удалить</button>
      </div>
    `;

    div.querySelector("[data-delete]").onclick = async () => {
      if (!confirm("Удалить это занятие?")) return;
      try {
        await api(
          `/api/admin/lessons/${lesson.id}?telegram_id=${telegramId}`,
          {method: "DELETE"}
        );
        await loadSchedule();
        await loadAdminLessons();
        toast("Удалено");
      } catch (e) {
        toast(e.message);
      }
    };

    div.querySelector("[data-edit]").onclick = () => editLesson(lesson);

    box.appendChild(div);
  }
}

async function editLesson(lesson) {
  const subject = prompt("Предмет:", lesson.subject);
  if (subject === null) return;

  const teacher = prompt("Преподаватель:", lesson.teacher || "");
  if (teacher === null) return;

  const room = prompt("Аудитория:", lesson.room || "");
  if (room === null) return;

  try {
    await api(
      `/api/admin/lessons/${lesson.id}?telegram_id=${telegramId}`,
      {
        method: "PUT",
        body: JSON.stringify({
          weekday: lesson.weekday,
          start_time: lesson.start_time,
          end_time: lesson.end_time,
          subject: subject.trim(),
          teacher: teacher.trim(),
          room: room.trim(),
          notes: lesson.notes || ""
        })
      }
    );

    await loadSchedule();
    await loadAdminLessons();
    toast("Изменения сохранены");
  } catch (e) {
    toast(e.message);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function init() {
  renderDays();

  if (telegramId) {
    try {
      isAdmin = (await api(`/api/admin/check/${telegramId}`)).admin;
    } catch {}

    if (isAdmin) {
      $("adminButton").classList.remove("hidden");
    }
  }

  await loadGroups();
}

init().catch(error => {
  console.error(error);
  toast(error.message);
});
