const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:5000" : "";

const state = {
  currentUser: null,
  systemDate: new Date().toISOString().slice(0, 10),
  books: [],
  bookItems: [],
  users: [],
  borrows: [],
  accidents: [],
  messages: []
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const today = () => state.systemDate;
const toDateText = (value) => value ? String(value).slice(0, 10) : "-";
const daysBetween = (start, end) => Math.ceil((new Date(end) - new Date(start)) / 86400000);
const isAdmin = () => state.currentUser?.role === "管理员";

function authQuery() {
  if (!state.currentUser) return "";
  return new URLSearchParams({
    operator_user_id: state.currentUser.user_id,
    operator_role: state.currentUser.role
  }).toString();
}

function authBody(extra = {}) {
  return {
    ...extra,
    operator_user_id: state.currentUser?.user_id,
    operator_role: state.currentUser?.role
  };
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const payload = await response.json();
  if (!response.ok || payload.code !== 200) {
    throw new Error(payload.msg || "接口请求失败");
  }
  return payload.data;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 2400);
}

function userName(userId) {
  return state.users.find((user) => Number(user.user_id) === Number(userId))?.name || "-";
}

function bookById(bookId) {
  return state.books.find((book) => Number(book.book_id) === Number(bookId));
}

function itemById(itemId) {
  return state.bookItems.find((item) => String(item.book_item_id) === String(itemId));
}

function bookByItemId(itemId) {
  const item = itemById(itemId);
  return item ? bookById(item.book_id) : null;
}

function bookNameByItem(itemId) {
  return bookByItemId(itemId)?.book_name || itemById(itemId)?.book_name || "-";
}

function itemLabel(item) {
  const book = bookById(item.book_id);
  return `${book?.book_name || item.book_name || "-"}（${item.book_item_id}）`;
}

function statusClass(value) {
  if (["正常", "在馆", "已还"].includes(value)) return "ok";
  if (["未还", "借出", "到期"].includes(value)) return "warn";
  return "bad";
}

function copyStats(bookId) {
  const book = bookById(bookId);
  const items = state.bookItems.filter((item) => Number(item.book_id) === Number(bookId));
  return {
    total: Number(book?.total_stock ?? items.length),
    available: Number(book?.available_stock ?? items.filter((item) => item.status === "在馆").length)
  };
}

async function loadAll() {
  const query = authQuery();
  const userScope = isAdmin() ? "" : `?user_id=${state.currentUser.user_id}`;
  const [dateData, books, items, readers, borrows, accidents, messages] = await Promise.all([
    apiRequest("/api/system/current_date"),
    apiRequest("/api/book/list"),
    apiRequest("/api/book_item/list"),
    isAdmin() ? apiRequest("/api/reader/list") : Promise.resolve([]),
    apiRequest(`/api/borrow/list${userScope}`),
    apiRequest(`/api/accident/list${userScope}`),
    apiRequest(`/api/message/list?${query}`)
  ]);

  state.systemDate = dateData.current_date;
  state.books = books || [];
  state.bookItems = items || [];
  const normalizedReaders = (readers || []).map((reader) => ({ ...reader, role: "读者" }));
  state.users = [
    ...(state.currentUser ? [state.currentUser] : []),
    ...normalizedReaders.filter((user) => Number(user.user_id) !== Number(state.currentUser?.user_id))
  ];
  state.borrows = borrows || [];
  state.accidents = accidents || [];
  state.messages = messages || [];
  $("#systemDate").value = state.systemDate;
  applyRoleView();
  setDefaultDates();
  renderAll();
}

function applyRoleView() {
  const adminViews = ["books", "items", "readers"];
  adminViews.forEach((viewId) => {
    const item = document.querySelector(`[data-view="${viewId}"]`);
    if (item) item.classList.toggle("hidden", !isAdmin());
  });
  $$(".admin-only").forEach((item) => item.classList.toggle("hidden", !isAdmin()));

  const activeHidden = document.querySelector(".nav-item.active.hidden");
  if (activeHidden) switchView("dashboard");
}

