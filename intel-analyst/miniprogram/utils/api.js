const { BASE_URL } = require("../config");

let token = wx.getStorageSync("token") || "";

function login() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: ({ code }) => wx.request({
        url: BASE_URL + "/api/login", method: "POST", data: { code },
        success: (r) => {
          if (r.statusCode !== 200) return reject(new Error(r.data.detail || "登录失败"));
          token = r.data.token;
          wx.setStorageSync("token", token);
          resolve();
        },
        fail: reject,
      }),
      fail: reject,
    });
  });
}

function raw(method, path, data) {
  return new Promise((resolve, reject) => wx.request({
    url: BASE_URL + "/api" + path, method, data,
    header: { Authorization: "Bearer " + token },
    success: resolve, fail: reject,
  }));
}

async function call(method, path, data) {
  if (!token) await login();
  let r = await raw(method, path, data);
  if (r.statusCode === 401) { await login(); r = await raw(method, path, data); }
  if (r.statusCode >= 400) throw new Error(r.data.detail || "请求失败(" + r.statusCode + ")");
  return r.data;
}

module.exports = {
  domains: () => call("GET", "/domains"),
  briefing: (key) => call("GET", "/briefing/" + key),
  ask: (domain, q) => call("POST", "/ask", { domain, q }),
  follow: (key, on) => call("PUT", "/follow/" + key, { on }),
};
