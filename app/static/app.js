"use strict";

const STATUS_FLOW = ["created", "in_transit", "out_for_delivery", "delivered"];
const STATUS_LABEL = {
  created: "Created",
  in_transit: "In transit",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
};

const form = document.getElementById("create-form");
const message = document.getElementById("form-message");
const list = document.getElementById("list");
const empty = document.getElementById("empty");
const count = document.getElementById("count");
const search = document.getElementById("search");

let shipments = [];

function setMessage(text, kind) {
  message.textContent = text;
  message.className = "message " + (kind || "");
}

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = "Request failed (" + response.status + ").";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = "Please check the form fields.";
    } catch (e) { /* keep default message */ }
    throw new Error(detail);
  }
  return response.json();
}

// All user-supplied text is added with textContent, never innerHTML (prevents XSS).
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderItem(s) {
  const li = el("li", "item");

  const top = el("div", "row");
  top.append(el("span", "code", s.tracking_code));
  top.append(el("span", "badge s-" + s.status, STATUS_LABEL[s.status]));
  li.append(top);

  li.append(el("p", "meta", s.item + " \u2022 " + s.sender + " \u2192 " + s.receiver));
  li.append(el("p", "meta", "Destination: " + s.destination));

  const steps = el("div", "steps");
  const reached = STATUS_FLOW.indexOf(s.status);
  STATUS_FLOW.forEach(function (_, i) {
    steps.append(el("span", "step" + (i <= reached ? " on" : "")));
  });
  li.append(steps);

  const bottom = el("div", "row");
  bottom.append(el("span", "muted", "Created " + new Date(s.created_at).toLocaleString()));
  const button = el("button", "", "Advance status");
  button.type = "button";
  button.disabled = s.status === "delivered";
  button.addEventListener("click", function () { advance(s.tracking_code, button); });
  bottom.append(button);
  li.append(bottom);
  return li;
}

function render() {
  const term = search.value.trim().toLowerCase();
  const visible = shipments.filter(function (s) {
    return !term || s.tracking_code.toLowerCase().includes(term) || s.receiver.toLowerCase().includes(term);
  });
  list.replaceChildren(...visible.map(renderItem));
  count.textContent = String(shipments.length);
  empty.hidden = visible.length > 0;
  empty.textContent = shipments.length ? "No shipments match your search." : "No shipments yet. Create one above.";
}

async function load() {
  try {
    shipments = await api("/api/v1/shipments");
    render();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

async function advance(code, button) {
  button.disabled = true;
  try {
    await api("/api/v1/shipments/" + encodeURIComponent(code) + "/advance", { method: "POST" });
    await load();
  } catch (error) {
    setMessage(error.message, "error");
    button.disabled = false;
  }
}

form.addEventListener("submit", async function (event) {
  event.preventDefault();
  const submit = form.querySelector("button");
  submit.disabled = true;
  setMessage("", "");
  try {
    const payload = Object.fromEntries(new FormData(form).entries());
    const created = await api("/api/v1/shipments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    form.reset();
    setMessage("Created " + created.tracking_code, "ok");
    await load();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    submit.disabled = false;
  }
});

search.addEventListener("input", render);
load();
