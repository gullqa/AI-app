// 极简 Markdown → 块列表。小程序里外链无法直接打开，链接单独成块，点击复制。
const URL_RE = /https?:\/\/[^\s)）]+/;

function parse(text) {
  const blocks = [];
  for (const line0 of String(text || "").split("\n")) {
    const line = line0.trim();
    if (!line || /^-{3,}$/.test(line)) continue;
    const url = (line.match(URL_RE) || [])[0];
    const clean = (s) => s.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, "$1").replace(/\*\*|__|`/g, "");
    let m;
    if ((m = line.match(/^(#{1,3})\s+(.*)/))) blocks.push({ t: "h" + m[1].length, text: clean(m[2]) });
    else if ((m = line.match(/^(?:[-*]|\d+\.)\s+(.*)/))) blocks.push({ t: "li", text: clean(m[1].replace(URL_RE, "")).trim(), url });
    else blocks.push({ t: "p", text: clean(line.replace(URL_RE, "")).trim(), url });
  }
  return blocks;
}

module.exports = { parse };