function switchView(viewId) {
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === viewId));
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === viewId));
  $("#pageTitle").textContent = document.querySelector(`[data-view="${viewId}"]`).textContent;
  renderAll();
}

function renderDashboard() {
  const borrowing = state.borrows.filter((item) => item.status === "未还");
  const overdue = borrowing.filter((item) => daysBetween(today(), item.return_deadline) < 0);
  $("#statBookTypes").textContent = state.books.length;
  $("#statAvailable").textContent = state.books.reduce((sum, book) => sum + Number(book.available_stock || 0), 0);
  $("#statBorrowing").textContent = borrowing.length;
  $("#statOverdue").textContent = overdue.length;
  $("#recentBorrowRows").innerHTML = state.borrows.slice(0, 6).map((item) => `
    <tr>
      <td>${item.user_name || userName(item.user_id)}</td>
      <td>${item.book_name || bookNameByItem(item.book_item_id)}</td>
      <td>${toDateText(item.borrow_date)}</td>
      <td>${toDateText(item.return_deadline)}</td>
      <td><span class="status ${statusClass(item.status)}">${item.status}</span></td>
    </tr>
  `).join("");
}

function renderBooks() {
  const search = $("#bookSearch").value.trim().toLowerCase();
  const category = $("#bookCategoryFilter").value;
  const categories = [...new Set(state.books.map((book) => book.category).filter(Boolean))];
  $("#bookCategoryFilter").innerHTML = `<option value="">全部分类</option>${categories.map((item) => `<option ${item === category ? "selected" : ""}>${item}</option>`).join("")}`;

  const rows = state.books.filter((book) => {
    const text = `${book.isbn} ${book.book_name} ${book.author}`.toLowerCase();
    return (!search || text.includes(search)) && (!category || book.category === category);
  });

  $("#bookRows").innerHTML = rows.map((book) => {
    const stats = copyStats(book.book_id);
    return `
      <tr>
        <td>${book.isbn}</td>
        <td>${book.book_name}</td>
        <td>${book.author || "-"}</td>
        <td>${book.category || "-"}</td>
        <td>${Number(book.price || 0).toFixed(2)}</td>
        <td>${stats.total}</td>
        <td><span class="tag ${stats.available > 0 ? "ok" : "bad"}">${stats.available}</span></td>
        <td><div class="row-actions">${isAdmin() ? `<button data-delete-book="${book.book_id}">删除</button>` : "-"}</div></td>
      </tr>
    `;
  }).join("");
}

function renderItems() {
  const search = $("#itemSearch").value.trim().toLowerCase();
  const status = $("#itemStatusFilter").value;
  const rows = state.bookItems.filter((item) => {
    const text = `${item.book_item_id} ${item.book_name || ""} ${item.shelf_code || ""}`.toLowerCase();
    return (!search || text.includes(search)) && (!status || item.status === status);
  });

  $("#itemRows").innerHTML = rows.map((item) => `
    <tr>
      <td>${item.book_item_id}</td>
      <td>${item.book_name || bookById(item.book_id)?.book_name || "-"}</td>
      <td>${item.shelf_code || "-"}</td>
      <td>${toDateText(item.create_time)}</td>
      <td><span class="status ${statusClass(item.status)}">${item.status}</span></td>
    </tr>
  `).join("");
}

function renderReaders() {
  const search = $("#readerSearch").value.trim().toLowerCase();
  const black = $("#readerStatusFilter").value;
  const rows = state.users.filter((user) => user.role === "读者").filter((user) => {
    const text = `${user.username} ${user.name} ${user.reader_type}`.toLowerCase();
    return (!search || text.includes(search)) && (!black || String(user.black) === black);
  });

  $("#readerRows").innerHTML = rows.map((user) => `
    <tr>
      <td>${user.username}</td>
      <td>${user.name}</td>
      <td>${user.gender || "-"}</td>
      <td>${user.reader_type || "-"}</td>
      <td>${user.max_borrow_num}</td>
      <td>${user.borrow_days} 天</td>
      <td><span class="status ${user.black ? "bad" : "ok"}">${user.black ? "黑名单" : "正常"}</span></td>
      <td><div class="row-actions">${isAdmin() ? `<button data-toggle-black="${user.user_id}">${user.black ? "恢复" : "拉黑"}</button>` : "-"}</div></td>
    </tr>
  `).join("");
}

