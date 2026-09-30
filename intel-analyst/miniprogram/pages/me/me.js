const api = require("../../utils/api");

Page({
  data: { domains: [] },
  async onShow() {
    try { this.setData({ domains: await api.domains() }); }
    catch (e) { wx.showToast({ title: e.message, icon: "none" }); }
  },
  async toggle(e) {
    const { key } = e.currentTarget.dataset;
    try { await api.follow(key, e.detail.value); }
    catch (err) { wx.showToast({ title: err.message, icon: "none" }); this.onShow(); }
  },
});
