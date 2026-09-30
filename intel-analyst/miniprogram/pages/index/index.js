const api = require("../../utils/api");
const { parse } = require("../../utils/md");

Page({
  data: { domains: [], current: "", blocks: [], loading: true, empty: false, error: "" },

  async onShow() {
    if (!this.data.domains.length) {
      try {
        const domains = await api.domains();
        const first = (domains.find((d) => d.followed) || domains[0] || {}).key || "";
        this.setData({ domains, current: first });
      } catch (e) { return this.setData({ loading: false, error: e.message }); }
    }
    this.load();
  },

  async load() {
    if (!this.data.current) return;
    this.setData({ loading: true, error: "" });
    try {
      const { briefing } = await api.briefing(this.data.current);
      this.setData({ blocks: parse(briefing), empty: !briefing, loading: false });
    } catch (e) { this.setData({ loading: false, error: e.message }); }
  },

  pick(e) { this.setData({ current: e.currentTarget.dataset.key }, () => this.load()); },
  async onPullDownRefresh() { await this.load(); wx.stopPullDownRefresh(); },
  copy(e) { wx.setClipboardData({ data: e.currentTarget.dataset.url }); },
});