function renderSelects() {
  const readers = isAdmin() ? state.users.filter((user) => user.role === "读者") : [state.currentUser].filter(Boolean);
  $("#borrowUser").innerHTML = readers.map((user) => `<option value="${user.user_id}">${user.name}（${user.username}）</option>`).join("");
  $("#borrowItem").innerHTML = state.bookItems.map((item) => `<option value="${item.book_item_id}" ${item.status !== "在馆" ? "disabled" : ""}>${itemLabel(item)} - ${item.status}</option>`).join("");
  $("#itemBook").innerHTML = state.books.map((book) => `<option value="${book.book_id}">${book.book_name}</option>`).join("");

  const unreturned = state.borrows.filter((item) => item.status === "未还");
  const options = unreturned.map((item) => `<option value="${item.borrow_id}">${item.user_name || userName(item.user_id)} - ${item.book_name || bookNameByItem(item.book_item_id)} - 应还 ${toDateText(item.return_deadline)}</option>`).join("");
  $("#returnBorrow").innerHTML = options || `<option value="">暂无未还记录</option>`;
  $("#accidentBorrow").innerHTML = options || `<option value="">暂无未还记录</option>`;
}

function renderRecords() {
  const search = $("#recordSearch").value.trim().toLowerCase();
  const status = $("#recordStatusFilter").value;
  const rows = state.borrows.filter((item) => {
    const text = `${item.user_name || userName(item.user_id)} ${item.book_name || bookNameByItem(item.book_item_id)} ${item.book_item_id}`.toLowerCase();
    return (!search || text.includes(search)) && (!status || item.status === status);
  });

  $("#recordRows").innerHTML = rows.map((item) => {
    const overdue = item.status === "未还" && daysBetween(today(), item.return_deadline) < 0;
    return `
      <tr>
        <td>${item.user_name || userName(item.user_id)}</td>
        <td>${item.book_name || bookNameByItem(item.book_item_id)}</td>
        <td>${toDateText(item.borrow_date)}</td>
        <td>${toDateText(item.return_deadline)}</td>
        <td>${item.renew_times}</td>
        <td><span class="status ${overdue ? "bad" : statusClass(item.status)}">${overdue ? "超期" : item.status}</span></td>
      </tr>
    `;
  }).join("");
}

function renderAccidents() {
  $("#accidentRows").innerHTML = state.accidents.map((item) => `
    <tr>
      <td>${item.user_name || userName(item.user_id)}</td>
      <td>${item.book_name || bookNameByItem(item.book_item_id)}</td>
      <td>${item.handle_type}</td>
      <td>${Number(item.amount || 0).toFixed(2)}</td>
      <td>${toDateText(item.handle_date)}</td>
      <td>${item.remark || "-"}</td>
    </tr>
  `).join("");
}

function renderMessages() {
  $("#messageList").innerHTML = state.messages.map((item) => `
    <article class="message-item ${item.is_read ? "" : "unread"}">
      <div>
        <strong>${item.title}<span class="tag ${statusClass(item.msg_type)}">${item.msg_type || "系统"}</span></strong>
        <span>${item.content}</span>
        <p class="muted">${userName(item.user_id)} · ${toDateText(item.create_time)}</p>
      </div>
      ${isAdmin()
        ? `<span class="read-state">${item.is_read ? "已读" : "未读"}</span>`
        : `<button class="ghost-btn" data-read-message="${item.msg_id}">${item.is_read ? "已读" : "标为已读"}</button>`}
    </article>
  `).join("");
}

