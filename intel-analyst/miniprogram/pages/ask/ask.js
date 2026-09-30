const api = require("../../utils/api");
const { parse } = require("../../utils/md");

Page({
  data: { names: [], keys: [], idx: 0, q: "", msgs: [], busy: false },

  async onShow() {
    if (this.data.keys.length) return;
    try {
      const ds = await api.domains();
      this.setData({ names: ds.map((d) => d.name), keys: ds.map((d) => d.key) });
    } catch (e) { wx.showToast({ title: e.message, icon: "none" }); }
  },

  pick(e) { this.setData({ idx: +e.detail.value }); },
  input(e) { this.setData({ q: e.detail.value }); },

  async send() {
    const q = this.data.q.trim();
    if (!q || this.data.busy) return;
    const msgs = this.data.msgs.concat({ role: "me", text: q });
    this.setData({ msgs, q: "", busy: true });
    try {
      const { answer } = await api.ask(this.data.keys[this.data.idx], q);
      this.setData({ msgs: msgs.concat({ role: "ai", blocks: parse(answer) }) });
    } catch (e) {
      this.setData({ msgs: msgs.concat({ role: "ai", blocks: [{ t: "p", text: e.message }] }) });
    }
    this.setData({ busy: false });
  },
});
