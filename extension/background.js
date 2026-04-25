const WS_URL = "ws://127.0.0.1:8765/ws/browser";
const RECONNECT_MS = 3000;

let ws = null;
let queue = [];

function connect() {
  try {
    ws = new WebSocket(WS_URL);
  } catch (e) {
    setTimeout(connect, RECONNECT_MS);
    return;
  }
  ws.onopen = () => {
    while (queue.length && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(queue.shift()));
    }
  };
  ws.onclose = () => {
    ws = null;
    setTimeout(connect, RECONNECT_MS);
  };
  ws.onerror = () => {
    try { ws.close(); } catch {}
  };
}

function send(kind, payload) {
  const msg = { kind, payload, ts: Date.now() / 1000 };
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  } else {
    queue.push(msg);
    if (queue.length > 200) queue.shift();
  }
}

connect();

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    send("tab_focus", { url: tab.url, title: tab.title });
  } catch {}
});

chrome.tabs.onUpdated.addListener((_id, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.active) {
    send("tab_loaded", { url: tab.url, title: tab.title });
  }
});

chrome.webNavigation.onCommitted.addListener((details) => {
  if (details.frameId === 0) {
    send("nav", {
      url: details.url,
      transitionType: details.transitionType,
    });
  }
});