function renderAll() {
  renderDashboard();
  renderBooks();
  renderItems();
  renderReaders();
  renderSelects();
  renderRecords();
  renderAccidents();
  renderMessages();
}

function openModal(id) {
  $(`#${id}`).classList.remove("hidden");
}

function closeModals() {
  $$(".modal").forEach((modal) => modal.classList.add("hidden"));
}

function setDefaultDates() {
  $("#systemDate").value = state.systemDate;
  $("#borrowDate").value = today();
  $("#returnDate").value = today();
  $("#accidentDate").value = today();
}

async function handleAction(work, okMessage) {
  try {
    await work();
    await loadAll();
    if (okMessage) showToast(okMessage);
  } catch (error) {
    showToast(error.message);
  }
}

function initEvents() {
  $("#loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const user = await apiRequest("/api/user/login", {
        method: "POST",
        body: JSON.stringify({
          username: $("#loginUsername").value.trim(),
          password: $("#loginPassword").value
        })
      });
      state.currentUser = user;
      $("#currentUser").textContent = user.name;
      $("#loginView").classList.add("hidden");
      $("#appView").classList.remove("hidden");
      await loadAll();
    } catch (error) {
      showToast(error.message);
    }
  });

  $("#registerForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await apiRequest("/api/user/register", {
        method: "POST",
        body: JSON.stringify({
          username: $("#registerUsername").value.trim(),
          password: $("#registerPassword").value,
          name: $("#registerName").value.trim(),
          gender: $("#registerGender").value,
          reader_type: $("#registerType").value.trim()
        })
      });
      event.target.reset();
      closeModals();
      showToast("注册成功，请登录");
    } catch (error) {
      showToast(error.message);
    }
  });

  $("#passwordForm").addEventListener("submit", (event) => {
    event.preventDefault();
    handleAction(async () => {
      await apiRequest("/api/user/change_pwd", {
        method: "PUT",
        body: JSON.stringify({
          user_id: state.currentUser.user_id,
          old_pwd: $("#oldPassword").value,
          new_pwd: $("#newPassword").value
        })
      });
      event.target.reset();
      closeModals();
    }, "密码修改成功");
  });

  $("#logoutBtn").addEventListener("click", () => {
    $("#appView").classList.add("hidden");
    $("#loginView").classList.remove("hidden");
  });

  $("#systemDate").addEventListener("change", (event) => handleAction(async () => {
    await apiRequest("/api/system/set_date", {
      method: "POST",
      body: JSON.stringify({ date: event.target.value })
    });
  }, "系统日期已调整"));

  $("#generateMessagesBtn").addEventListener("click", () => handleAction(async () => {
    const result = await apiRequest("/api/message/generate_due", {
      method: "POST",
      body: JSON.stringify({ current_date: today() })
    });
    showToast(`已生成 ${result.generated_count} 条提醒`);
  }));

  $$(".nav-item").forEach((item) => item.addEventListener("click", () => switchView(item.dataset.view)));
  $$("[data-open-modal]").forEach((item) => item.addEventListener("click", () => openModal(item.dataset.openModal)));
  $$("[data-close-modal]").forEach((item) => item.addEventListener("click", closeModals));
  $$(".modal").forEach((modal) => modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModals();
  }));

  ["bookSearch", "bookCategoryFilter", "itemSearch", "itemStatusFilter", "readerSearch", "readerStatusFilter", "recordSearch", "recordStatusFilter"].forEach((id) => {
    $(`#${id}`).addEventListener("input", renderAll);
    $(`#${id}`).addEventListener("change", renderAll);
  });

  $("#bookForm").addEventListener("submit", (event) => {
    event.preventDefault();
    handleAction(async () => {
      await apiRequest("/api/book/add", {
        method: "POST",
        body: JSON.stringify({
          isbn: $("#bookIsbn").value.trim(),
          book_name: $("#bookName").value.trim(),
          author: $("#bookAuthor").value.trim(),
          category: $("#bookCategory").value.trim(),
          price: Number($("#bookPrice").value || 0),
          total_stock: Number($("#bookStock").value || 1)
        })
      });
      event.target.reset();
      closeModals();
    }, "图书已新增");
  });

  $("#itemForm").addEventListener("submit", (event) => {
    event.preventDefault();
    handleAction(async () => {
      await apiRequest("/api/book_item/add", {
        method: "POST",
        body: JSON.stringify({
          book_id: Number($("#itemBook").value),
          book_item_id: $("#itemBarcode").value.trim(),
          shelf_code: $("#itemLocation").value.trim(),
          status: $("#itemStatus").value
        })
      });
      event.target.reset();
      closeModals();
    }, "馆藏副本已新增");
  });

  $("#readerForm").addEventListener("submit", (event) => {
    event.preventDefault();
    handleAction(async () => {
      await apiRequest("/api/reader/add", {
        method: "POST",
        body: JSON.stringify(authBody({
          username: $("#readerUsername").value.trim(),
          password: "123456",
          name: $("#readerName").value.trim(),
          gender: $("#readerGender").value,
          reader_type: $("#readerType").value.trim(),
          max_borrow_num: Number($("#readerMax").value || 5),
          borrow_days: Number($("#readerDays").value || 30)
        }))
      });
      event.target.reset();
      closeModals();
    }, "读者已新增，默认密码 123456");
  });

  $("#borrowForm").addEventListener("submit", (event) => {
    event.preventDefault();
    handleAction(async () => {
      await apiRequest("/api/borrow/add", {
        method: "POST",
        body: JSON.stringify(authBody({
          user_id: Number($("#borrowUser").value),
          book_item_id: $("#borrowItem").value
        }))
      });
      event.target.reset();
      setDefaultDates();
    }, "借书登记成功");
  });

  $("#returnForm").addEventListener("submit", (event) => {
    event.preventDefault();
    handleAction(async () => {
      await apiRequest("/api/borrow/return", {
        method: "POST",
        body: JSON.stringify(authBody({ borrow_id: Number($("#returnBorrow").value) }))
      });
      event.target.reset();
      setDefaultDates();
    }, "还书登记成功");
  });

  $("#accidentForm").addEventListener("submit", (event) => {
    event.preventDefault();
    handleAction(async () => {
      const handleType = $("#accidentType").value;
      if (handleType === "续借") {
        await apiRequest("/api/borrow/renew", {
          method: "POST",
          body: JSON.stringify(authBody({ borrow_id: Number($("#accidentBorrow").value) }))
        });
      } else {
        await apiRequest("/api/accident/add", {
          method: "POST",
          body: JSON.stringify(authBody({
            borrow_id: Number($("#accidentBorrow").value),
            handle_type: handleType,
            amount: Number($("#accidentAmount").value || 0),
            remark: $("#accidentRemark").value.trim()
          }))
        });
      }
      event.target.reset();
      closeModals();
      setDefaultDates();
    }, "意外处理已记录");
  });

  document.body.addEventListener("click", (event) => {
    const deleteBookId = event.target.dataset.deleteBook;
    const toggleUserId = event.target.dataset.toggleBlack;
    const readMessageId = event.target.dataset.readMessage;

    if (deleteBookId) {
      handleAction(async () => {
        await apiRequest("/api/book/delete", {
          method: "DELETE",
          body: JSON.stringify({ book_id: Number(deleteBookId) })
        });
      }, "图书已删除");
    }

    if (toggleUserId) {
      const user = state.users.find((item) => Number(item.user_id) === Number(toggleUserId));
      if (!user) return;
      handleAction(async () => {
        await apiRequest("/api/reader/update", {
          method: "PUT",
          body: JSON.stringify(authBody({ user_id: user.user_id, black: user.black ? 0 : 1 }))
        });
      });
    }

    if (readMessageId) {
      handleAction(async () => {
        await apiRequest("/api/message/read", {
          method: "PUT",
          body: JSON.stringify(authBody({ msg_id: Number(readMessageId) }))
        });
      });
    }
  });
}

setDefaultDates();
initEvents();
