const observed = ["endpoint", "width", "height", "title"];

export class MosaicUIElement extends HTMLElement {
  static get observedAttributes() { return observed; }

  constructor() {
    super();
    this.attachShadow({mode: "open"});
  }

  connectedCallback() { this.render(); }
  attributeChangedCallback() { if (this.isConnected) this.render(); }

  endpointURL() {
    const endpoint = this.getAttribute("endpoint") || window.location.origin;
    const url = new URL(endpoint, window.location.href);
    const bounds = this.getBoundingClientRect();
    url.searchParams.set("width", this.getAttribute("width") || String(Math.max(1, Math.round(bounds.width || 1280))));
    url.searchParams.set("height", this.getAttribute("height") || String(Math.max(1, Math.round(bounds.height || 800))));
    return url;
  }

  render() {
    const url = this.endpointURL();
    const title = this.getAttribute("title") || "Mosaic UI";
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;min-width:0;contain:content}
        iframe{display:block;width:100%;height:100%;min-height:320px;border:0;background:#141618}
      </style>
      <iframe title="${escapeAttribute(title)}" sandbox="allow-forms allow-scripts allow-same-origin" scrolling="no"
        referrerpolicy="no-referrer" src="${escapeAttribute(url.href)}"></iframe>`;
    this.shadowRoot.querySelector("iframe").addEventListener("load", () => {
      this.dispatchEvent(new CustomEvent("mosaic-load", {bubbles: true, composed: true, detail: {url: url.href}}));
    }, {once: true});
  }

  refresh() {
    const frame = this.shadowRoot.querySelector("iframe");
    if (frame) frame.src = this.endpointURL().href;
  }
}

function escapeAttribute(value) {
  return String(value).replace(/[&"<>]/g, character => ({"&":"&amp;", "\"":"&quot;", "<":"&lt;", ">":"&gt;"})[character]);
}

export function defineMosaicUI(tagName = "mosaic-ui") {
  if (!customElements.get(tagName)) customElements.define(tagName, MosaicUIElement);
  return tagName;
}

if (typeof window !== "undefined" && window.customElements) defineMosaicUI();
